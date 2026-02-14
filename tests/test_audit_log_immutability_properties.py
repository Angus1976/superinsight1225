"""
Property-based tests for audit log immutability.

Tests that audit logs cannot be modified after creation and that
signature verification detects any tampering.

Feature: ai-application-integration
Property 24: Audit Log Immutability
**Validates: Requirements 8.3**
"""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.ai_integration.audit_service import AuditService
from src.models.ai_integration import AIAuditLog

# Import fixtures from conftest_audit
pytest_plugins = ["tests.conftest_audit"]


# Strategy for generating valid metadata
@st.composite
def metadata_strategy(draw):
    """Generate random metadata dictionaries."""
    keys = draw(st.lists(
        st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            min_codepoint=65, max_codepoint=122
        )),
        min_size=0,
        max_size=5,
        unique=True
    ))
    
    values = draw(st.lists(
        st.one_of(
            st.text(max_size=50),
            st.integers(min_value=0, max_value=10000),
            st.booleans()
        ),
        min_size=len(keys),
        max_size=len(keys)
    ))
    
    return dict(zip(keys, values))


# Strategy for generating audit log data
@st.composite
def audit_log_data_strategy(draw):
    """Generate random audit log data."""
    return {
        "gateway_id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "resource": draw(st.text(min_size=1, max_size=100)),
        "action": draw(st.sampled_from(["query", "create", "update", "delete", "export"])),
        "metadata": draw(metadata_strategy()),
        "user_identifier": draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        "channel": draw(st.one_of(st.none(), st.sampled_from(["whatsapp", "telegram", "slack", "discord"]))),
        "success": draw(st.booleans()),
        "error_message": draw(st.one_of(st.none(), st.text(max_size=200)))
    }


# Strategy for tampering with audit logs
@st.composite
def tamper_strategy(draw):
    """Generate tampering operations."""
    field = draw(st.sampled_from([
        "gateway_id",
        "tenant_id",
        "resource",
        "action",
        "event_metadata",
        "success"
    ]))
    
    if field == "gateway_id" or field == "tenant_id":
        new_value = str(uuid4())
    elif field == "resource":
        new_value = draw(st.text(min_size=1, max_size=100))
    elif field == "action":
        new_value = draw(st.sampled_from(["query", "create", "update", "delete", "export"]))
    elif field == "event_metadata":
        new_value = draw(metadata_strategy())
    elif field == "success":
        new_value = draw(st.booleans())
    else:
        new_value = None
    
    return field, new_value


class TestAuditLogImmutability:
    """Property 24: Audit Log Immutability - Validates: Requirements 8.3"""

    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(log_data=audit_log_data_strategy())
    def test_signature_verification_detects_gateway_id_tampering(
        self,
        db_session: Session,
        log_data: dict
    ):
        """
        Property 24: Audit Log Immutability
        **Validates: Requirements 8.3**
        
        Test that tampering with gateway_id is detected by signature verification.
        """
        # Create audit service
        audit_service = AuditService(secret_key="test_secret_key")
        
        # Create audit log
        log_entry = audit_service.log_data_access(
            gateway_id=log_data["gateway_id"],
            tenant_id=log_data["tenant_id"],
            resource=log_data["resource"],
            action=log_data["action"],
            metadata=log_data["metadata"],
            db=db_session,
            user_identifier=log_data["user_identifier"],
            channel=log_data["channel"],
            success=log_data["success"],
            error_message=log_data["error_message"]
        )
        
        # Verify original signature is valid
        assert audit_service.verify_signature(log_entry) is True
        
        # Tamper with gateway_id
        original_gateway_id = log_entry.gateway_id
        log_entry.gateway_id = str(uuid4())
        
        # Ensure we actually changed it
        assume(log_entry.gateway_id != original_gateway_id)
        
        # Signature verification should detect tampering
        assert audit_service.verify_signature(log_entry) is False

    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(log_data=audit_log_data_strategy())
    def test_signature_verification_detects_tenant_id_tampering(
        self,
        db_session: Session,
        log_data: dict
    ):
        """
        Property 24: Audit Log Immutability
        **Validates: Requirements 8.3**
        
        Test that tampering with tenant_id is detected by signature verification.
        """
        # Create audit service
        audit_service = AuditService(secret_key="test_secret_key")
        
        # Create audit log
        log_entry = audit_service.log_data_access(
            gateway_id=log_data["gateway_id"],
            tenant_id=log_data["tenant_id"],
            resource=log_data["resource"],
            action=log_data["action"],
            metadata=log_data["metadata"],
            db=db_session,
            user_identifier=log_data["user_identifier"],
            channel=log_data["channel"],
            success=log_data["success"],
            error_message=log_data["error_message"]
        )
        
        # Verify original signature is valid
        assert audit_service.verify_signature(log_entry) is True
        
        # Tamper with tenant_id
        original_tenant_id = log_entry.tenant_id
        log_entry.tenant_id = str(uuid4())
        
        # Ensure we actually changed it
        assume(log_entry.tenant_id != original_tenant_id)
        
        # Signature verification should detect tampering
        assert audit_service.verify_signature(log_entry) is False

    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(log_data=audit_log_data_strategy())
    def test_signature_verification_detects_resource_tampering(
        self,
        db_session: Session,
        log_data: dict
    ):
        """
        Property 24: Audit Log Immutability
        **Validates: Requirements 8.3**
        
        Test that tampering with resource is detected by signature verification.
        """
        # Create audit service
        audit_service = AuditService(secret_key="test_secret_key")
        
        # Create audit log
        log_entry = audit_service.log_data_access(
            gateway_id=log_data["gateway_id"],
            tenant_id=log_data["tenant_id"],
            resource=log_data["resource"],
            action=log_data["action"],
            metadata=log_data["metadata"],
            db=db_session,
            user_identifier=log_data["user_identifier"],
            channel=log_data["channel"],
            success=log_data["success"],
            error_message=log_data["error_message"]
        )
        
        # Verify original signature is valid
        assert audit_service.verify_signature(log_entry) is True
        
        # Tamper with resource
        original_resource = log_entry.resource
        log_entry.resource = "tampered_resource_" + str(uuid4())
        
        # Ensure we actually changed it
        assume(log_entry.resource != original_resource)
        
        # Signature verification should detect tampering
        assert audit_service.verify_signature(log_entry) is False

    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(log_data=audit_log_data_strategy())
    def test_signature_verification_detects_action_tampering(
        self,
        db_session: Session,
        log_data: dict
    ):
        """
        Property 24: Audit Log Immutability
        **Validates: Requirements 8.3**
        
        Test that tampering with action is detected by signature verification.
        """
        # Create audit service
        audit_service = AuditService(secret_key="test_secret_key")
        
        # Create audit log
        log_entry = audit_service.log_data_access(
            gateway_id=log_data["gateway_id"],
            tenant_id=log_data["tenant_id"],
            resource=log_data["resource"],
            action=log_data["action"],
            metadata=log_data["metadata"],
            db=db_session,
            user_identifier=log_data["user_identifier"],
            channel=log_data["channel"],
            success=log_data["success"],
            error_message=log_data["error_message"]
        )
        
        # Verify original signature is valid
        assert audit_service.verify_signature(log_entry) is True
        
        # Tamper with action
        original_action = log_entry.action
        actions = ["query", "create", "update", "delete", "export"]
        actions.remove(original_action)
        log_entry.action = actions[0]
        
        # Signature verification should detect tampering
        assert audit_service.verify_signature(log_entry) is False

    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(log_data=audit_log_data_strategy())
    def test_signature_verification_detects_metadata_tampering(
        self,
        db_session: Session,
        log_data: dict
    ):
        """
        Property 24: Audit Log Immutability
        **Validates: Requirements 8.3**
        
        Test that tampering with metadata is detected by signature verification.
        """
        # Create audit service
        audit_service = AuditService(secret_key="test_secret_key")
        
        # Create audit log
        log_entry = audit_service.log_data_access(
            gateway_id=log_data["gateway_id"],
            tenant_id=log_data["tenant_id"],
            resource=log_data["resource"],
            action=log_data["action"],
            metadata=log_data["metadata"],
            db=db_session,
            user_identifier=log_data["user_identifier"],
            channel=log_data["channel"],
            success=log_data["success"],
            error_message=log_data["error_message"]
        )
        
        # Verify original signature is valid
        assert audit_service.verify_signature(log_entry) is True
        
        # Tamper with metadata
        log_entry.event_metadata = {"tampered": "data", "modified": True}
        
        # Signature verification should detect tampering
        assert audit_service.verify_signature(log_entry) is False

    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(log_data=audit_log_data_strategy())
    def test_signature_verification_detects_success_flag_tampering(
        self,
        db_session: Session,
        log_data: dict
    ):
        """
        Property 24: Audit Log Immutability
        **Validates: Requirements 8.3**
        
        Test that tampering with success flag is detected by signature verification.
        """
        # Create audit service
        audit_service = AuditService(secret_key="test_secret_key")
        
        # Create audit log
        log_entry = audit_service.log_data_access(
            gateway_id=log_data["gateway_id"],
            tenant_id=log_data["tenant_id"],
            resource=log_data["resource"],
            action=log_data["action"],
            metadata=log_data["metadata"],
            db=db_session,
            user_identifier=log_data["user_identifier"],
            channel=log_data["channel"],
            success=log_data["success"],
            error_message=log_data["error_message"]
        )
        
        # Verify original signature is valid
        assert audit_service.verify_signature(log_entry) is True
        
        # Tamper with success flag
        log_entry.success = not log_entry.success
        
        # Signature verification should detect tampering
        assert audit_service.verify_signature(log_entry) is False

    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        log_data=audit_log_data_strategy(),
        tamper_op=tamper_strategy()
    )
    def test_any_field_tampering_detected(
        self,
        db_session: Session,
        log_data: dict,
        tamper_op: tuple
    ):
        """
        Property 24: Audit Log Immutability
        **Validates: Requirements 8.3**
        
        Test that tampering with any critical field is detected by signature verification.
        """
        # Create audit service
        audit_service = AuditService(secret_key="test_secret_key")
        
        # Create audit log
        log_entry = audit_service.log_data_access(
            gateway_id=log_data["gateway_id"],
            tenant_id=log_data["tenant_id"],
            resource=log_data["resource"],
            action=log_data["action"],
            metadata=log_data["metadata"],
            db=db_session,
            user_identifier=log_data["user_identifier"],
            channel=log_data["channel"],
            success=log_data["success"],
            error_message=log_data["error_message"]
        )
        
        # Verify original signature is valid
        assert audit_service.verify_signature(log_entry) is True
        
        # Apply tampering
        field, new_value = tamper_op
        original_value = getattr(log_entry, field)
        setattr(log_entry, field, new_value)
        
        # Ensure we actually changed it
        assume(getattr(log_entry, field) != original_value)
        
        # Signature verification should detect tampering
        assert audit_service.verify_signature(log_entry) is False

    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(log_data=audit_log_data_strategy())
    def test_unmodified_logs_always_verify(
        self,
        db_session: Session,
        log_data: dict
    ):
        """
        Property 24: Audit Log Immutability
        **Validates: Requirements 8.3**
        
        Test that unmodified audit logs always pass signature verification.
        """
        # Create audit service
        audit_service = AuditService(secret_key="test_secret_key")
        
        # Create audit log
        log_entry = audit_service.log_data_access(
            gateway_id=log_data["gateway_id"],
            tenant_id=log_data["tenant_id"],
            resource=log_data["resource"],
            action=log_data["action"],
            metadata=log_data["metadata"],
            db=db_session,
            user_identifier=log_data["user_identifier"],
            channel=log_data["channel"],
            success=log_data["success"],
            error_message=log_data["error_message"]
        )
        
        # Unmodified log should always verify
        assert audit_service.verify_signature(log_entry) is True
        
        # Verify multiple times - should be consistent
        assert audit_service.verify_signature(log_entry) is True
        assert audit_service.verify_signature(log_entry) is True
