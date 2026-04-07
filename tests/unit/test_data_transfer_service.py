"""
Unit tests for DataTransferService.

Tests the core data transfer service functionality including:
- Permission checking integration
- Approval workflow integration
- Transfer to different target states
- Source validation
- Audit logging
- Sensitive data detection integration
- Error handling and rollback behavior
"""

import pytest
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session

from src.services.data_transfer_service import DataTransferService, User
from src.services.permission_service import UserRole, PermissionResult
from src.models.data_transfer import (
    DataTransferRequest, DataAttributes, TransferRecord
)
from src.models.data_lifecycle import DataState
from src.models.approval import ApprovalRequest, ApprovalStatus
from src.security.sensitive_data_validator import SensitiveDataDetectionResult
from src.sync.desensitization.models import SensitivityLevel


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = Mock(spec=Session)
    db.add = Mock()
    db.add_all = Mock()
    db.commit = Mock()
    db.flush = Mock()
    db.execute = Mock()
    db.bulk_save_objects = Mock()
    db.rollback = Mock()

    @contextmanager
    def _begin_nested():
        yield

    db.begin_nested = Mock(side_effect=_begin_nested)
    return db


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return User(id="admin-123", role=UserRole.ADMIN)


@pytest.fixture
def data_analyst_user():
    """Create a data analyst user."""
    return User(id="analyst-456", role=UserRole.DATA_ANALYST)


@pytest.fixture
def regular_user():
    """Create a regular user."""
    return User(id="user-789", role=UserRole.USER)


@pytest.fixture
def sample_transfer_request():
    """Create a sample transfer request."""
    return DataTransferRequest(
        source_type="structuring",
        source_id="struct-job-123",
        target_state="temp_stored",
        data_attributes=DataAttributes(
            category="test_category",
            tags=["test", "sample"],
            quality_score=0.85,
            description="Test data transfer"
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


class TestDataTransferServiceInit:
    """Test DataTransferService initialization."""
    
    def test_init_creates_services(self, mock_db):
        """Test that initialization creates required service instances."""
        service = DataTransferService(mock_db)
        
        assert service.db == mock_db
        assert service.permission_service is not None
        assert service.approval_service is not None


class TestTransferPermissionChecking:
    """Test permission checking in transfer operations."""
    
    @pytest.mark.asyncio
    async def test_admin_transfer_no_approval_required(
        self, mock_db, admin_user, sample_transfer_request
    ):
        """Test that admin can transfer without approval."""
        service = DataTransferService(mock_db)
        
        # Mock permission check to allow without approval
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(sample_transfer_request, admin_user)
        
        assert result["success"] is True
        assert "approval_required" not in result or not result["approval_required"]
        assert result["transferred_count"] == 2
    
    @pytest.mark.asyncio
    async def test_analyst_transfer_to_library_requires_approval(
        self, mock_db, data_analyst_user
    ):
        """Test that data analyst needs approval for sample library transfer."""
        service = DataTransferService(mock_db)
        
        request = DataTransferRequest(
            source_type="structuring",
            source_id="struct-job-123",
            target_state="in_sample_library",
            data_attributes=DataAttributes(
                category="test_category",
                tags=["test"],
                quality_score=0.85
            ),
            records=[
                TransferRecord(
                    id="record-1",
                    content={"field1": "value1"}
                )
            ]
        )
        
        # Mock permission check to require approval
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=True,
                current_role=UserRole.DATA_ANALYST
            )
        ):
            # Mock approval service
            mock_approval = ApprovalRequest(
                id="approval-123",
                transfer_request=request,
                requester_id=data_analyst_user.id,
                requester_role=UserRole.DATA_ANALYST.value,
                status=ApprovalStatus.PENDING,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow()
            )
            
            with patch.object(
                service.approval_service, 'create_approval_request',
                return_value=mock_approval
            ) as mock_create_approval:
                result = await service.transfer(request, data_analyst_user)
        
        assert result["success"] is True
        assert result["approval_required"] is True
        assert result["approval_id"] == "approval-123"
        mock_create_approval.assert_called_once()


class TestTransferToTempStorage:
    """Test transfer to temporary storage."""
    
    @pytest.mark.asyncio
    async def test_transfer_to_temp_storage_success(
        self, mock_db, admin_user, sample_transfer_request
    ):
        """Test successful transfer to temporary storage with bulk insert."""
        service = DataTransferService(mock_db)
        
        # Mock permission check
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(sample_transfer_request, admin_user)
        
        assert result["success"] is True
        assert result["transferred_count"] == 2
        assert result["target_state"] == "temp_stored"
        assert len(result["lifecycle_ids"]) == 2
        assert result["navigation_url"] == "/data-lifecycle/temp-data"
        
        # Verify database operations - bulk_save_objects for records + add for audit log
        assert mock_db.bulk_save_objects.call_count == 1
        assert mock_db.add.call_count == 1  # Only audit log
        assert mock_db.flush.call_count >= 1
        
        # Verify bulk_save_objects was called with correct number of records
        bulk_call_args = mock_db.bulk_save_objects.call_args[0][0]
        assert len(bulk_call_args) == 2
    
    @pytest.mark.asyncio
    async def test_transfer_preserves_metadata(
        self, mock_db, admin_user
    ):
        """Test that transfer preserves record metadata with bulk insert."""
        service = DataTransferService(mock_db)
        
        request = DataTransferRequest(
            source_type="augmentation",
            source_id="aug-job-456",
            target_state="temp_stored",
            data_attributes=DataAttributes(
                category="enhanced_data",
                tags=["enhanced"],
                quality_score=0.92,
                description="Enhanced data"
            ),
            records=[
                TransferRecord(
                    id="record-1",
                    content={"text": "sample text"},
                    metadata={
                        "enhancement_method": "paraphrase",
                        "original_id": "orig-123"
                    }
                )
            ]
        )
        
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)
        
        assert result["success"] is True
        
        # Verify metadata was preserved in the call to bulk_save_objects
        bulk_call_args = mock_db.bulk_save_objects.call_args[0][0]
        temp_data = bulk_call_args[0]
        
        assert temp_data.metadata_["source_type"] == "augmentation"
        assert temp_data.metadata_["category"] == "enhanced_data"
        assert temp_data.metadata_["enhancement_method"] == "paraphrase"
        assert temp_data.metadata_["original_id"] == "orig-123"


class TestTransferToSampleLibrary:
    """Test transfer to sample library."""
    
    @pytest.mark.asyncio
    async def test_transfer_to_sample_library_success(
        self, mock_db, admin_user
    ):
        """Test successful transfer to sample library with bulk insert."""
        service = DataTransferService(mock_db)
        
        request = DataTransferRequest(
            source_type="augmentation",
            source_id="aug-job-789",
            target_state="in_sample_library",
            data_attributes=DataAttributes(
                category="high_quality_samples",
                tags=["verified", "production"],
                quality_score=0.95,
                description="Production-ready samples"
            ),
            records=[
                TransferRecord(
                    id="record-1",
                    content={"text": "high quality text"}
                )
            ]
        )
        
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)
        
        assert result["success"] is True
        assert result["transferred_count"] == 1
        assert result["target_state"] == "in_sample_library"
        assert result["navigation_url"] == "/data-lifecycle/sample-library"
        
        # Sample library path uses add_all + flush (not bulk_save_objects)
        bulk_call_args = mock_db.add_all.call_args[0][0]
        sample = bulk_call_args[0]
        
        assert sample.quality_overall == 0.95
        assert sample.quality_completeness == 0.95
        assert sample.quality_accuracy == 0.95
        assert sample.quality_consistency == 0.95
        assert sample.category == "high_quality_samples"
        assert sample.tags == ["verified", "production"]


class TestTransferToAnnotationPending:
    """Test transfer to annotation pending state."""
    
    @pytest.mark.asyncio
    async def test_transfer_to_annotation_pending_success(
        self, mock_db, admin_user
    ):
        """Test successful transfer to annotation pending with bulk insert."""
        service = DataTransferService(mock_db)
        
        request = DataTransferRequest(
            source_type="sync",
            source_id="sync-job-999",
            target_state="annotation_pending",
            data_attributes=DataAttributes(
                category="needs_annotation",
                tags=["unlabeled"],
                quality_score=0.7,
                description="Data requiring annotation"
            ),
            records=[
                TransferRecord(
                    id="record-1",
                    content={"text": "text to annotate"}
                ),
                TransferRecord(
                    id="record-2",
                    content={"text": "another text"}
                )
            ]
        )
        
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)
        
        assert result["success"] is True
        assert result["transferred_count"] == 2
        assert result["target_state"] == "annotation_pending"
        assert result["navigation_url"] == "/data-lifecycle/annotation-pending"
        
        # Verify records marked as pending annotation using bulk_save_objects
        bulk_call_args = mock_db.bulk_save_objects.call_args[0][0]
        temp_data = bulk_call_args[0]
        
        assert temp_data.state == DataState.ANNOTATION_PENDING
        assert temp_data.metadata_["pending_annotation"] is True


class TestSourceValidation:
    """Test source data validation."""
    
    @pytest.mark.asyncio
    async def test_validate_source_with_empty_id_raises_error(
        self, mock_db, admin_user
    ):
        """Test that empty source_id raises ValueError during validation."""
        service = DataTransferService(mock_db)
        
        # Create a mock request that bypasses Pydantic validation
        # to test the service's own validation logic
        request = Mock(spec=DataTransferRequest)
        request.source_type = "structuring"
        request.source_id = ""  # Empty source_id
        request.target_state = "temp_stored"
        request.data_attributes = DataAttributes(
            category="test",
            quality_score=0.8
        )
        request.records = [
            TransferRecord(id="record-1", content={"test": "data"})
        ]
        request.request_approval = False
        
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            with pytest.raises(ValueError, match="Invalid source_id"):
                await service.transfer(request, admin_user)


class TestAuditLogging:
    """Test audit logging functionality."""
    
    @pytest.mark.asyncio
    async def test_audit_log_created_on_successful_transfer(
        self, mock_db, admin_user, sample_transfer_request
    ):
        """Test that audit log is created on successful transfer with bulk insert."""
        service = DataTransferService(mock_db)
        
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(sample_transfer_request, admin_user)
        
        assert result["success"] is True
        
        # Verify audit log was created (should be the only call to db.add)
        assert mock_db.add.call_count == 1
        audit_log = mock_db.add.call_args[0][0]
        
        # Verify TransferAuditLogModel fields
        assert audit_log.user_id == admin_user.id
        assert audit_log.user_role == UserRole.ADMIN.value
        assert audit_log.operation == "transfer"
        assert audit_log.source_type == "structuring"
        assert audit_log.source_id == "struct-job-123"
        assert audit_log.target_state == "temp_stored"
        assert audit_log.record_count == 2
        assert audit_log.success is True
        assert audit_log.error_message is None
    
    @pytest.mark.asyncio
    async def test_audit_log_failure_does_not_fail_transfer(
        self, mock_db, admin_user, sample_transfer_request
    ):
        """Test that audit log failure doesn't fail the transfer with bulk insert."""
        service = DataTransferService(mock_db)
        
        # Make audit log creation fail (db.add is only called for audit log now)
        mock_db.add = Mock(side_effect=Exception("Audit log creation failed"))
        mock_db.rollback = Mock()
        
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            # Should not raise exception
            result = await service.transfer(sample_transfer_request, admin_user)
        
        assert result["success"] is True
        mock_db.add.assert_called()
        # Real Session would roll back the nested savepoint; the mock does not call rollback().
    
    @pytest.mark.asyncio
    async def test_audit_log_created_on_failed_transfer(
        self, mock_db, admin_user, sample_transfer_request
    ):
        """Test that audit log is created even when transfer fails."""
        service = DataTransferService(mock_db)
        
        # Make the transfer fail by causing validation error
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            with patch.object(
                service, '_validate_source',
                side_effect=ValueError("Source validation failed")
            ):
                with pytest.raises(ValueError, match="Source validation failed"):
                    await service.transfer(sample_transfer_request, admin_user)
        
        # Verify audit log was created with error
        assert mock_db.add.call_count == 1
        audit_log = mock_db.add.call_args[0][0]
        
        assert audit_log.user_id == admin_user.id
        assert audit_log.success is False
        assert audit_log.error_message == "Source validation failed"
        assert audit_log.source_type == "structuring"
        assert audit_log.target_state == "temp_stored"
    
    @pytest.mark.asyncio
    async def test_audit_log_created_for_approval_submission(
        self, mock_db, data_analyst_user
    ):
        """Test that audit log is created when approval is required."""
        service = DataTransferService(mock_db)
        
        request = DataTransferRequest(
            source_type="structuring",
            source_id="struct-job-123",
            target_state="in_sample_library",
            data_attributes=DataAttributes(
                category="test_category",
                tags=["test"],
                quality_score=0.85
            ),
            records=[
                TransferRecord(
                    id="record-1",
                    content={"field1": "value1"}
                )
            ]
        )
        
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=True,
                current_role=UserRole.DATA_ANALYST
            )
        ):
            mock_approval = ApprovalRequest(
                id="approval-123",
                transfer_request=request,
                requester_id=data_analyst_user.id,
                requester_role=UserRole.DATA_ANALYST.value,
                status=ApprovalStatus.PENDING,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow()
            )
            
            with patch.object(
                service.approval_service, 'create_approval_request',
                return_value=mock_approval
            ):
                result = await service.transfer(request, data_analyst_user)
        
        assert result["approval_required"] is True
        
        # Verify audit log was created for approval submission
        assert mock_db.add.call_count == 1
        audit_log = mock_db.add.call_args[0][0]
        
        assert audit_log.user_id == data_analyst_user.id
        assert audit_log.success is True  # Approval submission is successful
        assert audit_log.operation == "transfer"
        assert audit_log.target_state == "in_sample_library"


class TestBatchTransfer:
    """Test batch transfer operations."""
    
    @pytest.mark.asyncio
    async def test_large_batch_transfer_triggers_approval(
        self, mock_db, data_analyst_user
    ):
        """Test that large batch transfers trigger approval for non-admin users."""
        service = DataTransferService(mock_db)
        
        # Create request with >1000 records
        records = [
            TransferRecord(
                id=f"record-{i}",
                content={"field": f"value-{i}"}
            )
            for i in range(1001)
        ]
        
        request = DataTransferRequest(
            source_type="sync",
            source_id="sync-large-batch",
            target_state="temp_stored",
            data_attributes=DataAttributes(
                category="batch_data",
                quality_score=0.8
            ),
            records=records
        )
        
        # Mock permission check to require approval for batch
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=True,
                current_role=UserRole.DATA_ANALYST
            )
        ):
            mock_approval = ApprovalRequest(
                id="approval-batch-123",
                transfer_request=request,
                requester_id=data_analyst_user.id,
                requester_role=UserRole.DATA_ANALYST.value,
                status=ApprovalStatus.PENDING,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow()
            )
            
            with patch.object(
                service.approval_service, 'create_approval_request',
                return_value=mock_approval
            ):
                result = await service.transfer(request, data_analyst_user)
        
        assert result["approval_required"] is True
        assert result["approval_id"] == "approval-batch-123"
    
    @pytest.mark.asyncio
    async def test_bulk_insert_optimization_for_large_batch(
        self, mock_db, admin_user
    ):
        """Test that bulk insert is used for large batches (1000+ records)."""
        service = DataTransferService(mock_db)
        
        # Create request with 1500 records
        records = [
            TransferRecord(
                id=f"record-{i}",
                content={"field": f"value-{i}"}
            )
            for i in range(1500)
        ]
        
        request = DataTransferRequest(
            source_type="sync",
            source_id="sync-large-batch",
            target_state="temp_stored",
            data_attributes=DataAttributes(
                category="batch_data",
                quality_score=0.8
            ),
            records=records
        )
        
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)
        
        assert result["success"] is True
        assert result["transferred_count"] == 1500
        
        # Verify bulk_save_objects was called once with all records
        assert mock_db.bulk_save_objects.call_count == 1
        bulk_call_args = mock_db.bulk_save_objects.call_args[0][0]
        assert len(bulk_call_args) == 1500
        
        # Verify individual add was NOT called for records (only for audit log)
        assert mock_db.add.call_count == 1  # Only audit log
    
    @pytest.mark.asyncio
    async def test_bulk_insert_preserves_all_record_data(
        self, mock_db, admin_user
    ):
        """Test that bulk insert preserves all record data correctly."""
        service = DataTransferService(mock_db)
        
        # Create request with multiple records with different data
        records = [
            TransferRecord(
                id=f"record-{i}",
                content={"text": f"content-{i}", "value": i},
                metadata={"index": i, "type": "test"}
            )
            for i in range(100)
        ]
        
        request = DataTransferRequest(
            source_type="augmentation",
            source_id="aug-job-bulk",
            target_state="in_sample_library",
            data_attributes=DataAttributes(
                category="bulk_test",
                tags=["bulk", "test"],
                quality_score=0.9,
                description="Bulk insert test"
            ),
            records=records
        )
        
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)
        
        assert result["success"] is True
        assert result["transferred_count"] == 100
        
        # Sample library uses add_all([...]) for ORM-visible inserts
        bulk_call_args = mock_db.add_all.call_args[0][0]
        assert len(bulk_call_args) == 100
        
        # Verify first and last records have correct data
        first_sample = bulk_call_args[0]
        assert first_sample.content == {"text": "content-0", "value": 0}
        assert first_sample.metadata_["index"] == 0
        assert first_sample.category == "bulk_test"
        assert first_sample.quality_overall == 0.9
        
        last_sample = bulk_call_args[99]
        assert last_sample.content == {"text": "content-99", "value": 99}
        assert last_sample.metadata_["index"] == 99


class TestErrorHandling:
    """Test error handling in transfer operations."""
    
    @pytest.mark.asyncio
    async def test_unsupported_target_state_raises_error(
        self, mock_db, admin_user
    ):
        """Test that unsupported target state raises ValueError."""
        service = DataTransferService(mock_db)
        
        # Create request with invalid target_state
        # Note: This would normally be caught by Pydantic validation,
        # but we test the service logic directly
        request = Mock(spec=DataTransferRequest)
        request.source_type = "structuring"
        request.source_id = "test-123"
        request.target_state = "invalid_state"
        request.data_attributes = DataAttributes(
            category="test",
            quality_score=0.8
        )
        request.records = [
            TransferRecord(id="record-1", content={"test": "data"})
        ]
        request.request_approval = False
        
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            with pytest.raises(ValueError, match="Unsupported target state"):
                await service.transfer(request, admin_user)
    
    @pytest.mark.asyncio
    async def test_database_error_during_transfer(
        self, mock_db, admin_user, sample_transfer_request
    ):
        """Test handling of database errors during transfer."""
        service = DataTransferService(mock_db)
        
        # Persist path uses flush(), not commit()
        mock_db.flush.side_effect = Exception("Database connection lost")
        
        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True,
                requires_approval=False,
                current_role=UserRole.ADMIN
            )
        ):
            with pytest.raises(Exception, match="Database connection lost"):
                await service.transfer(sample_transfer_request, admin_user)


# --- Helper for creating a default non-sensitive detection result ---

def _make_clean_detection_result():
    """Create a SensitiveDataDetectionResult with no sensitive data."""
    result = SensitiveDataDetectionResult()
    # defaults: has_sensitive_data=False, requires_additional_approval=False
    return result


# --- Additional tests for coverage gaps ---


class TestTransferToTempStorageMetadata:
    """Test metadata correctness for temp_stored transfers."""

    @pytest.mark.asyncio
    async def test_temp_storage_records_have_correct_state(self, mock_db, admin_user):
        """Test that all records are created with TEMP_STORED state."""
        service = DataTransferService(mock_db)

        request = DataTransferRequest(
            source_type="sync",
            source_id="sync-job-100",
            target_state="temp_stored",
            data_attributes=DataAttributes(
                category="sync_data",
                tags=["synced"],
                quality_score=0.75,
                description="Synced data batch"
            ),
            records=[
                TransferRecord(id="r1", content={"a": 1}),
                TransferRecord(id="r2", content={"b": 2}),
                TransferRecord(id="r3", content={"c": 3}),
            ]
        )

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)

        assert result["success"] is True
        assert result["transferred_count"] == 3

        bulk_args = mock_db.bulk_save_objects.call_args[0][0]
        for record in bulk_args:
            assert record.state == DataState.TEMP_STORED
            assert record.uploaded_by == admin_user.id
            assert record.source_document_id == "sync-job-100"
            assert record.metadata_["source_type"] == "sync"
            assert record.metadata_["category"] == "sync_data"
            assert record.metadata_["quality_score"] == 0.75

    @pytest.mark.asyncio
    async def test_temp_storage_without_record_metadata(self, mock_db, admin_user):
        """Test transfer when records have no metadata (None)."""
        service = DataTransferService(mock_db)

        request = DataTransferRequest(
            source_type="structuring",
            source_id="struct-no-meta",
            target_state="temp_stored",
            data_attributes=DataAttributes(category="plain", quality_score=0.5),
            records=[
                TransferRecord(id="r1", content={"x": "y"}, metadata=None)
            ]
        )

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)

        assert result["success"] is True
        bulk_args = mock_db.bulk_save_objects.call_args[0][0]
        # metadata_ should still contain the data_attributes fields
        assert bulk_args[0].metadata_["category"] == "plain"
        assert bulk_args[0].metadata_["quality_score"] == 0.5


class TestTransferToSampleLibraryDetails:
    """Test sample library transfer details beyond basic success."""

    @pytest.mark.asyncio
    async def test_sample_library_multiple_records_quality_scores(
        self, mock_db, admin_user
    ):
        """Test that all records in sample library get correct quality scores."""
        service = DataTransferService(mock_db)

        request = DataTransferRequest(
            source_type="augmentation",
            source_id="aug-multi",
            target_state="in_sample_library",
            data_attributes=DataAttributes(
                category="multi_sample",
                tags=["a", "b"],
                quality_score=0.88,
                description="Multiple samples"
            ),
            records=[
                TransferRecord(id=f"r{i}", content={"val": i})
                for i in range(5)
            ]
        )

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)

        assert result["transferred_count"] == 5
        assert result["target_state"] == "in_sample_library"

        bulk_args = mock_db.add_all.call_args[0][0]
        assert len(bulk_args) == 5
        for sample in bulk_args:
            assert sample.quality_overall == 0.88
            assert sample.quality_completeness == 0.88
            assert sample.quality_accuracy == 0.88
            assert sample.quality_consistency == 0.88
            assert sample.version == 1
            assert sample.usage_count == 0
            assert sample.tags == ["a", "b"]

    @pytest.mark.asyncio
    async def test_sample_library_metadata_includes_transfer_info(
        self, mock_db, admin_user
    ):
        """Test that sample metadata includes transfer user and timestamp."""
        service = DataTransferService(mock_db)

        request = DataTransferRequest(
            source_type="structuring",
            source_id="struct-meta-check",
            target_state="in_sample_library",
            data_attributes=DataAttributes(
                category="meta_check",
                quality_score=0.9,
                description="Metadata check"
            ),
            records=[
                TransferRecord(
                    id="r1",
                    content={"text": "hello"},
                    metadata={"custom_key": "custom_val"}
                )
            ]
        )

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)

        assert result["success"] is True
        sample = mock_db.add_all.call_args[0][0][0]
        assert sample.metadata_["transferred_by"] == admin_user.id
        assert "transferred_at" in sample.metadata_
        assert sample.metadata_["source_type"] == "structuring"
        assert sample.metadata_["custom_key"] == "custom_val"


class TestTransferToAnnotationPendingDetails:
    """Test annotation pending transfer metadata details."""

    @pytest.mark.asyncio
    async def test_annotation_pending_metadata_has_pending_flag(
        self, mock_db, admin_user
    ):
        """Test that annotation pending records have pending_annotation=True."""
        service = DataTransferService(mock_db)

        request = DataTransferRequest(
            source_type="augmentation",
            source_id="aug-annot",
            target_state="annotation_pending",
            data_attributes=DataAttributes(
                category="to_annotate",
                tags=["needs_label"],
                quality_score=0.6
            ),
            records=[
                TransferRecord(
                    id="r1",
                    content={"text": "annotate me"},
                    metadata={"priority": "high"}
                )
            ]
        )

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)

        assert result["success"] is True
        record = mock_db.bulk_save_objects.call_args[0][0][0]
        assert record.state == DataState.ANNOTATION_PENDING
        assert record.metadata_["pending_annotation"] is True
        assert record.metadata_["tags"] == ["needs_label"]
        assert record.metadata_["priority"] == "high"
        assert record.metadata_["source_type"] == "augmentation"


class TestSourceValidationExtended:
    """Extended source validation tests."""

    @pytest.mark.asyncio
    async def test_valid_source_id_passes_validation(self, mock_db, admin_user):
        """Test that a valid non-empty source_id passes validation."""
        service = DataTransferService(mock_db)

        request = DataTransferRequest(
            source_type="structuring",
            source_id="valid-source-123",
            target_state="temp_stored",
            data_attributes=DataAttributes(category="test", quality_score=0.8),
            records=[TransferRecord(id="r1", content={"a": 1})]
        )

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            # Should not raise
            result = await service.transfer(request, admin_user)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_all_source_types_accepted(self, mock_db, admin_user):
        """Test that all valid source types (structuring, augmentation, sync) work."""
        service = DataTransferService(mock_db)

        for source_type in ["structuring", "augmentation", "sync"]:
            mock_db.reset_mock()
            request = DataTransferRequest(
                source_type=source_type,
                source_id=f"{source_type}-job-1",
                target_state="temp_stored",
                data_attributes=DataAttributes(category="test", quality_score=0.8),
                records=[TransferRecord(id="r1", content={"data": source_type})]
            )

            with patch.object(
                service.permission_service, 'check_permission',
                return_value=PermissionResult(
                    allowed=True, requires_approval=False, current_role=UserRole.ADMIN
                )
            ):
                result = await service.transfer(request, admin_user)

            assert result["success"] is True
            assert result["transferred_count"] == 1


class TestApprovalWorkflowExtended:
    """Extended approval workflow tests."""

    @pytest.mark.asyncio
    async def test_regular_user_transfer_to_library_requires_approval(
        self, mock_db, regular_user
    ):
        """Test that regular user needs approval for sample library transfer."""
        service = DataTransferService(mock_db)

        request = DataTransferRequest(
            source_type="structuring",
            source_id="struct-user-req",
            target_state="in_sample_library",
            data_attributes=DataAttributes(category="user_data", quality_score=0.7),
            records=[TransferRecord(id="r1", content={"x": 1})]
        )

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=True, current_role=UserRole.USER
            )
        ):
            mock_approval = ApprovalRequest(
                id="approval-user-001",
                transfer_request=request,
                requester_id=regular_user.id,
                requester_role=UserRole.USER.value,
                status=ApprovalStatus.PENDING,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow()
            )
            with patch.object(
                service.approval_service, 'create_approval_request',
                return_value=mock_approval
            ) as mock_create:
                result = await service.transfer(request, regular_user)

        assert result["success"] is True
        assert result["approval_required"] is True
        assert result["approval_id"] == "approval-user-001"
        mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_sensitive_data_triggers_additional_approval(
        self, mock_db, admin_user
    ):
        """Test that sensitive data detection triggers approval even for admin."""
        service = DataTransferService(mock_db)

        request = DataTransferRequest(
            source_type="structuring",
            source_id="struct-sensitive",
            target_state="temp_stored",
            data_attributes=DataAttributes(category="sensitive", quality_score=0.8),
            records=[TransferRecord(id="r1", content={"ssn": "123-45-6789"})]
        )

        # Permission says no approval needed, but sensitive data says yes
        sensitive_result = SensitiveDataDetectionResult()
        sensitive_result.has_sensitive_data = True
        sensitive_result.requires_additional_approval = True
        sensitive_result.sensitivity_level = SensitivityLevel.CRITICAL
        sensitive_result.risk_score = 0.9
        sensitive_result.recommendations = ["Apply data masking"]

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            with patch.object(
                service.sensitive_data_validator, 'validate_transfer_request',
                return_value=sensitive_result
            ):
                mock_approval = ApprovalRequest(
                    id="approval-sensitive-001",
                    transfer_request=request,
                    requester_id=admin_user.id,
                    requester_role=UserRole.ADMIN.value,
                    status=ApprovalStatus.PENDING,
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow()
                )
                with patch.object(
                    service.approval_service, 'create_approval_request',
                    return_value=mock_approval
                ):
                    result = await service.transfer(request, admin_user)

        assert result["approval_required"] is True
        assert result["sensitive_data_detected"] is True
        assert result["sensitivity_level"] == "critical"
        assert "Apply data masking" in result["recommendations"]


class TestBulkInsertOptimizationExtended:
    """Extended bulk insert optimization tests."""

    @pytest.mark.asyncio
    async def test_small_batch_uses_bulk_save(self, mock_db, admin_user):
        """Test that even small batches use bulk_save_objects (not individual add)."""
        service = DataTransferService(mock_db)

        request = DataTransferRequest(
            source_type="structuring",
            source_id="struct-small",
            target_state="temp_stored",
            data_attributes=DataAttributes(category="small", quality_score=0.8),
            records=[TransferRecord(id="r1", content={"a": 1})]
        )

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)

        assert result["success"] is True
        # bulk_save_objects should be used for records
        assert mock_db.bulk_save_objects.call_count == 1
        # db.add should only be called for audit log, not for records
        assert mock_db.add.call_count == 1

    @pytest.mark.asyncio
    async def test_bulk_insert_for_annotation_pending_large_batch(
        self, mock_db, admin_user
    ):
        """Test bulk insert optimization for annotation_pending with >1000 records."""
        service = DataTransferService(mock_db)

        records = [
            TransferRecord(id=f"r{i}", content={"idx": i})
            for i in range(1200)
        ]

        request = DataTransferRequest(
            source_type="sync",
            source_id="sync-large-annot",
            target_state="annotation_pending",
            data_attributes=DataAttributes(category="large_annot", quality_score=0.7),
            records=records
        )

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            result = await service.transfer(request, admin_user)

        assert result["success"] is True
        assert result["transferred_count"] == 1200
        assert mock_db.bulk_save_objects.call_count == 1
        bulk_args = mock_db.bulk_save_objects.call_args[0][0]
        assert len(bulk_args) == 1200


class TestErrorHandlingExtended:
    """Extended error handling and rollback tests."""

    @pytest.mark.asyncio
    async def test_unsupported_target_state_logs_audit_with_error(
        self, mock_db, admin_user
    ):
        """Test that unsupported target state logs an audit entry with error."""
        service = DataTransferService(mock_db)

        request = Mock(spec=DataTransferRequest)
        request.source_type = "structuring"
        request.source_id = "test-err"
        request.target_state = "nonexistent_state"
        request.data_attributes = DataAttributes(category="err", quality_score=0.5)
        request.records = [TransferRecord(id="r1", content={"x": 1})]
        request.request_approval = False

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            with pytest.raises(ValueError, match="Unsupported target state"):
                await service.transfer(request, admin_user)

        # Audit log should still be created with error info
        assert mock_db.add.call_count == 1
        audit_log = mock_db.add.call_args[0][0]
        assert audit_log.success is False
        assert "Unsupported target state" in audit_log.error_message

    @pytest.mark.asyncio
    async def test_flush_failure_during_transfer_reraises(
        self, mock_db, admin_user
    ):
        """Flush failure during data persist re-raises (service does not commit)."""
        service = DataTransferService(mock_db)

        mock_db.flush.side_effect = RuntimeError("Connection lost during flush")

        request = DataTransferRequest(
            source_type="structuring",
            source_id="struct-fail",
            target_state="temp_stored",
            data_attributes=DataAttributes(category="fail", quality_score=0.5),
            records=[TransferRecord(id="r1", content={"a": 1})]
        )

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            with pytest.raises(RuntimeError, match="Connection lost"):
                await service.transfer(request, admin_user)

        assert mock_db.bulk_save_objects.call_count == 1

    @pytest.mark.asyncio
    async def test_validation_error_does_not_execute_transfer(
        self, mock_db, admin_user
    ):
        """Test that source validation failure prevents transfer execution."""
        service = DataTransferService(mock_db)

        request = Mock(spec=DataTransferRequest)
        request.source_type = "structuring"
        request.source_id = ""
        request.target_state = "temp_stored"
        request.data_attributes = DataAttributes(category="test", quality_score=0.8)
        request.records = [TransferRecord(id="r1", content={"a": 1})]
        request.request_approval = False

        with patch.object(
            service.permission_service, 'check_permission',
            return_value=PermissionResult(
                allowed=True, requires_approval=False, current_role=UserRole.ADMIN
            )
        ):
            with pytest.raises(ValueError, match="Invalid source_id"):
                await service.transfer(request, admin_user)

        # bulk_save_objects should NOT have been called
        assert mock_db.bulk_save_objects.call_count == 0
