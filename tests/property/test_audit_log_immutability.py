"""
Property-Based Tests for Audit Log Immutability

**Validates: Requirements 10.6**

Property 25: Audit Log Immutability
For any audit log entry, attempts to modify or delete it should be prevented.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.models.data_lifecycle import (
    AuditLogModel,
    OperationType,
    OperationResult,
    ResourceType,
    Action
)
from src.services.audit_logger import AuditLogger


# ============================================================================
# Test Strategies
# ============================================================================

@st.composite
def audit_log_data_strategy(draw):
    """Generate random audit log entry data"""
    return {
        "operation_type": draw(st.sampled_from(list(OperationType))),
        "user_id": f"user_{draw(st.integers(min_value=1, max_value=10000))}",
        "resource_type": draw(st.sampled_from(list(ResourceType))),
        "resource_id": str(uuid4()),
        "action": draw(st.sampled_from(list(Action))),
        "result": draw(st.sampled_from(list(OperationResult))),
        "duration": draw(st.integers(min_value=1, max_value=10000)),
        "error": draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        "details": draw(st.one_of(
            st.none(),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.one_of(st.text(max_size=50), st.integers()),
                max_size=3
            )
        )),
        "ip_address": draw(st.one_of(
            st.none(),
            st.text(min_size=7, max_size=15).map(
                lambda x: f"192.168.{draw(st.integers(0, 255))}.{draw(st.integers(1, 255))}"
            )
        )),
        "user_agent": draw(st.one_of(
            st.none(),
            st.sampled_from(["Mozilla/5.0", "Chrome/91.0", "Safari/14.0"])
        ))
    }


@st.composite
def field_modification_strategy(draw):
    """Generate field modifications to attempt on audit logs"""
    field = draw(st.sampled_from([
        "operation_type",
        "user_id",
        "resource_type",
        "resource_id",
        "action",
        "result",
        "duration",
        "error",
        "details",
        "ip_address",
        "user_agent",
        "timestamp"
    ]))
    
    # Generate new value based on field type
    if field == "operation_type":
        new_value = draw(st.sampled_from(list(OperationType)))
    elif field == "user_id":
        new_value = f"modified_user_{draw(st.integers(1, 1000))}"
    elif field == "resource_type":
        new_value = draw(st.sampled_from(list(ResourceType)))
    elif field == "resource_id":
        new_value = str(uuid4())
    elif field == "action":
        new_value = draw(st.sampled_from(list(Action)))
    elif field == "result":
        new_value = draw(st.sampled_from(list(OperationResult)))
    elif field == "duration":
        new_value = draw(st.integers(min_value=1, max_value=10000))
    elif field == "error":
        new_value = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    elif field == "details":
        new_value = {"modified": True}
    elif field == "ip_address":
        new_value = "10.0.0.1"
    elif field == "user_agent":
        new_value = "Modified Agent"
    elif field == "timestamp":
        new_value = datetime.utcnow()
    
    return field, new_value


# ============================================================================
# Property 25: Audit Log Immutability
# **Validates: Requirements 10.6**
# ============================================================================

@pytest.mark.property
class TestAuditLogImmutability:
    """
    Property 25: Audit Log Immutability
    
    For any audit log entry, attempts to modify or delete it should be prevented.
    The system must ensure audit logs are immutable and tamper-proof.
    """
    
    @given(
        log_data=audit_log_data_strategy(),
        modification=field_modification_strategy()
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_audit_log_fields_cannot_be_modified(
        self,
        db_session: Session,
        log_data: dict,
        modification: tuple
    ):
        """
        Property: Audit log fields cannot be modified after creation.
        
        For any audit log entry, attempting to modify any field should either
        fail or have no effect. The original values must remain unchanged.
        """
        # Create audit logger and log an operation
        audit_logger = AuditLogger(db_session)
        
        log_entry = audit_logger.log_operation(
            operation_type=log_data["operation_type"],
            user_id=log_data["user_id"],
            resource_type=log_data["resource_type"],
            resource_id=log_data["resource_id"],
            action=log_data["action"],
            result=log_data["result"],
            duration=log_data["duration"],
            error=log_data["error"],
            details=log_data["details"],
            ip_address=log_data["ip_address"],
            user_agent=log_data["user_agent"]
        )
        
        # Store original values
        original_id = log_entry.id
        original_timestamp = log_entry.timestamp
        original_values = {
            "operation_type": log_entry.operation_type,
            "user_id": log_entry.user_id,
            "resource_type": log_entry.resource_type,
            "resource_id": log_entry.resource_id,
            "action": log_entry.action,
            "result": log_entry.result,
            "duration": log_entry.duration,
            "error": log_entry.error,
            "details": log_entry.details,
            "ip_address": log_entry.ip_address,
            "user_agent": log_entry.user_agent,
            "timestamp": log_entry.timestamp
        }
        
        # Attempt to modify a field directly in the database
        field_name, new_value = modification
        
        # Get the database model instance
        db_log = db_session.query(AuditLogModel).filter(
            AuditLogModel.id == original_id
        ).first()
        
        assert db_log is not None, "Audit log must exist in database"
        
        # Attempt modification
        try:
            setattr(db_log, field_name, new_value)
            db_session.commit()
            
            # If commit succeeded, verify the value was NOT actually changed
            # (This tests application-level immutability enforcement)
            db_session.refresh(db_log)
            
            # The value should remain unchanged
            current_value = getattr(db_log, field_name)
            
            # For enum types, compare values
            if hasattr(original_values[field_name], 'value'):
                assert current_value == original_values[field_name], \
                    f"Audit log field '{field_name}' must remain immutable: " \
                    f"original={original_values[field_name]}, current={current_value}"
            else:
                assert current_value == original_values[field_name], \
                    f"Audit log field '{field_name}' must remain immutable: " \
                    f"original={original_values[field_name]}, current={current_value}"
        
        except (IntegrityError, Exception) as e:
            # Modification failed - this is acceptable for immutability
            db_session.rollback()
            
            # Verify the log entry still exists with original values
            db_log = db_session.query(AuditLogModel).filter(
                AuditLogModel.id == original_id
            ).first()
            
            assert db_log is not None, \
                "Audit log must still exist after failed modification attempt"
            
            # Verify all original values are preserved
            for field, original_value in original_values.items():
                current_value = getattr(db_log, field)
                if hasattr(original_value, 'value'):
                    assert current_value == original_value, \
                        f"Field '{field}' must preserve original value after failed modification"
                else:
                    assert current_value == original_value, \
                        f"Field '{field}' must preserve original value after failed modification"
    
    @given(log_data=audit_log_data_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_audit_log_cannot_be_deleted(
        self,
        db_session: Session,
        log_data: dict
    ):
        """
        Property: Audit log entries cannot be deleted.
        
        For any audit log entry, attempting to delete it should either fail
        or have no effect. The log entry must remain in the database.
        """
        # Create audit logger and log an operation
        audit_logger = AuditLogger(db_session)
        
        log_entry = audit_logger.log_operation(
            operation_type=log_data["operation_type"],
            user_id=log_data["user_id"],
            resource_type=log_data["resource_type"],
            resource_id=log_data["resource_id"],
            action=log_data["action"],
            result=log_data["result"],
            duration=log_data["duration"],
            error=log_data["error"],
            details=log_data["details"],
            ip_address=log_data["ip_address"],
            user_agent=log_data["user_agent"]
        )
        
        log_id = log_entry.id
        
        # Verify log exists
        db_log = db_session.query(AuditLogModel).filter(
            AuditLogModel.id == log_id
        ).first()
        assert db_log is not None, "Audit log must exist before deletion attempt"
        
        # Attempt to delete the audit log
        try:
            db_session.delete(db_log)
            db_session.commit()
            
            # If deletion succeeded, this violates immutability
            # Check if the log still exists (application-level protection)
            db_log_after = db_session.query(AuditLogModel).filter(
                AuditLogModel.id == log_id
            ).first()
            
            # The log should still exist (immutability enforced)
            assert db_log_after is not None, \
                "Audit log must not be deleted - immutability violated"
        
        except (IntegrityError, Exception) as e:
            # Deletion failed - this is the expected behavior for immutability
            db_session.rollback()
            
            # Verify the log entry still exists
            db_log_after = db_session.query(AuditLogModel).filter(
                AuditLogModel.id == log_id
            ).first()
            
            assert db_log_after is not None, \
                "Audit log must still exist after failed deletion attempt"
            
            # Verify all fields are intact
            assert db_log_after.id == log_id, "Audit log ID must be preserved"
            assert db_log_after.user_id == log_data["user_id"], \
                "Audit log user_id must be preserved"
            assert db_log_after.operation_type == log_data["operation_type"], \
                "Audit log operation_type must be preserved"
    
    @given(log_data=audit_log_data_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_audit_log_timestamp_cannot_be_modified(
        self,
        db_session: Session,
        log_data: dict
    ):
        """
        Property: Audit log timestamps cannot be modified.
        
        The timestamp field is critical for audit trail integrity. Any attempt
        to modify it should fail or have no effect.
        """
        # Create audit logger and log an operation
        audit_logger = AuditLogger(db_session)
        
        log_entry = audit_logger.log_operation(
            operation_type=log_data["operation_type"],
            user_id=log_data["user_id"],
            resource_type=log_data["resource_type"],
            resource_id=log_data["resource_id"],
            action=log_data["action"],
            result=log_data["result"],
            duration=log_data["duration"],
            error=log_data["error"],
            details=log_data["details"],
            ip_address=log_data["ip_address"],
            user_agent=log_data["user_agent"]
        )
        
        original_timestamp = log_entry.timestamp
        log_id = log_entry.id
        
        # Attempt to modify timestamp
        db_log = db_session.query(AuditLogModel).filter(
            AuditLogModel.id == log_id
        ).first()
        
        # Try to change timestamp to a different time
        new_timestamp = datetime(2020, 1, 1, 0, 0, 0)
        
        try:
            db_log.timestamp = new_timestamp
            db_session.commit()
            
            # If commit succeeded, verify timestamp was NOT changed
            db_session.refresh(db_log)
            
            assert db_log.timestamp == original_timestamp, \
                f"Audit log timestamp must remain immutable: " \
                f"original={original_timestamp}, current={db_log.timestamp}"
        
        except (IntegrityError, Exception) as e:
            # Modification failed - this is acceptable
            db_session.rollback()
            
            # Verify timestamp is still original
            db_log = db_session.query(AuditLogModel).filter(
                AuditLogModel.id == log_id
            ).first()
            
            assert db_log.timestamp == original_timestamp, \
                "Audit log timestamp must be preserved after failed modification"
    
    @given(
        log_data1=audit_log_data_strategy(),
        log_data2=audit_log_data_strategy()
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_audit_logs_all_immutable(
        self,
        db_session: Session,
        log_data1: dict,
        log_data2: dict
    ):
        """
        Property: Multiple audit logs are all independently immutable.
        
        When multiple audit log entries exist, each one must be independently
        immutable. Modifications to one should not affect others, and all
        should resist modification attempts.
        """
        # Create audit logger
        audit_logger = AuditLogger(db_session)
        
        # Create two audit log entries
        log1 = audit_logger.log_operation(
            operation_type=log_data1["operation_type"],
            user_id=log_data1["user_id"],
            resource_type=log_data1["resource_type"],
            resource_id=log_data1["resource_id"],
            action=log_data1["action"],
            result=log_data1["result"],
            duration=log_data1["duration"],
            error=log_data1["error"],
            details=log_data1["details"],
            ip_address=log_data1["ip_address"],
            user_agent=log_data1["user_agent"]
        )
        
        log2 = audit_logger.log_operation(
            operation_type=log_data2["operation_type"],
            user_id=log_data2["user_id"],
            resource_type=log_data2["resource_type"],
            resource_id=log_data2["resource_id"],
            action=log_data2["action"],
            result=log_data2["result"],
            duration=log_data2["duration"],
            error=log_data2["error"],
            details=log_data2["details"],
            ip_address=log_data2["ip_address"],
            user_agent=log_data2["user_agent"]
        )
        
        # Store original values
        log1_original = {
            "id": log1.id,
            "user_id": log1.user_id,
            "operation_type": log1.operation_type,
            "timestamp": log1.timestamp
        }
        
        log2_original = {
            "id": log2.id,
            "user_id": log2.user_id,
            "operation_type": log2.operation_type,
            "timestamp": log2.timestamp
        }
        
        # Attempt to modify log1
        db_log1 = db_session.query(AuditLogModel).filter(
            AuditLogModel.id == log1.id
        ).first()
        
        try:
            db_log1.user_id = "hacker_user"
            db_session.commit()
            db_session.refresh(db_log1)
            
            # Verify log1 was not modified
            assert db_log1.user_id == log1_original["user_id"], \
                "Log1 user_id must remain immutable"
        except Exception:
            db_session.rollback()
        
        # Verify both logs still exist with original values
        db_log1_check = db_session.query(AuditLogModel).filter(
            AuditLogModel.id == log1_original["id"]
        ).first()
        
        db_log2_check = db_session.query(AuditLogModel).filter(
            AuditLogModel.id == log2_original["id"]
        ).first()
        
        assert db_log1_check is not None, "Log1 must still exist"
        assert db_log2_check is not None, "Log2 must still exist"
        
        # Verify original values are preserved
        assert db_log1_check.user_id == log1_original["user_id"], \
            "Log1 user_id must be preserved"
        assert db_log1_check.operation_type == log1_original["operation_type"], \
            "Log1 operation_type must be preserved"
        
        assert db_log2_check.user_id == log2_original["user_id"], \
            "Log2 user_id must be preserved"
        assert db_log2_check.operation_type == log2_original["operation_type"], \
            "Log2 operation_type must be preserved"
    
    def test_audit_logger_has_no_update_method(self):
        """
        Property: AuditLogger service should not provide update methods.
        
        The AuditLogger service should only provide methods for creating and
        reading audit logs, not for updating or deleting them.
        """
        # Verify AuditLogger does not have update or delete methods
        audit_logger_methods = dir(AuditLogger)
        
        # Check for suspicious method names
        forbidden_methods = [
            'update_operation',
            'update_log',
            'modify_log',
            'delete_operation',
            'delete_log',
            'remove_log',
            'edit_log'
        ]
        
        for method in forbidden_methods:
            assert method not in audit_logger_methods, \
                f"AuditLogger must not have '{method}' method - violates immutability"
        
        # Verify only safe methods exist
        assert 'log_operation' in audit_logger_methods, \
            "AuditLogger must have 'log_operation' method"
        assert 'get_audit_log' in audit_logger_methods, \
            "AuditLogger must have 'get_audit_log' method"
    
    @given(log_data=audit_log_data_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_audit_log_details_cannot_be_modified(
        self,
        db_session: Session,
        log_data: dict
    ):
        """
        Property: Audit log details (JSON field) cannot be modified.
        
        The details field contains important context about the operation.
        It must be immutable like all other fields.
        """
        # Create audit logger and log an operation with details
        audit_logger = AuditLogger(db_session)
        
        original_details = log_data["details"] or {"original": "data"}
        
        log_entry = audit_logger.log_operation(
            operation_type=log_data["operation_type"],
            user_id=log_data["user_id"],
            resource_type=log_data["resource_type"],
            resource_id=log_data["resource_id"],
            action=log_data["action"],
            result=log_data["result"],
            duration=log_data["duration"],
            details=original_details
        )
        
        log_id = log_entry.id
        
        # Attempt to modify details
        db_log = db_session.query(AuditLogModel).filter(
            AuditLogModel.id == log_id
        ).first()
        
        modified_details = {"modified": "malicious_data", "tampered": True}
        
        try:
            db_log.details = modified_details
            db_session.commit()
            db_session.refresh(db_log)
            
            # Verify details were NOT changed
            assert db_log.details == original_details, \
                f"Audit log details must remain immutable: " \
                f"original={original_details}, current={db_log.details}"
        
        except (IntegrityError, Exception) as e:
            # Modification failed - this is acceptable
            db_session.rollback()
            
            # Verify details are still original
            db_log = db_session.query(AuditLogModel).filter(
                AuditLogModel.id == log_id
            ).first()
            
            assert db_log.details == original_details, \
                "Audit log details must be preserved after failed modification"
