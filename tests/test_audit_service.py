"""
Unit tests for AI Integration Audit Service.

Tests audit logging, signature generation, and query filtering.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session

from src.ai_integration.audit_service import AuditService
from src.models.ai_integration import AIAuditLog

# Import fixtures from conftest_audit
pytest_plugins = ["tests.conftest_audit"]


@pytest.fixture
def audit_service():
    """Create audit service instance."""
    return AuditService(secret_key="test_secret_key")


@pytest.fixture
def sample_gateway_id():
    """Sample gateway ID."""
    return str(uuid4())


@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID."""
    return str(uuid4())


class TestLogDataAccess:
    """Test log_data_access method."""

    def test_log_successful_data_access(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test logging successful data access."""
        metadata = {
            "dataset": "customers",
            "records_accessed": 100,
            "filters": {"status": "active"}
        }

        log_entry = audit_service.log_data_access(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            resource="dataset/customers",
            action="query",
            metadata=metadata,
            db=db_session,
            user_identifier="user@example.com",
            channel="whatsapp",
            success=True
        )

        assert log_entry.id is not None
        assert log_entry.gateway_id == sample_gateway_id
        assert log_entry.tenant_id == sample_tenant_id
        assert log_entry.event_type == "data_access"
        assert log_entry.resource == "dataset/customers"
        assert log_entry.action == "query"
        assert log_entry.event_metadata == metadata
        assert log_entry.user_identifier == "user@example.com"
        assert log_entry.channel == "whatsapp"
        assert log_entry.success is True
        assert log_entry.signature is not None
        assert len(log_entry.signature) == 64  # SHA256 hex

    def test_log_failed_data_access(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test logging failed data access."""
        log_entry = audit_service.log_data_access(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            resource="dataset/restricted",
            action="query",
            metadata={"attempted_access": "restricted_data"},
            db=db_session,
            success=False,
            error_message="Permission denied"
        )

        assert log_entry.success is False
        assert log_entry.error_message == "Permission denied"
        assert log_entry.signature is not None


class TestLogSecurityEvent:
    """Test log_security_event method."""

    def test_log_cross_tenant_access_attempt(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test logging cross-tenant access attempt."""
        details = {
            "attempted_tenant": str(uuid4()),
            "gateway_tenant": sample_tenant_id,
            "resource": "dataset/customers"
        }

        log_entry = audit_service.log_security_event(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            event_type="cross_tenant_access_attempt",
            details=details,
            db=db_session,
            user_identifier="suspicious_user"
        )

        assert log_entry.event_type == "cross_tenant_access_attempt"
        assert log_entry.resource == "security"
        assert log_entry.action == "monitor"
        assert log_entry.event_metadata == details
        assert log_entry.user_identifier == "suspicious_user"
        assert log_entry.signature is not None

    def test_log_authentication_failure(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test logging authentication failure."""
        details = {
            "reason": "invalid_credentials",
            "ip_address": "192.168.1.100"
        }

        log_entry = audit_service.log_security_event(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            event_type="authentication_failure",
            details=details,
            db=db_session
        )

        assert log_entry.event_type == "authentication_failure"
        assert log_entry.signature is not None


class TestQueryAuditLogs:
    """Test query_audit_logs method."""

    def test_query_by_gateway_id(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test querying logs by gateway ID."""
        # Create multiple log entries
        for i in range(3):
            audit_service.log_data_access(
                gateway_id=sample_gateway_id,
                tenant_id=sample_tenant_id,
                resource=f"dataset_{i}",
                action="query",
                metadata={"index": i},
                db=db_session
            )

        # Create log for different gateway
        other_gateway = str(uuid4())
        audit_service.log_data_access(
            gateway_id=other_gateway,
            tenant_id=sample_tenant_id,
            resource="dataset_other",
            action="query",
            metadata={},
            db=db_session
        )

        # Query by gateway ID
        logs = audit_service.query_audit_logs(
            db=db_session,
            gateway_id=sample_gateway_id
        )

        assert len(logs) == 3
        assert all(log.gateway_id == sample_gateway_id for log in logs)

    def test_query_by_tenant_id(
        self,
        audit_service,
        sample_gateway_id,
        db_session: Session
    ):
        """Test querying logs by tenant ID."""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())

        # Create logs for tenant1
        for i in range(2):
            audit_service.log_data_access(
                gateway_id=sample_gateway_id,
                tenant_id=tenant1,
                resource=f"dataset_{i}",
                action="query",
                metadata={},
                db=db_session
            )

        # Create log for tenant2
        audit_service.log_data_access(
            gateway_id=sample_gateway_id,
            tenant_id=tenant2,
            resource="dataset_other",
            action="query",
            metadata={},
            db=db_session
        )

        # Query by tenant ID
        logs = audit_service.query_audit_logs(
            db=db_session,
            tenant_id=tenant1
        )

        assert len(logs) == 2
        assert all(log.tenant_id == tenant1 for log in logs)

    def test_query_by_time_range(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test querying logs by time range."""
        now = datetime.utcnow()

        # Create log entry
        log_entry = audit_service.log_data_access(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            resource="dataset",
            action="query",
            metadata={},
            db=db_session
        )

        # Query with time range
        start_time = now - timedelta(minutes=5)
        end_time = now + timedelta(minutes=5)

        logs = audit_service.query_audit_logs(
            db=db_session,
            gateway_id=sample_gateway_id,
            start_time=start_time,
            end_time=end_time
        )

        assert len(logs) == 1
        assert logs[0].id == log_entry.id

    def test_query_by_operation_type(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test querying logs by operation type."""
        # Create data access log
        audit_service.log_data_access(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            resource="dataset",
            action="query",
            metadata={},
            db=db_session
        )

        # Create security event log
        audit_service.log_security_event(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            event_type="authentication_failure",
            details={},
            db=db_session
        )

        # Query by operation type
        logs = audit_service.query_audit_logs(
            db=db_session,
            gateway_id=sample_gateway_id,
            operation_type="data_access"
        )

        assert len(logs) == 1
        assert logs[0].event_type == "data_access"

    def test_query_with_pagination(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test querying logs with pagination."""
        # Create 5 log entries
        for i in range(5):
            audit_service.log_data_access(
                gateway_id=sample_gateway_id,
                tenant_id=sample_tenant_id,
                resource=f"dataset_{i}",
                action="query",
                metadata={"index": i},
                db=db_session
            )

        # Query first page
        page1 = audit_service.query_audit_logs(
            db=db_session,
            gateway_id=sample_gateway_id,
            limit=2,
            offset=0
        )

        # Query second page
        page2 = audit_service.query_audit_logs(
            db=db_session,
            gateway_id=sample_gateway_id,
            limit=2,
            offset=2
        )

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id


class TestSignatureGeneration:
    """Test signature generation and verification."""

    def test_signature_is_deterministic(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test that signature is deterministic."""
        log_entry = audit_service.log_data_access(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            resource="dataset",
            action="query",
            metadata={"test": "data"},
            db=db_session
        )

        # Generate signature again
        signature1 = log_entry.signature
        signature2 = audit_service._generate_signature(log_entry)

        assert signature1 == signature2

    def test_verify_valid_signature(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test verifying valid signature."""
        log_entry = audit_service.log_data_access(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            resource="dataset",
            action="query",
            metadata={},
            db=db_session
        )

        assert audit_service.verify_signature(log_entry) is True

    def test_detect_tampered_signature(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test detecting tampered signature."""
        log_entry = audit_service.log_data_access(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            resource="dataset",
            action="query",
            metadata={},
            db=db_session
        )

        # Tamper with the log entry
        log_entry.event_metadata = {"tampered": "data"}

        # Signature should no longer be valid
        assert audit_service.verify_signature(log_entry) is False

    def test_signature_changes_with_data(
        self,
        audit_service,
        sample_gateway_id,
        sample_tenant_id,
        db_session: Session
    ):
        """Test that signature changes with data."""
        log1 = audit_service.log_data_access(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            resource="dataset1",
            action="query",
            metadata={},
            db=db_session
        )

        log2 = audit_service.log_data_access(
            gateway_id=sample_gateway_id,
            tenant_id=sample_tenant_id,
            resource="dataset2",
            action="query",
            metadata={},
            db=db_session
        )

        assert log1.signature != log2.signature
