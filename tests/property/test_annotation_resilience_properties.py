"""Property-based tests for Annotation Resilience and Error Handling.

This module tests the following properties:
- Property 34: LLM API Retry Logic
- Property 35: Network Failure Queuing
- Property 36: Transaction Rollback
- Property 37: Input Validation
- Property 38: Error Logging and Notification

Requirements:
- LLM API calls should retry with exponential backoff (1s, 2s, 4s)
- Network failures should queue operations for retry
- Database transactions should rollback on errors
- Input validation should provide specific error details
- Errors should be logged with full context and notifications sent
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import List
from datetime import datetime
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.ai.annotation_resilience import (
    LLMRetryService,
    RetryPolicy,
    NetworkFailureQueue,
    DatabaseTransactionManager,
    InputValidationService,
    ErrorNotificationService,
    ErrorCategory,
    ErrorSeverity,
    reset_resilience_services,
)


# ============================================================================
# Property 34: LLM API Retry Logic
# ============================================================================

class TestLLMAPIRetryLogic:
    """Property 34: LLM API retry with exponential backoff.

    Validates: Requirements 10.1
    """

    @pytest.mark.asyncio
    @given(
        num_failures_before_success=st.integers(min_value=0, max_value=3)
    )
    @settings(max_examples=100, deadline=None)
    async def test_retry_with_exponential_backoff(self, num_failures_before_success: int):
        """Test that retry uses exponential backoff (1s, 2s, 4s)."""
        await reset_resilience_services()

        policy = RetryPolicy(
            max_retries=3,
            backoff_base=1.0,
            backoff_multiplier=2.0,
            jitter=False,  # Disable jitter for predictable testing
        )
        service = LLMRetryService(policy)

        # Track call times
        call_times = []
        attempt_count = [0]

        async def failing_function():
            call_times.append(datetime.now())
            attempt_count[0] += 1

            if attempt_count[0] <= num_failures_before_success:
                raise ValueError(f"Simulated failure {attempt_count[0]}")

            return "success"

        # Call with retry
        start_time = datetime.now()
        result = await service.retry_with_backoff(
            failing_function,
            operation_name="test_operation"
        )

        # Should eventually succeed
        assert result == "success"
        assert attempt_count[0] == num_failures_before_success + 1

        # Verify exponential backoff delays
        if num_failures_before_success > 0:
            for i in range(1, num_failures_before_success + 1):
                delay = (call_times[i] - call_times[i-1]).total_seconds()
                expected_delay = policy.backoff_base * (policy.backoff_multiplier ** (i-1))

                # Allow small margin for timing
                assert delay >= expected_delay * 0.9
                assert delay <= expected_delay * 1.2

    @pytest.mark.asyncio
    @given(
        max_retries=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    async def test_retry_exhaustion(self, max_retries: int):
        """Test that retry gives up after max_retries attempts."""
        await reset_resilience_services()

        policy = RetryPolicy(max_retries=max_retries, backoff_base=0.1)
        service = LLMRetryService(policy)

        attempt_count = [0]

        async def always_failing():
            attempt_count[0] += 1
            raise ValueError("Always fails")

        # Should raise after all retries exhausted
        with pytest.raises(ValueError, match="Always fails"):
            await service.retry_with_backoff(
                always_failing,
                operation_name="test_operation"
            )

        # Should have tried max_retries + 1 times (initial + retries)
        assert attempt_count[0] == max_retries + 1

    @pytest.mark.asyncio
    async def test_immediate_success_no_retry(self):
        """Test that immediate success does not trigger retries."""
        await reset_resilience_services()

        service = LLMRetryService()

        attempt_count = [0]

        async def immediate_success():
            attempt_count[0] += 1
            return "success"

        result = await service.retry_with_backoff(
            immediate_success,
            operation_name="test_operation"
        )

        assert result == "success"
        assert attempt_count[0] == 1  # Only one attempt


# ============================================================================
# Property 35: Network Failure Queuing
# ============================================================================

class TestNetworkFailureQueuing:
    """Property 35: Network failures queue operations for retry.

    Validates: Requirements 10.2
    """

    @pytest.mark.asyncio
    @given(
        num_operations=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    async def test_queue_operations(self, num_operations: int):
        """Test that operations can be queued."""
        await reset_resilience_services()

        queue = NetworkFailureQueue(retry_interval=1, max_queue_size=100)

        operation_ids = []

        async def dummy_operation(value: int):
            return value * 2

        # Queue operations
        for i in range(num_operations):
            op_id = await queue.enqueue(
                operation_type="test_op",
                operation_func=dummy_operation,
                value=i
            )
            operation_ids.append(op_id)

        # Verify all queued
        assert await queue.get_queue_size() == num_operations

        # Verify operations retrievable
        queued_ops = await queue.get_queued_operations()
        assert len(queued_ops) == num_operations

    @pytest.mark.asyncio
    async def test_queue_retry_on_connectivity_restore(self):
        """Test that queued operations retry when connectivity restored."""
        await reset_resilience_services()

        queue = NetworkFailureQueue(retry_interval=1)

        success_count = [0]
        is_connected = [False]

        async def network_dependent_operation():
            if not is_connected[0]:
                raise ConnectionError("No network")
            success_count[0] += 1

        # Queue operation (will fail first time)
        op_id = await queue.enqueue(
            operation_type="network_op",
            operation_func=network_dependent_operation
        )

        # Start retry loop
        await queue.start_retry_loop()

        # Wait a bit (operation will fail)
        await asyncio.sleep(0.5)
        assert success_count[0] == 0

        # Restore connectivity
        is_connected[0] = True

        # Wait for retry
        await asyncio.sleep(1.5)

        # Should have succeeded
        assert success_count[0] == 1

        # Should be removed from queue
        assert await queue.get_queue_size() == 0

        await queue.stop_retry_loop()

    @pytest.mark.asyncio
    async def test_queue_size_limit(self):
        """Test that queue enforces size limit."""
        await reset_resilience_services()

        max_size = 10
        queue = NetworkFailureQueue(max_queue_size=max_size)

        async def dummy_op():
            pass

        # Fill queue to limit
        for i in range(max_size):
            await queue.enqueue("test_op", dummy_op)

        # Next enqueue should fail
        with pytest.raises(ValueError, match="Queue full"):
            await queue.enqueue("test_op", dummy_op)


# ============================================================================
# Property 36: Transaction Rollback
# ============================================================================

class TestTransactionRollback:
    """Property 36: Database transactions rollback on errors.

    Validates: Requirements 10.4
    """

    @pytest.mark.asyncio
    async def test_rollback_on_exception(self):
        """Test that transaction rolls back on exception."""
        # Mock session
        class MockSession:
            def __init__(self):
                self.committed = False
                self.rolled_back = False

            async def commit(self):
                self.committed = True

            async def rollback(self):
                self.rolled_back = True

        session = MockSession()

        async def failing_operation(sess):
            raise ValueError("Operation failed")

        # Should raise and rollback
        with pytest.raises(ValueError, match="Operation failed"):
            await DatabaseTransactionManager.execute_with_rollback(
                session,
                failing_operation,
                operation_name="test_op"
            )

        # Should have rolled back, not committed
        assert session.rolled_back
        assert not session.committed

    @pytest.mark.asyncio
    async def test_commit_on_success(self):
        """Test that transaction commits on success."""
        class MockSession:
            def __init__(self):
                self.committed = False
                self.rolled_back = False

            async def commit(self):
                self.committed = True

            async def rollback(self):
                self.rolled_back = True

        session = MockSession()

        async def successful_operation(sess):
            return "success"

        result = await DatabaseTransactionManager.execute_with_rollback(
            session,
            successful_operation,
            operation_name="test_op"
        )

        # Should have committed, not rolled back
        assert session.committed
        assert not session.rolled_back
        assert result == "success"


# ============================================================================
# Property 37: Input Validation
# ============================================================================

class TestInputValidation:
    """Property 37: Input validation provides specific error details.

    Validates: Requirements 10.5
    """

    @pytest.mark.asyncio
    @given(
        text_length=st.integers(min_value=0, max_value=200000)
    )
    @settings(max_examples=100, deadline=None)
    async def test_text_length_validation(self, text_length: int):
        """Test that text length validation works correctly."""
        text = "a" * text_length

        result = InputValidationService.validate_annotation_task(
            text=text,
            annotation_type="entity_recognition"
        )

        if text_length == 0:
            # Empty text should fail
            assert not result.valid
            assert any(e.field == "text" and e.constraint == "required" for e in result.errors)
        elif text_length > 100000:
            # Too long should fail
            assert not result.valid
            assert any(
                e.field == "text" and e.constraint == "max_length"
                for e in result.errors
            )
        else:
            # Valid length (but may fail on other fields)
            # Just check text field is ok
            text_errors = [e for e in result.errors if e.field == "text"]
            assert len(text_errors) == 0

    @pytest.mark.asyncio
    @given(
        annotation_type=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=100, deadline=None)
    async def test_annotation_type_validation(self, annotation_type: str):
        """Test that annotation type validation works correctly."""
        result = InputValidationService.validate_annotation_task(
            text="Test text",
            annotation_type=annotation_type
        )

        valid_types = [
            "entity_recognition",
            "classification",
            "sentiment",
            "relation_extraction",
            "text_generation",
        ]

        if annotation_type in valid_types:
            # Valid type - no error for this field
            type_errors = [e for e in result.errors if e.field == "annotation_type"]
            assert len(type_errors) == 0
        else:
            # Invalid type
            assert not result.valid
            assert any(
                e.field == "annotation_type" and e.constraint == "enum"
                for e in result.errors
            )

    @pytest.mark.asyncio
    @given(
        batch_size=st.integers(min_value=-10, max_value=2000)
    )
    @settings(max_examples=100, deadline=None)
    async def test_batch_size_validation(self, batch_size: int):
        """Test that batch size validation enforces range."""
        result = InputValidationService.validate_batch_size(batch_size)

        if batch_size < 1:
            assert not result.valid
            assert any(e.constraint == "min_value" for e in result.errors)
        elif batch_size > 1000:
            assert not result.valid
            assert any(e.constraint == "max_value" for e in result.errors)
        else:
            assert result.valid
            assert len(result.errors) == 0

    @pytest.mark.asyncio
    @given(
        threshold=st.floats(min_value=-1.0, max_value=2.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100, deadline=None)
    async def test_confidence_threshold_validation(self, threshold: float):
        """Test that confidence threshold validation enforces 0-1 range."""
        result = InputValidationService.validate_confidence_threshold(threshold)

        if threshold < 0.0 or threshold > 1.0:
            assert not result.valid
            assert any(e.constraint == "range" for e in result.errors)
        else:
            assert result.valid
            assert len(result.errors) == 0


# ============================================================================
# Property 38: Error Logging and Notification
# ============================================================================

class TestErrorLoggingAndNotification:
    """Property 38: Errors logged with full context and notifications sent.

    Validates: Requirements 10.6
    """

    @pytest.mark.asyncio
    @given(
        num_errors=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=100, deadline=None)
    async def test_error_logging_completeness(self, num_errors: int):
        """Test that all errors are logged with full context."""
        await reset_resilience_services()

        service = ErrorNotificationService()

        error_ids = []

        # Log multiple errors
        for i in range(num_errors):
            error_id = await service.log_error(
                category=ErrorCategory.LLM_API,
                severity=ErrorSeverity.ERROR,
                operation=f"operation_{i}",
                error=ValueError(f"Error {i}"),
                context={"index": i},
                retry_count=i % 3,
            )
            error_ids.append(error_id)

        # All errors should be in log
        all_errors = await service.get_errors()
        assert len(all_errors) == num_errors

        # Each error should have required fields
        for error in all_errors:
            assert error.error_id in error_ids
            assert error.category == ErrorCategory.LLM_API
            assert error.severity == ErrorSeverity.ERROR
            assert error.error_message.startswith("Error")
            assert error.error_type == "ValueError"
            assert "index" in error.context

    @pytest.mark.asyncio
    async def test_critical_error_notification(self):
        """Test that critical errors trigger notifications."""
        await reset_resilience_services()

        service = ErrorNotificationService()

        # Register notification callback
        notification_received = [False]
        received_record = [None]

        async def notification_callback(record):
            notification_received[0] = True
            received_record[0] = record

        await service.register_notification_callback(notification_callback)

        # Log critical error
        error_id = await service.log_error(
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            operation="critical_operation",
            error=Exception("Critical error"),
        )

        # Wait for async callback
        await asyncio.sleep(0.1)

        # Should have received notification
        assert notification_received[0]
        assert received_record[0] is not None
        assert received_record[0].error_id == error_id
        assert received_record[0].severity == ErrorSeverity.CRITICAL

    @pytest.mark.asyncio
    @given(
        severity=st.sampled_from([
            ErrorSeverity.DEBUG,
            ErrorSeverity.INFO,
            ErrorSeverity.WARNING,
            ErrorSeverity.ERROR,
            ErrorSeverity.CRITICAL,
        ])
    )
    @settings(max_examples=100, deadline=None)
    async def test_error_filtering_by_severity(self, severity: ErrorSeverity):
        """Test that errors can be filtered by severity."""
        await reset_resilience_services()

        service = ErrorNotificationService()

        # Log errors of different severities
        severities = [
            ErrorSeverity.DEBUG,
            ErrorSeverity.INFO,
            ErrorSeverity.WARNING,
            ErrorSeverity.ERROR,
            ErrorSeverity.CRITICAL,
        ]

        for sev in severities:
            await service.log_error(
                category=ErrorCategory.VALIDATION,
                severity=sev,
                operation="test_op",
                error=ValueError(f"{sev.value} error"),
            )

        # Filter by severity
        filtered = await service.get_errors(severity=severity)

        # Should only get errors of specified severity
        assert all(e.severity == severity for e in filtered)
        assert len(filtered) >= 1

    @pytest.mark.asyncio
    async def test_error_resolution_marking(self):
        """Test that errors can be marked as resolved."""
        await reset_resilience_services()

        service = ErrorNotificationService()

        # Log error
        error_id = await service.log_error(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.ERROR,
            operation="test_op",
            error=ConnectionError("Network error"),
        )

        # Should be unresolved
        unresolved = await service.get_errors(unresolved_only=True)
        assert len(unresolved) == 1
        assert unresolved[0].error_id == error_id

        # Mark resolved
        await service.mark_resolved(error_id)

        # Should no longer be in unresolved list
        unresolved = await service.get_errors(unresolved_only=True)
        assert len(unresolved) == 0

        # Should still be in all errors
        all_errors = await service.get_errors()
        assert len(all_errors) == 1
        assert all_errors[0].resolved


# ============================================================================
# Helper functions for running async tests
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
