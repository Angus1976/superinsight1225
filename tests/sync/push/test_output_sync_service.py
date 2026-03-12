"""
Unit tests for OutputSyncService.

Tests output sync execution, data validation, and checkpoint resume.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.sync.push.output_sync_service import (
    OutputSyncService,
    SyncResult,
    ValidationResult,
)
from src.sync.push.incremental_push import PushResult
from src.sync.models import (
    SyncJobModel,
    SyncExecutionModel,
    SyncDirection,
    DataSourceModel,
    DataSourceType,
)


@pytest.fixture
def output_sync_service():
    """Create OutputSyncService instance."""
    return OutputSyncService()


@pytest.fixture
def sample_job():
    """Create sample sync job."""
    return SyncJobModel(
        id=uuid4(),
        tenant_id="test-tenant",
        name="Test Output Sync",
        source_id=uuid4(),
        target_source_id=uuid4(),
        direction=SyncDirection.PUSH,
        field_mapping_rules={
            "field_mappings": [
                {
                    "source_field": "id",
                    "target_field": "record_id",
                    "target_type": "string",
                    "required": True
                },
                {
                    "source_field": "value",
                    "target_field": "data_value",
                    "target_type": "integer",
                    "required": True
                }
            ]
        },
        output_sync_strategy="full",
        output_checkpoint=None,
        target_config={"table_name": "output_table"},
        max_retries=3,
        retry_delay=60
    )


@pytest.fixture
def sample_data():
    """Create sample data records."""
    return [
        {"id": "1", "value": 100, "name": "Record 1"},
        {"id": "2", "value": 200, "name": "Record 2"},
        {"id": "3", "value": 300, "name": "Record 3"}
    ]


class TestValidateOutputData:
    """Test data validation before writing."""
    
    def test_validate_valid_data(self, output_sync_service):
        """Test validation passes for valid data."""
        data = [
            {"record_id": "1", "data_value": 100},
            {"record_id": "2", "data_value": 200}
        ]
        
        mapping = {
            "field_mappings": [
                {
                    "target_field": "record_id",
                    "target_type": "string",
                    "required": True
                },
                {
                    "target_field": "data_value",
                    "target_type": "integer",
                    "required": True
                }
            ]
        }
        
        result = output_sync_service.validate_output_data(data, mapping)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_missing_required_field(self, output_sync_service):
        """Test validation fails for missing required field."""
        data = [
            {"record_id": "1"},  # Missing data_value
            {"record_id": "2", "data_value": 200}
        ]
        
        mapping = {
            "field_mappings": [
                {
                    "target_field": "record_id",
                    "target_type": "string",
                    "required": True
                },
                {
                    "target_field": "data_value",
                    "target_type": "integer",
                    "required": True
                }
            ]
        }
        
        result = output_sync_service.validate_output_data(data, mapping)
        
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0]["type"] == "missing_required_field"
        assert result.errors[0]["field"] == "data_value"
    
    def test_validate_type_mismatch(self, output_sync_service):
        """Test validation fails for type mismatch."""
        data = [
            {"record_id": "1", "data_value": "not_an_integer"},
            {"record_id": "2", "data_value": 200}
        ]
        
        mapping = {
            "field_mappings": [
                {
                    "target_field": "record_id",
                    "target_type": "string",
                    "required": True
                },
                {
                    "target_field": "data_value",
                    "target_type": "integer",
                    "required": True
                }
            ]
        }
        
        result = output_sync_service.validate_output_data(data, mapping)
        
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0]["type"] == "type_mismatch"
        assert result.errors[0]["field"] == "data_value"
        assert result.errors[0]["expected_type"] == "integer"
    
    def test_validate_empty_dataset(self, output_sync_service):
        """Test validation handles empty dataset."""
        data = []
        mapping = {"field_mappings": []}
        
        result = output_sync_service.validate_output_data(data, mapping)
        
        assert result.is_valid
        assert len(result.warnings) == 1
        assert result.warnings[0]["type"] == "empty_dataset"
    
    def test_validate_null_values_allowed(self, output_sync_service):
        """Test validation allows null values for nullable fields."""
        data = [
            {"record_id": "1", "data_value": None}
        ]
        
        mapping = {
            "field_mappings": [
                {
                    "target_field": "record_id",
                    "target_type": "string",
                    "required": True
                },
                {
                    "target_field": "data_value",
                    "target_type": "integer",
                    "required": False,
                    "nullable": True
                }
            ]
        }
        
        result = output_sync_service.validate_output_data(data, mapping)
        
        assert result.is_valid
        assert len(result.errors) == 0


class TestExecuteOutputSync:
    """Test output sync execution."""
    
    @pytest.mark.asyncio
    async def test_execute_full_sync_success(
        self, output_sync_service, sample_job, sample_data
    ):
        """Test successful full sync execution."""
        with patch.object(
            output_sync_service, "_load_sync_job", new_callable=AsyncMock
        ) as mock_load_job, \
        patch.object(
            output_sync_service, "_create_execution_record", new_callable=AsyncMock
        ) as mock_create_exec, \
        patch.object(
            output_sync_service, "_load_source_data", new_callable=AsyncMock
        ) as mock_load_data, \
        patch.object(
            output_sync_service, "_create_push_target", new_callable=AsyncMock
        ) as mock_create_target, \
        patch.object(
            output_sync_service.push_service, "push_with_retry", new_callable=AsyncMock
        ) as mock_push, \
        patch.object(
            output_sync_service, "_update_execution_record", new_callable=AsyncMock
        ) as mock_update_exec, \
        patch("src.sync.push.output_sync_service.db_manager") as mock_db:
            
            # Setup mocks
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            mock_load_job.return_value = sample_job
            mock_create_exec.return_value = MagicMock(spec=SyncExecutionModel)
            mock_load_data.return_value = sample_data
            mock_create_target.return_value = MagicMock()
            
            mock_push.return_value = PushResult(
                push_id=str(uuid4()),
                target_id=str(sample_job.target_source_id),
                status="success",
                records_pushed=3,
                records_failed=0,
                execution_time_ms=100.0
            )
            
            # Execute
            result = await output_sync_service.execute_output_sync(sample_job.id)
            
            # Verify
            assert result.status == "success"
            assert result.records_written == 3
            assert result.records_failed == 0
            assert result.job_id == sample_job.id
            
            mock_load_job.assert_called_once()
            mock_push.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_sync_validation_failure(
        self, output_sync_service, sample_job
    ):
        """Test sync fails when validation fails."""
        # Create invalid mapped data (missing required field after mapping)
        invalid_mapped_data = [
            {"record_id": "1"}  # Missing data_value
        ]
        
        with patch.object(
            output_sync_service, "_load_sync_job", new_callable=AsyncMock
        ) as mock_load_job, \
        patch.object(
            output_sync_service, "_create_execution_record", new_callable=AsyncMock
        ), \
        patch.object(
            output_sync_service, "_load_source_data", new_callable=AsyncMock
        ) as mock_load_data, \
        patch.object(
            output_sync_service, "_apply_field_mapping"
        ) as mock_apply_mapping, \
        patch("src.sync.push.output_sync_service.db_manager") as mock_db:
            
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            mock_load_job.return_value = sample_job
            mock_load_data.return_value = [{"id": "1", "value": 100}]
            mock_apply_mapping.return_value = invalid_mapped_data
            
            # Execute
            result = await output_sync_service.execute_output_sync(sample_job.id)
            
            # Verify
            assert result.status == "failed"
            assert "validation failed" in result.error_message.lower()


class TestResumeFromCheckpoint:
    """Test checkpoint resume functionality."""
    
    @pytest.mark.asyncio
    async def test_resume_with_checkpoint(self, output_sync_service, sample_job):
        """Test resume from existing checkpoint."""
        sample_job.output_checkpoint = {
            "checkpoint_field": "updated_at",
            "last_sync_value": "2024-01-01T00:00:00",
            "last_sync_time": "2024-01-01T00:00:00"
        }
        
        with patch.object(
            output_sync_service, "_load_sync_job", new_callable=AsyncMock
        ) as mock_load_job, \
        patch.object(
            output_sync_service, "execute_output_sync", new_callable=AsyncMock
        ) as mock_execute, \
        patch("src.sync.push.output_sync_service.db_manager") as mock_db:
            
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            mock_load_job.return_value = sample_job
            mock_execute.return_value = SyncResult(
                execution_id=uuid4(),
                job_id=sample_job.id,
                status="success",
                records_total=5,
                records_written=5,
                records_failed=0,
                execution_time_ms=100.0
            )
            
            # Execute
            result = await output_sync_service.resume_from_checkpoint(sample_job.id)
            
            # Verify
            assert result.status == "success"
            mock_execute.assert_called_once_with(sample_job.id, strategy="incremental")
    
    @pytest.mark.asyncio
    async def test_resume_without_checkpoint(self, output_sync_service, sample_job):
        """Test resume without checkpoint falls back to full sync."""
        sample_job.output_checkpoint = None
        
        with patch.object(
            output_sync_service, "_load_sync_job", new_callable=AsyncMock
        ) as mock_load_job, \
        patch.object(
            output_sync_service, "execute_output_sync", new_callable=AsyncMock
        ) as mock_execute, \
        patch("src.sync.push.output_sync_service.db_manager") as mock_db:
            
            mock_session = AsyncMock()
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            
            mock_load_job.return_value = sample_job
            mock_execute.return_value = SyncResult(
                execution_id=uuid4(),
                job_id=sample_job.id,
                status="success",
                records_total=10,
                records_written=10,
                records_failed=0,
                execution_time_ms=200.0
            )
            
            # Execute
            result = await output_sync_service.resume_from_checkpoint(sample_job.id)
            
            # Verify
            assert result.status == "success"
            mock_execute.assert_called_once_with(sample_job.id, strategy="full")
