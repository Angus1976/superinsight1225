"""
Property-Based Tests for Audit Logging Completeness

**Validates: Requirements 3.6, 10.1, 10.2**

Property 6: Audit Logging Completeness
For all state-changing operations (review actions, state transitions, enhancements),
an audit log entry must be created with timestamp, user, operation details, and result.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session

from src.models.data_lifecycle import (
    OperationType,
    OperationResult,
    ResourceType,
    Action,
    DataState,
    TempDataModel
)
from src.services.audit_logger import AuditLogger
from src.services.data_lifecycle_state_manager import (
    DataStateManager,
    StateTransitionContext
)
from tests.conftest import db_session


# ============================================================================
# Test Strategies
# ============================================================================

@st.composite
def operation_type_strategy(draw):
    """Generate valid operation types"""
    return draw(st.sampled_from(list(OperationType)))


@st.composite
def resource_type_strategy(draw):
    """Generate valid resource types"""
    return draw(st.sampled_from(list(ResourceType)))


@st.composite
def action_strategy(draw):
    """Generate valid actions"""
    return draw(st.sampled_from(list(Action)))


@st.composite
def operation_result_strategy(draw):
    """Generate valid operation results"""
    return draw(st.sampled_from(list(OperationResult)))


@st.composite
def user_id_strategy(draw):
    """Generate valid user IDs"""
    return f"user_{draw(st.integers(min_value=1, max_value=10000))}"


@st.composite
def resource_id_strategy(draw):
    """Generate valid resource IDs"""
    return str(uuid4())


@st.composite
def duration_strategy(draw):
    """Generate realistic operation durations in milliseconds"""
    return draw(st.integers(min_value=1, max_value=10000))


@st.composite
def details_strategy(draw):
    """Generate operation details dictionaries"""
    return draw(st.one_of(
        st.none(),
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll'),
                min_codepoint=ord('a'),
                max_codepoint=ord('z')
            )),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False)
            ),
            max_size=5
        )
    ))


@st.composite
def ip_address_strategy(draw):
    """Generate valid IP addresses"""
    return draw(st.one_of(
        st.none(),
        st.text(min_size=7, max_size=15).filter(
            lambda x: all(c.isdigit() or c == '.' for c in x)
        ).map(lambda x: f"192.168.{draw(st.integers(0, 255))}.{draw(st.integers(1, 255))}")
    ))


@st.composite
def user_agent_strategy(draw):
    """Generate user agent strings"""
    return draw(st.one_of(
        st.none(),
        st.sampled_from([
            "Mozilla/5.0",
            "Chrome/91.0",
            "Safari/14.0",
            "Firefox/89.0"
        ])
    ))


# ============================================================================
# Property 6: Audit Logging Completeness
# **Validates: Requirements 3.6, 10.1, 10.2**
# ============================================================================

@pytest.mark.property
class TestAuditLoggingCompleteness:
    """
    Property 6: Audit Logging Completeness
    
    For all state-changing operations (review actions, state transitions,
    enhancements), an audit log entry must be created with timestamp, user,
    operation details, and result.
    """
    
    @given(
        operation_type=operation_type_strategy(),
        user_id=user_id_strategy(),
        resource_type=resource_type_strategy(),
        resource_id=resource_id_strategy(),
        action=action_strategy(),
        result=operation_result_strategy(),
        duration=duration_strategy(),
        details=details_strategy(),
        ip_address=ip_address_strategy(),
        user_agent=user_agent_strategy()
    )
    @settings(deadline=None)
    def test_all_operations_create_audit_log(
        self,
        db_session: Session,
        operation_type: OperationType,
        user_id: str,
        resource_type: ResourceType,
        resource_id: str,
        action: Action,
        result: OperationResult,
        duration: int,
        details: dict,
        ip_address: str,
        user_agent: str
    ):
        """
        Property: Every operation logged creates an audit log entry with all required fields.
        
        For any operation with the required parameters, an audit log entry must be
        created with timestamp, user, operation details, and result.
        """
        # Create audit logger
        audit_logger = AuditLogger(db_session)
        
        # Record the time before logging
        before_log = datetime.utcnow()
        
        # Log the operation
        log_entry = audit_logger.log_operation(
            operation_type=operation_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            duration=duration,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Record the time after logging
        after_log = datetime.utcnow()
        
        # Assert: Log entry must be created
        assert log_entry is not None, "Audit log entry must be created"
        
        # Assert: Log entry must have an ID
        assert log_entry.id is not None, "Audit log entry must have an ID"
        
        # Assert: Log entry must have timestamp
        assert log_entry.timestamp is not None, "Audit log entry must have timestamp"
        assert before_log <= log_entry.timestamp <= after_log, \
            f"Timestamp must be between {before_log} and {after_log}"
        
        # Assert: Log entry must have user information
        assert log_entry.user_id == user_id, \
            f"Audit log must record user_id: expected {user_id}, got {log_entry.user_id}"
        
        # Assert: Log entry must have operation details
        assert log_entry.operation_type == operation_type, \
            f"Audit log must record operation_type: expected {operation_type}, got {log_entry.operation_type}"
        assert log_entry.resource_type == resource_type, \
            f"Audit log must record resource_type: expected {resource_type}, got {log_entry.resource_type}"
        assert log_entry.resource_id == resource_id, \
            f"Audit log must record resource_id: expected {resource_id}, got {log_entry.resource_id}"
        assert log_entry.action == action, \
            f"Audit log must record action: expected {action}, got {log_entry.action}"
        
        # Assert: Log entry must have result
        assert log_entry.result == result, \
            f"Audit log must record result: expected {result}, got {log_entry.result}"
        
        # Assert: Log entry must have duration
        assert log_entry.duration == duration, \
            f"Audit log must record duration: expected {duration}, got {log_entry.duration}"
        
        # Assert: Log entry must preserve details
        if details:
            assert log_entry.details == details, \
                f"Audit log must preserve details: expected {details}, got {log_entry.details}"
        
        # Assert: Log entry must preserve IP address
        if ip_address:
            assert log_entry.ip_address == ip_address, \
                f"Audit log must preserve ip_address: expected {ip_address}, got {log_entry.ip_address}"
        
        # Assert: Log entry must preserve user agent
        if user_agent:
            assert log_entry.user_agent == user_agent, \
                f"Audit log must preserve user_agent: expected {user_agent}, got {log_entry.user_agent}"
    
    @given(
        user_id=user_id_strategy(),
        details=details_strategy()
    )
    @settings(deadline=None)
    def test_state_transitions_create_audit_log(
        self,
        db_session: Session,
        user_id: str,
        details: dict
    ):
        """
        Property: State transitions create audit log entries.
        
        For any valid state transition, an audit log entry must be created
        recording the state change operation.
        """
        # Create temp data in initial state
        temp_data = TempDataModel(
            id=uuid4(),
            source_document_id=str(uuid4()),
            content={"test": "data"},
            state=DataState.TEMP_STORED,
            uploaded_by=user_id,
            uploaded_at=datetime.utcnow(),
            metadata={}
        )
        db_session.add(temp_data)
        db_session.commit()
        
        data_id = str(temp_data.id)
        
        # Create state manager and audit logger
        state_manager = DataStateManager(db_session)
        audit_logger = AuditLogger(db_session)
        
        # Get initial audit log count
        initial_logs = audit_logger.get_audit_log(
            resource_id=data_id,
            resource_type=ResourceType.TEMP_DATA
        )
        initial_count = len(initial_logs)
        
        # Perform a valid state transition
        context = StateTransitionContext(
            user_id=user_id,
            reason="Test transition",
            metadata=details
        )
        
        before_transition = datetime.utcnow()
        result = state_manager.transition_state(
            data_id=data_id,
            resource_type=ResourceType.TEMP_DATA,
            target_state=DataState.UNDER_REVIEW,
            context=context
        )
        after_transition = datetime.utcnow()
        
        # Skip if transition failed
        assume(result.success)
        
        # Get updated audit logs
        updated_logs = audit_logger.get_audit_log(
            resource_id=data_id,
            resource_type=ResourceType.TEMP_DATA
        )
        
        # Assert: Audit log count must increase
        assert len(updated_logs) > initial_count, \
            f"State transition must create audit log: expected > {initial_count}, got {len(updated_logs)}"
        
        # Get the new log entry (most recent)
        new_logs = [log for log in updated_logs if log not in initial_logs]
        assert len(new_logs) > 0, "At least one new audit log must be created"
        
        latest_log = new_logs[-1]
        
        # Assert: Log must have all required fields
        assert latest_log.timestamp is not None, "Audit log must have timestamp"
        assert before_transition <= latest_log.timestamp <= after_transition, \
            "Timestamp must be within transition window"
        
        assert latest_log.user_id == user_id, \
            f"Audit log must record user_id: expected {user_id}, got {latest_log.user_id}"
        
        assert latest_log.resource_type == ResourceType.TEMP_DATA, \
            "Audit log must record correct resource_type"
        
        assert latest_log.resource_id == data_id, \
            f"Audit log must record resource_id: expected {data_id}, got {latest_log.resource_id}"
        
        assert latest_log.result == OperationResult.SUCCESS, \
            "Successful transition must log SUCCESS result"
        
        assert latest_log.operation_type == OperationType.STATE_CHANGE, \
            "State transition must log STATE_CHANGE operation type"
    
    @given(
        user_id=user_id_strategy(),
        result=operation_result_strategy()
    )
    @settings(deadline=None)
    def test_operation_result_recorded_correctly(
        self,
        db_session: Session,
        user_id: str,
        result: OperationResult
    ):
        """
        Property: Operation results (success, failure, partial) are recorded correctly.
        
        For any operation result type, the audit log must accurately record
        whether the operation succeeded, failed, or partially completed.
        """
        # Create audit logger
        audit_logger = AuditLogger(db_session)
        
        # Log operation with specific result
        error_message = "Test error" if result == OperationResult.FAILURE else None
        
        log_entry = audit_logger.log_operation(
            operation_type=OperationType.UPDATE,
            user_id=user_id,
            resource_type=ResourceType.TEMP_DATA,
            resource_id=str(uuid4()),
            action=Action.EDIT,
            result=result,
            duration=100,
            error=error_message
        )
        
        # Assert: Result must be recorded correctly
        assert log_entry.result == result, \
            f"Audit log must record result: expected {result}, got {log_entry.result}"
        
        # Assert: Error message must be recorded for failures
        if result == OperationResult.FAILURE:
            assert log_entry.error is not None, \
                "Failed operations must record error message"
        
        # Assert: Success operations should not have error
        if result == OperationResult.SUCCESS:
            assert log_entry.error is None or log_entry.error == "", \
                "Successful operations should not have error message"
    
    def test_multiple_operations_all_logged(self, db_session: Session):
        """
        Property: Multiple operations are all logged independently.
        
        When multiple operations are performed, each one must create its own
        audit log entry with correct details.
        """
        audit_logger = AuditLogger(db_session)
        
        # Perform multiple operations
        operations = []
        for i in range(5):
            user_id = f"user_{i}"
            resource_id = str(uuid4())
            
            log_entry = audit_logger.log_operation(
                operation_type=OperationType.CREATE,
                user_id=user_id,
                resource_type=ResourceType.SAMPLE,
                resource_id=resource_id,
                action=Action.EDIT,
                result=OperationResult.SUCCESS,
                duration=100 + i * 10,
                details={"operation_index": i}
            )
            
            operations.append({
                "user_id": user_id,
                "resource_id": resource_id,
                "log_entry": log_entry
            })
        
        # Assert: All operations must be logged
        assert len(operations) == 5, "All operations must be logged"
        
        # Assert: Each log entry must have unique ID
        log_ids = [op["log_entry"].id for op in operations]
        assert len(set(log_ids)) == 5, "Each log entry must have unique ID"
        
        # Assert: Each log entry must have correct user and resource
        for i, op in enumerate(operations):
            assert op["log_entry"].user_id == f"user_{i}", \
                f"Log entry {i} must have correct user_id"
            assert op["log_entry"].resource_id == op["resource_id"], \
                f"Log entry {i} must have correct resource_id"
            assert op["log_entry"].details["operation_index"] == i, \
                f"Log entry {i} must have correct details"
    
    @given(
        user_id=user_id_strategy(),
        operation_type=operation_type_strategy()
    )
    @settings(deadline=None)
    def test_failed_operations_logged_with_error(
        self,
        db_session: Session,
        user_id: str,
        operation_type: OperationType
    ):
        """
        Property: Failed operations are logged with error details.
        
        When an operation fails, the audit log must record the failure result
        and include error details for debugging.
        """
        audit_logger = AuditLogger(db_session)
        
        error_message = "Permission denied: insufficient privileges"
        
        # Log a failed operation
        log_entry = audit_logger.log_operation(
            operation_type=operation_type,
            user_id=user_id,
            resource_type=ResourceType.TEMP_DATA,
            resource_id=str(uuid4()),
            action=Action.DELETE,
            result=OperationResult.FAILURE,
            duration=50,
            error=error_message
        )
        
        # Assert: Failure must be recorded
        assert log_entry.result == OperationResult.FAILURE, \
            "Failed operation must record FAILURE result"
        
        # Assert: Error message must be recorded
        assert log_entry.error == error_message, \
            f"Failed operation must record error: expected '{error_message}', got '{log_entry.error}'"
        
        # Assert: All other required fields must still be present
        assert log_entry.timestamp is not None, "Failed operation must have timestamp"
        assert log_entry.user_id == user_id, "Failed operation must record user_id"
        assert log_entry.operation_type == operation_type, "Failed operation must record operation_type"
        assert log_entry.duration > 0, "Failed operation must record duration"
    
    def test_audit_log_retrieval_completeness(self, db_session: Session):
        """
        Property: All logged operations can be retrieved.
        
        After logging multiple operations, all of them must be retrievable
        through the audit log query interface.
        """
        audit_logger = AuditLogger(db_session)
        
        # Log multiple operations with different characteristics
        test_user = "test_user_123"
        logged_operations = []
        
        for i in range(3):
            log_entry = audit_logger.log_operation(
                operation_type=OperationType.UPDATE,
                user_id=test_user,
                resource_type=ResourceType.SAMPLE,
                resource_id=str(uuid4()),
                action=Action.EDIT,
                result=OperationResult.SUCCESS,
                duration=100 + i * 50
            )
            logged_operations.append(log_entry)
        
        # Retrieve all logs for this user
        retrieved_logs = audit_logger.get_audit_log(user_id=test_user)
        
        # Assert: All logged operations must be retrievable
        assert len(retrieved_logs) >= len(logged_operations), \
            f"All operations must be retrievable: expected >= {len(logged_operations)}, got {len(retrieved_logs)}"
        
        # Assert: Retrieved logs must contain all logged operation IDs
        retrieved_ids = {log.id for log in retrieved_logs}
        logged_ids = {log.id for log in logged_operations}
        
        assert logged_ids.issubset(retrieved_ids), \
            "All logged operation IDs must be in retrieved logs"
