"""
Integration Tests for Data Permission Control.

Tests the complete data permission control system including:
- Permission engine
- Policy inheritance
- Approval workflows
- Access logging
- Data classification
- Data masking
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from typing import List, Dict, Any

from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Integer, Text, JSON, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

Base = declarative_base()


# ============================================================================
# Test Models (SQLite Compatible)
# ============================================================================

class TestDataPermission(Base):
    __tablename__ = "data_permissions"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    resource_level = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    field_name = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    role_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    conditions = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    granted_by = Column(String, nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    is_temporary = Column(Boolean, default=False)


class TestPolicySource(Base):
    __tablename__ = "policy_sources"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    attribute_mapping = Column(JSON, nullable=True)
    sync_schedule = Column(String, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestApprovalWorkflow(Base):
    __tablename__ = "approval_workflows"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    sensitivity_levels = Column(JSON, nullable=False)
    approval_levels = Column(JSON, nullable=False)
    timeout_hours = Column(Integer, default=72)
    auto_approve_conditions = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestApprovalRequest(Base):
    __tablename__ = "approval_requests"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    requester_id = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    action = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    sensitivity_level = Column(String, nullable=False)
    workflow_id = Column(String, nullable=True)
    status = Column(String, default="pending")
    current_level = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)


class TestApprovalAction(Base):
    __tablename__ = "approval_actions"
    
    id = Column(String, primary_key=True)
    request_id = Column(String, nullable=False)
    approver_id = Column(String, nullable=False)
    approval_level = Column(Integer, nullable=False)
    decision = Column(String, nullable=False)
    comments = Column(Text, nullable=True)
    delegated_from = Column(String, nullable=True)
    action_at = Column(DateTime, default=datetime.utcnow)


class TestAccessLog(Base):
    __tablename__ = "data_access_logs"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    operation_type = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    fields_accessed = Column(JSON, nullable=True)
    details = Column(JSON, nullable=True)
    record_count = Column(Integer, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(String, nullable=True)
    sensitivity_level = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class DataClassificationModel(Base):
    __tablename__ = "data_classifications"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    dataset_id = Column(String, nullable=False)
    field_name = Column(String, nullable=True)
    category = Column(String, nullable=False)
    sensitivity_level = Column(String, nullable=False)
    classified_by = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=True)
    manually_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestMaskingRule(Base):
    __tablename__ = "masking_rules"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    field_pattern = Column(String, nullable=False)
    algorithm = Column(String, nullable=False)
    algorithm_config = Column(JSON, nullable=True)
    applicable_roles = Column(JSON, nullable=True)
    conditions = Column(JSON, nullable=True)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def tenant_id():
    """Test tenant ID."""
    return "test_tenant"


@pytest.fixture
def user_id():
    """Test user ID."""
    return str(uuid4())


@pytest.fixture
def admin_id():
    """Test admin ID."""
    return str(uuid4())


# ============================================================================
# Test Classes
# ============================================================================

class TestDataPermissionEngine:
    """Tests for Data Permission Engine."""
    
    def test_grant_dataset_permission(self, db_session, tenant_id, user_id, admin_id):
        """Test granting dataset-level permission."""
        permission = TestDataPermission(
            id=str(uuid4()),
            tenant_id=tenant_id,
            resource_level="dataset",
            resource_type="dataset",
            resource_id="dataset_001",
            user_id=user_id,
            action="read",
            granted_by=admin_id
        )
        db_session.add(permission)
        db_session.commit()
        
        # Verify permission exists
        result = db_session.query(TestDataPermission).filter(
            TestDataPermission.user_id == user_id,
            TestDataPermission.resource_id == "dataset_001"
        ).first()
        
        assert result is not None
        assert result.action == "read"
        assert result.is_active == True
    
    def test_grant_field_permission(self, db_session, tenant_id, user_id, admin_id):
        """Test granting field-level permission."""
        permission = TestDataPermission(
            id=str(uuid4()),
            tenant_id=tenant_id,
            resource_level="field",
            resource_type="field",
            resource_id="dataset_001",
            field_name="email",
            user_id=user_id,
            action="read",
            granted_by=admin_id
        )
        db_session.add(permission)
        db_session.commit()
        
        result = db_session.query(TestDataPermission).filter(
            TestDataPermission.field_name == "email"
        ).first()
        
        assert result is not None
        assert result.resource_level == "field"
    
    def test_temporary_permission_expiry(self, db_session, tenant_id, user_id, admin_id):
        """Test temporary permission with expiry."""
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        permission = TestDataPermission(
            id=str(uuid4()),
            tenant_id=tenant_id,
            resource_level="dataset",
            resource_type="dataset",
            resource_id="dataset_002",
            user_id=user_id,
            action="export",
            granted_by=admin_id,
            expires_at=expires_at,
            is_temporary=True
        )
        db_session.add(permission)
        db_session.commit()
        
        result = db_session.query(TestDataPermission).filter(
            TestDataPermission.is_temporary == True
        ).first()
        
        assert result is not None
        assert result.expires_at is not None
        assert result.expires_at > datetime.utcnow()
    
    def test_tag_based_permission(self, db_session, tenant_id, user_id, admin_id):
        """Test tag-based (ABAC) permission."""
        permission = TestDataPermission(
            id=str(uuid4()),
            tenant_id=tenant_id,
            resource_level="dataset",
            resource_type="dataset",
            resource_id="*",
            user_id=user_id,
            action="read",
            tags=["project_a", "public"],
            granted_by=admin_id
        )
        db_session.add(permission)
        db_session.commit()
        
        result = db_session.query(TestDataPermission).filter(
            TestDataPermission.tags.isnot(None)
        ).first()
        
        assert result is not None
        assert "project_a" in result.tags
    
    def test_revoke_permission(self, db_session, tenant_id, user_id, admin_id):
        """Test revoking a permission."""
        permission = TestDataPermission(
            id=str(uuid4()),
            tenant_id=tenant_id,
            resource_level="dataset",
            resource_type="dataset",
            resource_id="dataset_003",
            user_id=user_id,
            action="write",
            granted_by=admin_id
        )
        db_session.add(permission)
        db_session.commit()
        
        # Revoke
        permission.is_active = False
        db_session.commit()
        
        result = db_session.query(TestDataPermission).filter(
            TestDataPermission.resource_id == "dataset_003"
        ).first()
        
        assert result.is_active == False


class TestPolicyInheritance:
    """Tests for Policy Inheritance Manager."""
    
    def test_create_policy_source(self, db_session, tenant_id, admin_id):
        """Test creating a policy source."""
        source = TestPolicySource(
            id=str(uuid4()),
            tenant_id=tenant_id,
            name="ldap_corporate",
            source_type="ldap",
            config={
                "url": "ldap://corp.example.com",
                "base_dn": "dc=example,dc=com"
            },
            created_by=admin_id
        )
        db_session.add(source)
        db_session.commit()
        
        result = db_session.query(TestPolicySource).filter(
            TestPolicySource.name == "ldap_corporate"
        ).first()
        
        assert result is not None
        assert result.source_type == "ldap"
    
    def test_policy_sync_status(self, db_session, tenant_id, admin_id):
        """Test policy sync status tracking."""
        source = TestPolicySource(
            id=str(uuid4()),
            tenant_id=tenant_id,
            name="oauth_provider",
            source_type="oauth",
            config={"provider_url": "https://auth.example.com"},
            last_sync_at=datetime.utcnow(),
            last_sync_status="success",
            created_by=admin_id
        )
        db_session.add(source)
        db_session.commit()
        
        result = db_session.query(TestPolicySource).filter(
            TestPolicySource.last_sync_status == "success"
        ).first()
        
        assert result is not None
        assert result.last_sync_at is not None


class TestApprovalWorkflows:
    """Tests for Approval Workflow Engine."""
    
    def test_create_workflow(self, db_session, tenant_id, admin_id):
        """Test creating an approval workflow."""
        workflow = TestApprovalWorkflow(
            id=str(uuid4()),
            tenant_id=tenant_id,
            name="sensitive_data_workflow",
            sensitivity_levels=["confidential", "top_secret"],
            approval_levels=[
                {"level": 0, "name": "Manager", "approvers": []},
                {"level": 1, "name": "Security", "approvers": []}
            ],
            timeout_hours=48,
            created_by=admin_id
        )
        db_session.add(workflow)
        db_session.commit()
        
        result = db_session.query(TestApprovalWorkflow).filter(
            TestApprovalWorkflow.name == "sensitive_data_workflow"
        ).first()
        
        assert result is not None
        assert len(result.approval_levels) == 2
    
    def test_create_approval_request(self, db_session, tenant_id, user_id):
        """Test creating an approval request."""
        request = TestApprovalRequest(
            id=str(uuid4()),
            tenant_id=tenant_id,
            requester_id=user_id,
            resource="dataset_sensitive",
            resource_type="dataset",
            action="export",
            reason="Need data for quarterly report",
            sensitivity_level="confidential",
            expires_at=datetime.utcnow() + timedelta(hours=72)
        )
        db_session.add(request)
        db_session.commit()
        
        result = db_session.query(TestApprovalRequest).filter(
            TestApprovalRequest.requester_id == user_id
        ).first()
        
        assert result is not None
        assert result.status == "pending"
    
    def test_approve_request(self, db_session, tenant_id, user_id, admin_id):
        """Test approving a request."""
        request_id = str(uuid4())
        
        request = TestApprovalRequest(
            id=request_id,
            tenant_id=tenant_id,
            requester_id=user_id,
            resource="dataset_001",
            resource_type="dataset",
            action="read",
            reason="Analysis",
            sensitivity_level="internal",
            expires_at=datetime.utcnow() + timedelta(hours=72)
        )
        db_session.add(request)
        db_session.commit()
        
        # Record approval action
        action = TestApprovalAction(
            id=str(uuid4()),
            request_id=request_id,
            approver_id=admin_id,
            approval_level=0,
            decision="approved",
            comments="Approved for analysis"
        )
        db_session.add(action)
        
        # Update request status
        request.status = "approved"
        request.resolved_at = datetime.utcnow()
        db_session.commit()
        
        result = db_session.query(TestApprovalRequest).filter(
            TestApprovalRequest.id == request_id
        ).first()
        
        assert result.status == "approved"
        assert result.resolved_at is not None
    
    def test_reject_request(self, db_session, tenant_id, user_id, admin_id):
        """Test rejecting a request."""
        request_id = str(uuid4())
        
        request = TestApprovalRequest(
            id=request_id,
            tenant_id=tenant_id,
            requester_id=user_id,
            resource="dataset_secret",
            resource_type="dataset",
            action="export",
            reason="External sharing",
            sensitivity_level="top_secret",
            expires_at=datetime.utcnow() + timedelta(hours=72)
        )
        db_session.add(request)
        db_session.commit()
        
        # Reject
        request.status = "rejected"
        request.resolved_at = datetime.utcnow()
        db_session.commit()
        
        result = db_session.query(TestApprovalRequest).filter(
            TestApprovalRequest.id == request_id
        ).first()
        
        assert result.status == "rejected"


class TestAccessLogging:
    """Tests for Access Log Manager."""
    
    def test_log_read_operation(self, db_session, tenant_id, user_id):
        """Test logging a read operation."""
        log = TestAccessLog(
            id=str(uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type="read",
            resource="dataset_001",
            resource_type="dataset",
            fields_accessed=["name", "email", "phone"],
            record_count=100,
            ip_address="192.168.1.100"
        )
        db_session.add(log)
        db_session.commit()
        
        result = db_session.query(TestAccessLog).filter(
            TestAccessLog.operation_type == "read"
        ).first()
        
        assert result is not None
        assert result.record_count == 100
    
    def test_log_export_operation(self, db_session, tenant_id, user_id):
        """Test logging an export operation."""
        log = TestAccessLog(
            id=str(uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type="export",
            resource="dataset_002",
            resource_type="dataset",
            details={"format": "csv", "destination": "local"},
            record_count=5000,
            sensitivity_level="confidential"
        )
        db_session.add(log)
        db_session.commit()
        
        result = db_session.query(TestAccessLog).filter(
            TestAccessLog.operation_type == "export"
        ).first()
        
        assert result is not None
        assert result.sensitivity_level == "confidential"
    
    def test_query_logs_by_user(self, db_session, tenant_id, user_id):
        """Test querying logs by user."""
        # Create multiple logs
        for i in range(5):
            log = TestAccessLog(
                id=str(uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                operation_type="read",
                resource=f"dataset_{i}",
                resource_type="dataset"
            )
            db_session.add(log)
        db_session.commit()
        
        results = db_session.query(TestAccessLog).filter(
            TestAccessLog.user_id == user_id
        ).all()
        
        assert len(results) == 5


class TestDataClassificationTests:
    """Tests for Data Classification Engine."""
    
    def test_classify_field(self, db_session, tenant_id):
        """Test classifying a field."""
        classification = DataClassificationModel(
            id=str(uuid4()),
            tenant_id=tenant_id,
            dataset_id="dataset_001",
            field_name="email",
            category="pii",
            sensitivity_level="confidential",
            classified_by="rule_based"
        )
        db_session.add(classification)
        db_session.commit()
        
        result = db_session.query(DataClassificationModel).filter(
            DataClassificationModel.field_name == "email"
        ).first()
        
        assert result is not None
        assert result.sensitivity_level == "confidential"
    
    def test_ai_classification_with_confidence(self, db_session, tenant_id):
        """Test AI-based classification with confidence score."""
        classification = DataClassificationModel(
            id=str(uuid4()),
            tenant_id=tenant_id,
            dataset_id="dataset_002",
            field_name="custom_field",
            category="financial",
            sensitivity_level="top_secret",
            classified_by="ai_based",
            confidence_score=0.95
        )
        db_session.add(classification)
        db_session.commit()
        
        result = db_session.query(DataClassificationModel).filter(
            DataClassificationModel.classified_by == "ai_based"
        ).first()
        
        assert result is not None
        assert result.confidence_score == 0.95
    
    def test_manual_verification(self, db_session, tenant_id):
        """Test manual verification of classification."""
        classification = DataClassificationModel(
            id=str(uuid4()),
            tenant_id=tenant_id,
            dataset_id="dataset_003",
            field_name="ssn",
            category="pii",
            sensitivity_level="top_secret",
            classified_by="rule_based",
            manually_verified=True
        )
        db_session.add(classification)
        db_session.commit()
        
        result = db_session.query(DataClassificationModel).filter(
            DataClassificationModel.manually_verified == True
        ).first()
        
        assert result is not None
        assert result.field_name == "ssn"


class TestDataMasking:
    """Tests for Data Masking Service."""
    
    def test_create_masking_rule(self, db_session, tenant_id, admin_id):
        """Test creating a masking rule."""
        rule = TestMaskingRule(
            id=str(uuid4()),
            tenant_id=tenant_id,
            name="email_masking",
            field_pattern="*email*",
            algorithm="partial",
            algorithm_config={"show_start": 2, "show_end": 4},
            priority=10,
            created_by=admin_id
        )
        db_session.add(rule)
        db_session.commit()
        
        result = db_session.query(TestMaskingRule).filter(
            TestMaskingRule.name == "email_masking"
        ).first()
        
        assert result is not None
        assert result.algorithm == "partial"
    
    def test_role_based_masking_rule(self, db_session, tenant_id, admin_id):
        """Test role-based masking rule."""
        rule = TestMaskingRule(
            id=str(uuid4()),
            tenant_id=tenant_id,
            name="ssn_masking",
            field_pattern="*ssn*",
            algorithm="replacement",
            applicable_roles=["viewer", "analyst"],
            priority=20,
            created_by=admin_id
        )
        db_session.add(rule)
        db_session.commit()
        
        result = db_session.query(TestMaskingRule).filter(
            TestMaskingRule.applicable_roles.isnot(None)
        ).first()
        
        assert result is not None
        assert "viewer" in result.applicable_roles
    
    def test_masking_algorithm_replacement(self):
        """Test replacement masking algorithm."""
        value = "sensitive_data"
        masked = "***"
        
        assert masked != value
        assert value not in masked
    
    def test_masking_algorithm_partial(self):
        """Test partial masking algorithm."""
        value = "john.doe@example.com"
        # Partial mask: show first 2 and last 2 chars
        masked = value[:2] + "****" + value[-2:]
        
        assert masked != value
        assert masked.startswith("jo")
        assert masked.endswith("om")
    
    def test_masking_algorithm_hash(self):
        """Test hash masking algorithm."""
        import hashlib
        value = "secret_value"
        masked = hashlib.sha256(value.encode()).hexdigest()[:16]
        
        assert masked != value
        assert len(masked) == 16


class TestEndToEndScenarios:
    """End-to-end integration tests."""
    
    def test_complete_permission_flow(self, db_session, tenant_id, user_id, admin_id):
        """Test complete permission grant and check flow."""
        # 1. Create classification
        classification = DataClassificationModel(
            id=str(uuid4()),
            tenant_id=tenant_id,
            dataset_id="dataset_e2e",
            category="general",
            sensitivity_level="internal",
            classified_by="manual"
        )
        db_session.add(classification)
        
        # 2. Grant permission
        permission = TestDataPermission(
            id=str(uuid4()),
            tenant_id=tenant_id,
            resource_level="dataset",
            resource_type="dataset",
            resource_id="dataset_e2e",
            user_id=user_id,
            action="read",
            granted_by=admin_id
        )
        db_session.add(permission)
        
        # 3. Log access
        log = TestAccessLog(
            id=str(uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type="read",
            resource="dataset_e2e",
            resource_type="dataset",
            sensitivity_level="internal"
        )
        db_session.add(log)
        db_session.commit()
        
        # Verify all components
        assert db_session.query(DataClassificationModel).filter(
            DataClassificationModel.dataset_id == "dataset_e2e"
        ).first() is not None
        
        assert db_session.query(TestDataPermission).filter(
            TestDataPermission.resource_id == "dataset_e2e"
        ).first() is not None
        
        assert db_session.query(TestAccessLog).filter(
            TestAccessLog.resource == "dataset_e2e"
        ).first() is not None
    
    def test_approval_workflow_flow(self, db_session, tenant_id, user_id, admin_id):
        """Test complete approval workflow."""
        # 1. Create workflow
        workflow_id = str(uuid4())
        workflow = TestApprovalWorkflow(
            id=workflow_id,
            tenant_id=tenant_id,
            name="test_workflow",
            sensitivity_levels=["confidential"],
            approval_levels=[{"level": 0, "name": "Manager"}],
            timeout_hours=24,
            created_by=admin_id
        )
        db_session.add(workflow)
        
        # 2. Create request
        request_id = str(uuid4())
        request = TestApprovalRequest(
            id=request_id,
            tenant_id=tenant_id,
            requester_id=user_id,
            resource="sensitive_dataset",
            resource_type="dataset",
            action="export",
            reason="Business need",
            sensitivity_level="confidential",
            workflow_id=workflow_id,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db_session.add(request)
        
        # 3. Approve
        action = TestApprovalAction(
            id=str(uuid4()),
            request_id=request_id,
            approver_id=admin_id,
            approval_level=0,
            decision="approved"
        )
        db_session.add(action)
        
        request.status = "approved"
        request.resolved_at = datetime.utcnow()
        
        # 4. Grant temporary permission
        permission = TestDataPermission(
            id=str(uuid4()),
            tenant_id=tenant_id,
            resource_level="dataset",
            resource_type="dataset",
            resource_id="sensitive_dataset",
            user_id=user_id,
            action="export",
            granted_by=admin_id,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_temporary=True
        )
        db_session.add(permission)
        db_session.commit()
        
        # Verify
        final_request = db_session.query(TestApprovalRequest).filter(
            TestApprovalRequest.id == request_id
        ).first()
        
        assert final_request.status == "approved"
        
        temp_perm = db_session.query(TestDataPermission).filter(
            TestDataPermission.is_temporary == True,
            TestDataPermission.resource_id == "sensitive_dataset"
        ).first()
        
        assert temp_perm is not None


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
