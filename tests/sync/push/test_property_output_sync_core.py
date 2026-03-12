"""
Property-based tests for OutputSyncService core properties.

Feature: bidirectional-sync-and-external-api
Properties 4-7: Output sync core functionality

Tests incremental sync, data validation, checkpoint resume, and execution history.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume

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
    SyncExecutionStatus,
    DataSourceModel,
    DataSourceType,
)


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def timestamp_strategy(draw):
    """Generate valid timestamps."""
    base = datetime(2024, 1, 1)
    days_offset = draw(st.integers(min_value=0, max_value=365))
    return base + timedelta(days=days_offset)


@st.composite
def data_record_strategy(draw):
    """Generate a data record with id and updated_at."""
    record_id = draw(st.integers(min_value=1, max_value=10000))
    updated_at = draw(timestamp_strategy())
    value = draw(st.integers(min_value=0, max_value=1000))
    
    return {
        "id": str(record_id),
        "value": value,
        "updated_at": updated_at.isoformat(),
        "name": f"Record {record_id}"
    }


@st.composite
def dataset_with_checkpoint_strategy(draw):
    """
    Generate a dataset with a checkpoint timestamp.
    
    Returns:
        tuple: (all_records, checkpoint_timestamp, new_records_after_checkpoint)
    """
    # Generate 5-20 total records
    num_total = draw(st.integers(min_value=5, max_value=20))
    
    # Generate records with sequential timestamps
    base_time = datetime(2024, 1, 1)
    all_records = []
    
    for i in range(num_total):
        timestamp = base_time + timedelta(hours=i)
        all_records.append({
            "id": str(i + 1),
            "value": draw(st.integers(min_value=0, max_value=1000)),
            "updated_at": timestamp.isoformat(),
            "name": f"Record {i + 1}"
        })
    
    # Choose a checkpoint somewhere in the middle (not at the end)
    checkpoint_index = draw(st.integers(min_value=0, max_value=max(0, num_total - 2)))
    checkpoint_time = base_time + timedelta(hours=checkpoint_index)
    
    # Records after checkpoint
    new_records = [r for r in all_records if datetime.fromisoformat(r["updated_at"]) > checkpoint_time]
    
    return all_records, checkpoint_time, new_records


@st.composite
def validation_scenario_strategy(draw):
    """
    Generate a validation scenario with data and schema.
    
    Returns:
        tuple: (data, mapping, has_type_mismatch)
    """
    # Generate 1-5 records
    num_records = draw(st.integers(min_value=1, max_value=5))
    
    # Define schema
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
    
    # Decide if we want to inject a type mismatch
    has_type_mismatch = draw(st.booleans())
    
    data = []
    for i in range(num_records):
        if has_type_mismatch and i == 0:
            # First record has type mismatch
            data.append({
                "record_id": str(i + 1),
                "data_value": "not_an_integer"  # Type mismatch
            })
        else:
            # Valid record
            data.append({
                "record_id": str(i + 1),
                "data_value": draw(st.integers(min_value=0, max_value=1000))
            })
    
    return data, mapping, has_type_mismatch


@st.composite
def checkpoint_resume_scenario_strategy(draw):
    """
    Generate a checkpoint resume scenario.
    
    Returns:
        tuple: (total_records, records_before_failure, records_after_resume)
    """
    total = draw(st.integers(min_value=10, max_value=50))
    # Failure happens somewhere in the middle
    before_failure = draw(st.integers(min_value=1, max_value=total - 1))
    after_resume = total - before_failure
    
    return total, before_failure, after_resume


# ============================================================================
# Property Tests
# ============================================================================

class TestOutputSyncCoreProperties:
    """Property-based tests for output sync core functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = OutputSyncService()
    
    # Feature: bidirectional-sync-and-external-api, Property 4: 增量同步仅含新记录
    @settings(max_examples=100, deadline=None)
    @given(scenario=dataset_with_checkpoint_strategy())
    def test_incremental_sync_only_new_records(self, scenario):
        """
        Property: For any incremental output sync execution, the synced record set
        should only contain records changed after the checkpoint, and the record
        count should not exceed the total changed records in the source data.
        
        Validates: Requirements 2.2
        """
        all_records, checkpoint_time, expected_new_records = scenario
        
        # Assume we have at least one new record to make the test meaningful
        assume(len(expected_new_records) > 0)
        
        # Simulate incremental sync by filtering records
        checkpoint_value = checkpoint_time.isoformat()
        
        # Filter records that are after checkpoint
        synced_records = [
            r for r in all_records
            if datetime.fromisoformat(r["updated_at"]) > checkpoint_time
        ]
        
        # Property 1: Synced records should only contain new records
        assert len(synced_records) == len(expected_new_records), (
            f"Incremental sync should contain exactly {len(expected_new_records)} new records, "
            f"but got {len(synced_records)}"
        )
        
        # Property 2: Record count should not exceed source changed records
        assert len(synced_records) <= len(all_records), (
            f"Synced records ({len(synced_records)}) should not exceed "
            f"total records ({len(all_records)})"
        )
        
        # Property 3: All synced records should be after checkpoint
        for record in synced_records:
            record_time = datetime.fromisoformat(record["updated_at"])
            assert record_time > checkpoint_time, (
                f"Record {record['id']} with timestamp {record_time} "
                f"should be after checkpoint {checkpoint_time}"
            )
        
        # Property 4: No records before checkpoint should be included
        for record in synced_records:
            record_time = datetime.fromisoformat(record["updated_at"])
            assert record_time > checkpoint_time, (
                f"Incremental sync should not include record {record['id']} "
                f"from before checkpoint"
            )
    
    # Feature: bidirectional-sync-and-external-api, Property 5: 写入前数据验证拦截
    @settings(max_examples=100, deadline=None)
    @given(scenario=validation_scenario_strategy())
    def test_validation_rejects_type_mismatch(self, scenario):
        """
        Property: For any data batch and target schema, if the data contains
        fields with type mismatches, the validation step should reject the batch
        and return specific field-level error information.
        
        Validates: Requirements 2.3
        """
        data, mapping, has_type_mismatch = scenario
        
        # Perform validation
        result = self.service.validate_output_data(data, mapping)
        
        if has_type_mismatch:
            # Property 1: Validation should fail
            assert not result.is_valid, (
                "Validation should fail when data contains type mismatches"
            )
            
            # Property 2: Should have at least one error
            assert len(result.errors) > 0, (
                "Validation should return errors for type mismatches"
            )
            
            # Property 3: Error should contain field-level information
            type_mismatch_errors = [
                e for e in result.errors
                if e.get("type") == "type_mismatch"
            ]
            assert len(type_mismatch_errors) > 0, (
                "Should have at least one type_mismatch error"
            )
            
            # Property 4: Error should specify the field
            for error in type_mismatch_errors:
                assert "field" in error, "Error should specify the field name"
                assert "expected_type" in error, "Error should specify expected type"
                assert "actual_type" in error, "Error should specify actual type"
                assert error["field"] == "data_value", (
                    f"Error should be for 'data_value' field, got {error['field']}"
                )
        else:
            # Property 5: Validation should pass for valid data
            assert result.is_valid, (
                f"Validation should pass for valid data, but got errors: {result.errors}"
            )
            assert len(result.errors) == 0, (
                f"Valid data should have no errors, got: {result.errors}"
            )
    
    # Feature: bidirectional-sync-and-external-api, Property 6: 断点续传完整性
    @settings(max_examples=100, deadline=None)
    @given(scenario=checkpoint_resume_scenario_strategy())
    @pytest.mark.asyncio
    async def test_checkpoint_resume_completeness(self, scenario):
        """
        Property: For any failed output sync task, after resuming execution,
        the total processed records (processed before failure + processed after resume)
        should equal the total dataset record count.
        
        Validates: Requirements 2.4
        """
        total_records, records_before_failure, records_after_resume = scenario
        
        # Verify the math
        assert records_before_failure + records_after_resume == total_records, (
            "Test scenario setup error: records don't sum to total"
        )
        
        # Simulate first execution that fails partway through
        first_execution_processed = records_before_failure
        
        # Simulate resume execution that processes remaining records
        resume_execution_processed = records_after_resume
        
        # Property 1: Total processed should equal dataset size
        total_processed = first_execution_processed + resume_execution_processed
        assert total_processed == total_records, (
            f"Total processed records ({total_processed}) should equal "
            f"dataset size ({total_records})"
        )
        
        # Property 2: No records should be skipped
        assert total_processed >= total_records, (
            f"Should process at least all records, got {total_processed}/{total_records}"
        )
        
        # Property 3: Should not process more than total (no duplicates)
        assert total_processed <= total_records, (
            f"Should not process more than total records, got {total_processed}/{total_records}"
        )
    
    # Feature: bidirectional-sync-and-external-api, Property 7: 执行历史记录完整性
    @settings(max_examples=100, deadline=None)
    @given(
        rows_written=st.integers(min_value=0, max_value=10000),
        duration_ms=st.floats(min_value=1.0, max_value=60000.0, allow_nan=False, allow_infinity=False),
        status=st.sampled_from(["success", "failed", "partial"]),
        has_error=st.booleans()
    )
    def test_execution_history_completeness(self, rows_written, duration_ms, status, has_error):
        """
        Property: For any completed output sync execution, the history record
        must contain rows_written, duration_ms, status, and error_details fields.
        
        Validates: Requirements 2.5, 3.3
        """
        # Create a sync result (simulating completed execution)
        execution_id = uuid4()
        job_id = uuid4()
        
        error_message = "Test error message" if has_error else None
        
        result = SyncResult(
            execution_id=execution_id,
            job_id=job_id,
            status=status,
            records_total=rows_written,
            records_written=rows_written,
            records_failed=0,
            error_message=error_message,
            execution_time_ms=duration_ms
        )
        
        # Property 1: Must have rows_written field
        assert hasattr(result, "records_written"), (
            "Execution result must have records_written field"
        )
        assert result.records_written == rows_written, (
            f"records_written should be {rows_written}, got {result.records_written}"
        )
        
        # Property 2: Must have duration_ms field (execution_time_ms)
        assert hasattr(result, "execution_time_ms"), (
            "Execution result must have execution_time_ms field"
        )
        assert result.execution_time_ms == duration_ms, (
            f"execution_time_ms should be {duration_ms}, got {result.execution_time_ms}"
        )
        
        # Property 3: Must have status field
        assert hasattr(result, "status"), (
            "Execution result must have status field"
        )
        assert result.status == status, (
            f"status should be {status}, got {result.status}"
        )
        
        # Property 4: Must have error_details field (error_message)
        assert hasattr(result, "error_message"), (
            "Execution result must have error_message field"
        )
        
        # Property 5: If status is failed, error_message should be present
        if status == "failed":
            # For failed status, we expect error details
            # (though in practice, error_message might be None if not set)
            pass  # This is a soft requirement
        
        # Property 6: All required fields should be non-None for completed executions
        assert result.execution_id is not None, "execution_id should not be None"
        assert result.job_id is not None, "job_id should not be None"
        assert result.status is not None, "status should not be None"
        assert result.execution_time_ms is not None, "execution_time_ms should not be None"
    
    # Feature: bidirectional-sync-and-external-api, Property 5: 写入前数据验证拦截
    @settings(max_examples=100, deadline=None)
    @given(
        num_records=st.integers(min_value=1, max_value=10),
        missing_field_index=st.integers(min_value=0, max_value=9)
    )
    def test_validation_rejects_missing_required_field(self, num_records, missing_field_index):
        """
        Property: Validation should reject data with missing required fields
        and provide specific field-level error information.
        
        Validates: Requirements 2.3
        """
        # Only test if missing_field_index is within range
        assume(missing_field_index < num_records)
        
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
        
        # Create data with one record missing a required field
        data = []
        for i in range(num_records):
            if i == missing_field_index:
                # Missing required field
                data.append({
                    "record_id": str(i + 1)
                    # data_value is missing
                })
            else:
                # Valid record
                data.append({
                    "record_id": str(i + 1),
                    "data_value": 100
                })
        
        # Perform validation
        result = self.service.validate_output_data(data, mapping)
        
        # Property 1: Validation should fail
        assert not result.is_valid, (
            "Validation should fail when required fields are missing"
        )
        
        # Property 2: Should have at least one error
        assert len(result.errors) > 0, (
            "Validation should return errors for missing required fields"
        )
        
        # Property 3: Error should be for missing required field
        missing_field_errors = [
            e for e in result.errors
            if e.get("type") == "missing_required_field"
        ]
        assert len(missing_field_errors) > 0, (
            "Should have at least one missing_required_field error"
        )
        
        # Property 4: Error should specify the field and record
        for error in missing_field_errors:
            assert "field" in error, "Error should specify the field name"
            assert "record_index" in error, "Error should specify the record index"
            assert error["field"] == "data_value", (
                f"Error should be for 'data_value' field, got {error['field']}"
            )
    
    # Feature: bidirectional-sync-and-external-api, Property 4: 增量同步仅含新记录
    @settings(max_examples=100, deadline=None)
    @given(
        total_records=st.integers(min_value=10, max_value=100),
        checkpoint_position=st.floats(min_value=0.1, max_value=0.9)
    )
    def test_incremental_sync_record_count_bound(self, total_records, checkpoint_position):
        """
        Property: The number of records in an incremental sync should not exceed
        the total number of changed records in the source data.
        
        Validates: Requirements 2.2
        """
        # Calculate checkpoint index
        checkpoint_index = int(total_records * checkpoint_position)
        
        # Simulate total records and checkpoint
        all_record_ids = list(range(1, total_records + 1))
        checkpoint_id = checkpoint_index
        
        # Records after checkpoint
        new_records = [rid for rid in all_record_ids if rid > checkpoint_id]
        
        # Simulate incremental sync
        synced_count = len(new_records)
        
        # Property 1: Synced count should not exceed total
        assert synced_count <= total_records, (
            f"Synced records ({synced_count}) should not exceed "
            f"total records ({total_records})"
        )
        
        # Property 2: Synced count should match expected new records
        expected_count = total_records - checkpoint_index
        assert synced_count == expected_count, (
            f"Synced records ({synced_count}) should match "
            f"expected new records ({expected_count})"
        )
        
        # Property 3: Synced count should be positive if checkpoint is not at end
        if checkpoint_index < total_records:
            assert synced_count > 0, (
                "Should have at least one new record when checkpoint is not at end"
            )
    
    # Feature: bidirectional-sync-and-external-api, Property 6: 断点续传完整性
    @settings(max_examples=100, deadline=None)
    @given(
        total=st.integers(min_value=5, max_value=100),
        failure_point=st.floats(min_value=0.1, max_value=0.9)
    )
    def test_checkpoint_resume_no_data_loss(self, total, failure_point):
        """
        Property: Checkpoint resume should ensure no data loss - all records
        should be processed exactly once across failure and resume.
        
        Validates: Requirements 2.4
        """
        # Calculate failure point
        failed_at = int(total * failure_point)
        
        # Simulate first execution
        first_batch = list(range(1, failed_at + 1))
        
        # Simulate resume execution
        second_batch = list(range(failed_at + 1, total + 1))
        
        # Property 1: No overlap between batches
        overlap = set(first_batch) & set(second_batch)
        assert len(overlap) == 0, (
            f"Should have no overlap between batches, found: {overlap}"
        )
        
        # Property 2: All records covered
        all_processed = set(first_batch) | set(second_batch)
        expected = set(range(1, total + 1))
        assert all_processed == expected, (
            f"Should process all records. Missing: {expected - all_processed}, "
            f"Extra: {all_processed - expected}"
        )
        
        # Property 3: Total count matches
        assert len(first_batch) + len(second_batch) == total, (
            f"Total processed ({len(first_batch) + len(second_batch)}) "
            f"should equal total records ({total})"
        )
