"""
Unit tests for approval models.

Tests the ApprovalStatus enum and ApprovalRequest model to ensure
they work correctly according to the design specification.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.models.approval import ApprovalStatus, ApprovalRequest
from src.models.data_transfer import (
    DataTransferRequest,
    DataAttributes,
    TransferRecord
)


class TestApprovalStatus:
    """Test ApprovalStatus enum."""
    
    def test_approval_status_values(self):
        """Test that all expected approval statuses are defined."""
        assert ApprovalStatus.PENDING == "pending"
        assert ApprovalStatus.APPROVED == "approved"
        assert ApprovalStatus.REJECTED == "rejected"
        assert ApprovalStatus.EXPIRED == "expired"
    
    def test_approval_status_value_access(self):
        """Test that ApprovalStatus values can be accessed."""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
        assert ApprovalStatus.EXPIRED.value == "expired"
    
    def test_approval_status_from_string(self):
        """Test that ApprovalStatus can be created from string."""
        assert ApprovalStatus("pending") == ApprovalStatus.PENDING
        assert ApprovalStatus("approved") == ApprovalStatus.APPROVED
        assert ApprovalStatus("rejected") == ApprovalStatus.REJECTED
        assert ApprovalStatus("expired") == ApprovalStatus.EXPIRED
    
    def test_approval_status_invalid_value(self):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError):
            ApprovalStatus("invalid_status")


class TestApprovalRequest:
    """Test ApprovalRequest model."""
    
    @pytest.fixture
    def sample_transfer_request(self):
        """Create a sample transfer request for testing."""
        return DataTransferRequest(
            source_type="structuring",
            source_id="test-source-123",
            target_state="in_sample_library",
            data_attributes=DataAttributes(
                category="test_category",
                tags=["tag1", "tag2"],
                quality_score=0.9,
                description="Test description"
            ),
            records=[
                TransferRecord(
                    id="record-1",
                    content={"field1": "value1"},
                    metadata={"meta1": "value1"}
                )
            ]
        )
    
    def test_approval_request_creation(self, sample_transfer_request):
        """Test creating an ApprovalRequest with all required fields."""
        now = datetime.utcnow()
        expires = now + timedelta(days=7)
        
        approval = ApprovalRequest(
            id="approval-123",
            transfer_request=sample_transfer_request,
            requester_id="user-456",
            requester_role="data_analyst",
            created_at=now,
            expires_at=expires
        )
        
        assert approval.id == "approval-123"
        assert approval.transfer_request == sample_transfer_request
        assert approval.requester_id == "user-456"
        assert approval.requester_role == "data_analyst"
        assert approval.status == ApprovalStatus.PENDING
        assert approval.created_at == now
        assert approval.expires_at == expires
        assert approval.approver_id is None
        assert approval.approved_at is None
        assert approval.comment is None
    
    def test_approval_request_with_custom_status(self, sample_transfer_request):
        """Test creating an ApprovalRequest with custom status."""
        now = datetime.utcnow()
        
        approval = ApprovalRequest(
            id="approval-123",
            transfer_request=sample_transfer_request,
            requester_id="user-456",
            requester_role="data_analyst",
            status=ApprovalStatus.APPROVED,
            created_at=now,
            expires_at=now + timedelta(days=7)
        )
        
        assert approval.status == ApprovalStatus.APPROVED
    
    def test_approval_request_with_approver_info(self, sample_transfer_request):
        """Test creating an ApprovalRequest with approver information."""
        now = datetime.utcnow()
        approved_time = now + timedelta(hours=2)
        
        approval = ApprovalRequest(
            id="approval-123",
            transfer_request=sample_transfer_request,
            requester_id="user-456",
            requester_role="data_analyst",
            status=ApprovalStatus.APPROVED,
            created_at=now,
            expires_at=now + timedelta(days=7),
            approver_id="admin-789",
            approved_at=approved_time,
            comment="Approved for high quality data"
        )
        
        assert approval.approver_id == "admin-789"
        assert approval.approved_at == approved_time
        assert approval.comment == "Approved for high quality data"
    
    def test_approval_request_missing_required_fields(self):
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ApprovalRequest(
                id="approval-123"
                # Missing all other required fields
            )
        
        errors = exc_info.value.errors()
        assert len(errors) >= 4
        field_names = {error['loc'][0] for error in errors}
        assert 'transfer_request' in field_names
        assert 'requester_id' in field_names
        assert 'created_at' in field_names
        assert 'expires_at' in field_names
    
    def test_approval_request_comment_max_length(self, sample_transfer_request):
        """Test that comment exceeding max length raises ValidationError."""
        now = datetime.utcnow()
        long_comment = "x" * 501  # Exceeds 500 character limit
        
        with pytest.raises(ValidationError) as exc_info:
            ApprovalRequest(
                id="approval-123",
                transfer_request=sample_transfer_request,
                requester_id="user-456",
                requester_role="data_analyst",
                created_at=now,
                expires_at=now + timedelta(days=7),
                comment=long_comment
            )
        
        errors = exc_info.value.errors()
        assert any(error['loc'][0] == 'comment' for error in errors)
    
    def test_approval_request_json_serialization(self, sample_transfer_request):
        """Test that ApprovalRequest can be serialized to JSON."""
        now = datetime.utcnow()
        expires = now + timedelta(days=7)
        
        approval = ApprovalRequest(
            id="approval-123",
            transfer_request=sample_transfer_request,
            requester_id="user-456",
            requester_role="data_analyst",
            created_at=now,
            expires_at=expires
        )
        
        json_data = approval.model_dump()
        
        assert json_data['id'] == "approval-123"
        assert json_data['requester_id'] == "user-456"
        assert json_data['requester_role'] == "data_analyst"
        assert json_data['status'] == "pending"
        assert json_data['approver_id'] is None
        assert json_data['approved_at'] is None
        assert json_data['comment'] is None
    
    def test_approval_request_from_dict(self, sample_transfer_request):
        """Test creating ApprovalRequest from dictionary."""
        now = datetime.utcnow()
        expires = now + timedelta(days=7)
        
        data = {
            'id': 'approval-123',
            'transfer_request': sample_transfer_request.model_dump(),
            'requester_id': 'user-456',
            'requester_role': 'data_analyst',
            'status': 'pending',
            'created_at': now.isoformat(),
            'expires_at': expires.isoformat()
        }
        
        approval = ApprovalRequest(**data)
        
        assert approval.id == "approval-123"
        assert approval.requester_id == "user-456"
        assert approval.status == ApprovalStatus.PENDING
    
    def test_approval_request_rejected_with_comment(self, sample_transfer_request):
        """Test creating a rejected ApprovalRequest with comment."""
        now = datetime.utcnow()
        
        approval = ApprovalRequest(
            id="approval-123",
            transfer_request=sample_transfer_request,
            requester_id="user-456",
            requester_role="data_analyst",
            status=ApprovalStatus.REJECTED,
            created_at=now,
            expires_at=now + timedelta(days=7),
            approver_id="admin-789",
            approved_at=now + timedelta(hours=1),
            comment="Data quality does not meet requirements"
        )
        
        assert approval.status == ApprovalStatus.REJECTED
        assert approval.comment == "Data quality does not meet requirements"
    
    def test_approval_request_expired(self, sample_transfer_request):
        """Test creating an expired ApprovalRequest."""
        now = datetime.utcnow()
        past_time = now - timedelta(days=1)
        
        approval = ApprovalRequest(
            id="approval-123",
            transfer_request=sample_transfer_request,
            requester_id="user-456",
            requester_role="data_analyst",
            status=ApprovalStatus.EXPIRED,
            created_at=past_time - timedelta(days=7),
            expires_at=past_time
        )
        
        assert approval.status == ApprovalStatus.EXPIRED
        assert approval.expires_at < now
