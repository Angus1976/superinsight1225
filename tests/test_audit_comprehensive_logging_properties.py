"""
Property-based tests for comprehensive audit logging.

**Validates: Requirements 8.1, 8.2**

Property 23: Comprehensive Audit Logging
For any gateway data access or operation, an audit log entry should be created
containing gateway_id, skill_name, timestamp, user/channel, resource, action,
operation_type, parameters, result_status, and cryptographic signature.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from sqlalchemy.orm import Session

from src.ai_integration.audit_service import AuditService

# Import fixtures from conftest_audit
pytest_plugins = ["tests.conftest_audit"]


# Strategy for generating gateway IDs
gateway_ids = st.uuids().map(str)

# Strategy for generating tenant IDs
tenant_ids = st.uuids().map(str)

# Strategy for generating skill names
skill_names = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"),
    min_size=3,
    max_size=50
)

# Strategy for generating resource names
resources = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="/_-"),
    min_size=5,
    max_size=100
)

# Strategy for generating actions
actions = st.sampled_from(["query", "create", "update", "delete", "export", "list"])

# Strategy for generating operation types
operation_types = st.sampled_from([
    "data_access",
    "skill_execution",
    "configuration_change",
    "authentication",
    "authorization"
])

# Strategy for generating user identifiers
user_identifiers = st.one_of(
    st.none(),
    st.emails(),
    st.text(min_size=5, max_size=50).map(lambda x: f"user_{x}")
)

# Strategy for generating channels
channels = st.one_of(
    st.none(),
    st.sampled_from(["whatsapp", "telegram", "slack", "discord", "web"])
)

# Strategy for generating metadata with required fields
@st.composite
def metadata_with_skill(draw):
    """Generate metadata that includes skill_name and parameters."""
    skill_name = draw(skill_names)
    
    # Generate parameters
    param_keys = draw(st.lists(
        st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll"))),
        min_size=0,
        max_size=5,
        unique=True
    ))
    
    parameters = {}
    for key in param_keys:
        value = draw(st.one_of(
            st.text(max_size=50),
            st.integers(),
            st.booleans(),
            st.floats(allow_nan=False, allow_infinity=False)
        ))
        parameters[key] = value
    
    return {
        "skill_name": skill_name,
        "parameters": parameters,
        "additional_info": draw(st.text(max_size=100))
    }

# Strategy for success status
success_status = st.booleans()

# Strategy for error messages
error_messages = st.one_of(
    st.none(),
    st.text(min_size=10, max_size=200)
)


@pytest.fixture
def audit_service():
    """Create audit service instance."""
    return AuditService(secret_key="test_property_secret")


class TestComprehensiveAuditLogging:
    """Property-based tests for comprehensive audit logging."""

    @given(
        gateway_id=gateway_ids,
        tenant_id=tenant_ids,
        resource=resources,
        action=actions,
        metadata=metadata_with_skill(),
        user_identifier=user_identifiers,
        channel=channels,
        success=success_status,
        error_message=error_messages
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    def test_all_required_fields_present(
        self,
        audit_service,
        db_session: Session,
        gateway_id,
        tenant_id,
        resource,
        action,
        metadata,
        user_identifier,
        channel,
        success,
        error_message
    ):
        """
        Property 23: Comprehensive Audit Logging
        
        For any gateway operation, verify that all required fields are present
        in the audit log entry.
        
        **Validates: Requirements 8.1, 8.2**
        """
        # Ensure error_message is only present when success is False
        if success:
            error_message = None
        
        # Log the operation
        log_entry = audit_service.log_data_access(
            gateway_id=gateway_id,
            tenant_id=tenant_id,
            resource=resource,
            action=action,
            metadata=metadata,
            db=db_session,
            user_identifier=user_identifier,
            channel=channel,
            success=success,
            error_message=error_message
        )
        
        # Verify all required fields are present
        assert log_entry.id is not None, "Log entry must have an ID"
        assert log_entry.gateway_id == gateway_id, "Gateway ID must match"
        assert log_entry.tenant_id == tenant_id, "Tenant ID must match"
        assert log_entry.timestamp is not None, "Timestamp must be present"
        assert isinstance(log_entry.timestamp, datetime), "Timestamp must be datetime"
        
        # Verify resource and action
        assert log_entry.resource == resource, "Resource must match"
        assert log_entry.action == action, "Action must match"
        
        # Verify operation type
        assert log_entry.event_type is not None, "Operation type must be present"
        assert log_entry.event_type == "data_access", "Event type must be set"
        
        # Verify metadata contains required fields
        assert log_entry.event_metadata is not None, "Metadata must be present"
        assert "skill_name" in log_entry.event_metadata, "Skill name must be in metadata"
        assert "parameters" in log_entry.event_metadata, "Parameters must be in metadata"
        assert log_entry.event_metadata["skill_name"] == metadata["skill_name"]
        assert log_entry.event_metadata["parameters"] == metadata["parameters"]
        
        # Verify user/channel information
        assert log_entry.user_identifier == user_identifier, "User identifier must match"
        assert log_entry.channel == channel, "Channel must match"
        
        # Verify result status
        assert log_entry.success == success, "Success status must match"
        if not success:
            assert log_entry.error_message == error_message, "Error message must match when failed"
        else:
            assert log_entry.error_message is None, "Error message must be None when successful"
        
        # Verify cryptographic signature
        assert log_entry.signature is not None, "Signature must be present"
        assert len(log_entry.signature) == 64, "Signature must be SHA256 hex (64 chars)"
        assert audit_service.verify_signature(log_entry), "Signature must be valid"

    @given(
        gateway_id=gateway_ids,
        tenant_id=tenant_ids,
        event_type=st.text(min_size=5, max_size=50),
        details=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(max_size=100), st.integers(), st.booleans()),
            min_size=1,
            max_size=5
        ),
        user_identifier=user_identifiers
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    def test_security_event_logging_completeness(
        self,
        audit_service,
        db_session: Session,
        gateway_id,
        tenant_id,
        event_type,
        details,
        user_identifier
    ):
        """
        Property 23: Comprehensive Audit Logging (Security Events)
        
        For any security event, verify that all required fields are present
        in the audit log entry.
        
        **Validates: Requirements 8.1, 8.2**
        """
        # Log security event
        log_entry = audit_service.log_security_event(
            gateway_id=gateway_id,
            tenant_id=tenant_id,
            event_type=event_type,
            details=details,
            db=db_session,
            user_identifier=user_identifier
        )
        
        # Verify all required fields
        assert log_entry.id is not None
        assert log_entry.gateway_id == gateway_id
        assert log_entry.tenant_id == tenant_id
        assert log_entry.timestamp is not None
        assert isinstance(log_entry.timestamp, datetime)
        
        # Verify event details
        assert log_entry.event_type == event_type
        assert log_entry.resource == "security"
        assert log_entry.action == "monitor"
        assert log_entry.event_metadata == details
        
        # Verify user information
        assert log_entry.user_identifier == user_identifier
        
        # Verify success status (security events are always logged as successful)
        assert log_entry.success is True
        
        # Verify signature
        assert log_entry.signature is not None
        assert len(log_entry.signature) == 64
        assert audit_service.verify_signature(log_entry)

    @given(
        operations=st.lists(
            st.tuples(
                gateway_ids,
                tenant_ids,
                resources,
                actions,
                metadata_with_skill()
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    def test_multiple_operations_all_logged(
        self,
        audit_service,
        db_session: Session,
        operations
    ):
        """
        Property 23: Comprehensive Audit Logging (Multiple Operations)
        
        For any sequence of gateway operations, verify that all operations
        are logged with complete metadata.
        
        **Validates: Requirements 8.1, 8.2**
        """
        logged_entries = []
        
        # Log all operations
        for gateway_id, tenant_id, resource, action, metadata in operations:
            log_entry = audit_service.log_data_access(
                gateway_id=gateway_id,
                tenant_id=tenant_id,
                resource=resource,
                action=action,
                metadata=metadata,
                db=db_session,
                success=True
            )
            logged_entries.append(log_entry)
        
        # Verify all operations were logged
        assert len(logged_entries) == len(operations)
        
        # Verify each log entry has all required fields
        for i, log_entry in enumerate(logged_entries):
            gateway_id, tenant_id, resource, action, metadata = operations[i]
            
            assert log_entry.gateway_id == gateway_id
            assert log_entry.tenant_id == tenant_id
            assert log_entry.resource == resource
            assert log_entry.action == action
            assert log_entry.event_metadata["skill_name"] == metadata["skill_name"]
            assert log_entry.event_metadata["parameters"] == metadata["parameters"]
            assert log_entry.signature is not None
            assert audit_service.verify_signature(log_entry)
        
        # Verify all entries can be queried back
        all_logs = audit_service.query_audit_logs(
            db=db_session,
            limit=len(operations)
        )
        
        assert len(all_logs) >= len(operations)

    @given(
        gateway_id=gateway_ids,
        tenant_id=tenant_ids,
        resource=resources,
        action=actions,
        metadata=metadata_with_skill()
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    def test_signature_prevents_tampering(
        self,
        audit_service,
        db_session: Session,
        gateway_id,
        tenant_id,
        resource,
        action,
        metadata
    ):
        """
        Property 23: Comprehensive Audit Logging (Tamper Detection)
        
        For any logged operation, verify that the cryptographic signature
        can detect tampering with the log entry.
        
        **Validates: Requirements 8.1, 8.2, 8.3**
        """
        # Log operation
        log_entry = audit_service.log_data_access(
            gateway_id=gateway_id,
            tenant_id=tenant_id,
            resource=resource,
            action=action,
            metadata=metadata,
            db=db_session,
            success=True
        )
        
        # Verify original signature is valid
        assert audit_service.verify_signature(log_entry)
        
        # Attempt to tamper with various fields
        original_metadata = log_entry.event_metadata.copy()
        log_entry.event_metadata = {"tampered": "data"}
        assert not audit_service.verify_signature(log_entry), "Tampering with metadata should be detected"
        
        # Restore and tamper with another field
        log_entry.event_metadata = original_metadata
        original_action = log_entry.action
        log_entry.action = "tampered_action"
        assert not audit_service.verify_signature(log_entry), "Tampering with action should be detected"
        
        # Restore original
        log_entry.action = original_action
        assert audit_service.verify_signature(log_entry), "Restored entry should be valid"
