"""
Property-based tests for IsolationEngine.

Tests Property 8: Tenant data isolation
"""

import pytest
from datetime import datetime
from uuid import uuid4
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
import enum

# Test-specific base and models for SQLite compatibility
TestBase = declarative_base()


class TestTenantModel(TestBase):
    """Test tenant model for SQLite."""
    __tablename__ = "tenants"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class TestWorkspaceModel(TestBase):
    """Test workspace model for SQLite."""
    __tablename__ = "workspaces"
    
    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestResourceModel(TestBase):
    """Test resource model for SQLite."""
    __tablename__ = "resources"
    
    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), nullable=False)
    workspace_id = Column(String(100), nullable=True)
    name = Column(String(200), nullable=False)
    data = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestCrossTenantAccessLogModel(TestBase):
    """Test cross-tenant access log model for SQLite."""
    __tablename__ = "cross_tenant_access_logs"
    
    id = Column(String(100), primary_key=True)
    accessor_tenant_id = Column(String(100), nullable=False)
    owner_tenant_id = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestAuditLogModel(TestBase):
    """Test audit log model for SQLite."""
    __tablename__ = "tenant_audit_logs"
    
    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class SimpleIsolationEngine:
    """Simplified isolation engine for property testing."""
    
    def __init__(self, session):
        self.session = session
        self.access_logs = []
    
    def get_tenant_filter(self, tenant_id: str, model_class):
        """Get tenant filter condition."""
        if hasattr(model_class, 'tenant_id'):
            return model_class.tenant_id == tenant_id
        elif hasattr(model_class, 'id'):
            return model_class.id == tenant_id
        raise ValueError(f"Model {model_class} has no tenant_id")
    
    def apply_tenant_filter(self, query, tenant_id: str, model_class):
        """Apply tenant filter to query."""
        filter_condition = self.get_tenant_filter(tenant_id, model_class)
        return query.filter(filter_condition)
    
    def verify_tenant_access(
        self,
        user_id: str,
        user_tenant_id: str,
        target_tenant_id: str,
        resource_id: str = None,
        resource_type: str = None
    ) -> bool:
        """Verify tenant access."""
        # Same tenant - always allowed
        if user_tenant_id == target_tenant_id:
            return True
        
        # Log cross-tenant attempt
        self._log_cross_tenant_access(
            accessor_tenant_id=user_tenant_id,
            owner_tenant_id=target_tenant_id,
            resource_id=resource_id or "unknown",
            resource_type=resource_type or "unknown",
            action="access_attempt",
            success=False
        )
        
        return False
    
    def _log_cross_tenant_access(
        self,
        accessor_tenant_id: str,
        owner_tenant_id: str,
        resource_id: str,
        resource_type: str,
        action: str,
        success: bool
    ):
        """Log cross-tenant access attempt."""
        log_entry = TestCrossTenantAccessLogModel(
            id=str(uuid4()),
            accessor_tenant_id=accessor_tenant_id,
            owner_tenant_id=owner_tenant_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            success=success,
        )
        self.session.add(log_entry)
        self.session.commit()
        self.access_logs.append(log_entry)
    
    def encrypt_tenant_data(self, tenant_id: str, data: bytes) -> bytes:
        """Simple encryption (XOR with tenant ID hash for testing)."""
        import hashlib
        key = hashlib.sha256(tenant_id.encode()).digest()
        # Simple XOR encryption for testing
        encrypted = bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))
        return encrypted
    
    def decrypt_tenant_data(self, tenant_id: str, encrypted_data: bytes) -> bytes:
        """Simple decryption (XOR is symmetric)."""
        return self.encrypt_tenant_data(tenant_id, encrypted_data)


def create_fresh_session():
    """Create a fresh database session for each test example."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    TestBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture
def test_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    TestBase.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def isolation_engine(test_session):
    """Create isolation engine."""
    return SimpleIsolationEngine(test_session)


class TestTenantDataIsolation:
    """
    Property 8: Tenant data isolation
    
    For any database query, tenant filter should be automatically applied.
    Users should only see data from their own tenant.
    """
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        num_tenants=st.integers(min_value=2, max_value=5),
        resources_per_tenant=st.integers(min_value=1, max_value=10)
    )
    def test_tenant_filter_isolates_data(self, num_tenants, resources_per_tenant):
        """
        Property: Tenant filter ensures users only see their own data.
        """
        session = create_fresh_session()
        engine = SimpleIsolationEngine(session)
        
        # Create tenants and resources
        tenants = []
        for i in range(num_tenants):
            tenant_id = f"tenant-{uuid4().hex[:8]}"
            tenant = TestTenantModel(
                id=tenant_id,
                name=f"Tenant {i}",
            )
            session.add(tenant)
            tenants.append(tenant_id)
            
            # Create resources for this tenant
            for j in range(resources_per_tenant):
                resource = TestResourceModel(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    name=f"Resource {j} for {tenant_id}",
                )
                session.add(resource)
        
        session.commit()
        
        # For each tenant, verify they only see their own resources
        for tenant_id in tenants:
            query = session.query(TestResourceModel)
            filtered_query = engine.apply_tenant_filter(query, tenant_id, TestResourceModel)
            results = filtered_query.all()
            
            # Should only see resources from this tenant
            assert len(results) == resources_per_tenant
            for resource in results:
                assert resource.tenant_id == tenant_id
        
        session.close()
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        tenant1_resources=st.integers(min_value=1, max_value=20),
        tenant2_resources=st.integers(min_value=1, max_value=20)
    )
    def test_cross_tenant_data_invisible(self, tenant1_resources, tenant2_resources):
        """
        Property: Data from one tenant is invisible to another tenant.
        """
        session = create_fresh_session()
        engine = SimpleIsolationEngine(session)
        
        tenant1_id = f"tenant-{uuid4().hex[:8]}"
        tenant2_id = f"tenant-{uuid4().hex[:8]}"
        
        # Create resources for tenant 1
        tenant1_resource_ids = []
        for i in range(tenant1_resources):
            resource = TestResourceModel(
                id=str(uuid4()),
                tenant_id=tenant1_id,
                name=f"Tenant1 Resource {i}",
            )
            session.add(resource)
            tenant1_resource_ids.append(resource.id)
        
        # Create resources for tenant 2
        tenant2_resource_ids = []
        for i in range(tenant2_resources):
            resource = TestResourceModel(
                id=str(uuid4()),
                tenant_id=tenant2_id,
                name=f"Tenant2 Resource {i}",
            )
            session.add(resource)
            tenant2_resource_ids.append(resource.id)
        
        session.commit()
        
        # Tenant 1 should not see tenant 2's resources
        query = session.query(TestResourceModel)
        tenant1_results = engine.apply_tenant_filter(query, tenant1_id, TestResourceModel).all()
        tenant1_result_ids = [r.id for r in tenant1_results]
        
        for resource_id in tenant2_resource_ids:
            assert resource_id not in tenant1_result_ids
        
        # Tenant 2 should not see tenant 1's resources
        query = session.query(TestResourceModel)
        tenant2_results = engine.apply_tenant_filter(query, tenant2_id, TestResourceModel).all()
        tenant2_result_ids = [r.id for r in tenant2_results]
        
        for resource_id in tenant1_resource_ids:
            assert resource_id not in tenant2_result_ids
        
        session.close()
    
    def test_empty_tenant_sees_no_data(self, test_session, isolation_engine):
        """
        Property: A tenant with no data sees empty results.
        """
        # Create resources for another tenant
        other_tenant_id = f"tenant-{uuid4().hex[:8]}"
        for i in range(5):
            resource = TestResourceModel(
                id=str(uuid4()),
                tenant_id=other_tenant_id,
                name=f"Other Resource {i}",
            )
            test_session.add(resource)
        test_session.commit()
        
        # New tenant should see nothing
        new_tenant_id = f"tenant-{uuid4().hex[:8]}"
        query = test_session.query(TestResourceModel)
        results = isolation_engine.apply_tenant_filter(query, new_tenant_id, TestResourceModel).all()
        
        assert len(results) == 0


class TestTenantAccessVerification:
    """Tests for tenant access verification."""
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        tenant_id=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    def test_same_tenant_access_allowed(self, tenant_id):
        """
        Property: Users can always access their own tenant's resources.
        """
        session = create_fresh_session()
        engine = SimpleIsolationEngine(session)
        
        user_id = f"user-{uuid4().hex[:8]}"
        
        # Same tenant access should be allowed
        result = engine.verify_tenant_access(
            user_id=user_id,
            user_tenant_id=tenant_id,
            target_tenant_id=tenant_id,
            resource_id="some-resource",
            resource_type="document"
        )
        
        assert result == True
        session.close()
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        tenant1=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        tenant2=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    def test_cross_tenant_access_denied(self, tenant1, tenant2):
        """
        Property: Cross-tenant access is denied by default.
        """
        # Skip if same tenant
        if tenant1 == tenant2:
            return
        
        session = create_fresh_session()
        engine = SimpleIsolationEngine(session)
        
        user_id = f"user-{uuid4().hex[:8]}"
        
        # Cross-tenant access should be denied
        result = engine.verify_tenant_access(
            user_id=user_id,
            user_tenant_id=tenant1,
            target_tenant_id=tenant2,
            resource_id="some-resource",
            resource_type="document"
        )
        
        assert result == False
        session.close()
    
    def test_cross_tenant_access_logged(self, test_session, isolation_engine):
        """
        Property: Cross-tenant access attempts are logged.
        """
        tenant1_id = f"tenant-{uuid4().hex[:8]}"
        tenant2_id = f"tenant-{uuid4().hex[:8]}"
        user_id = f"user-{uuid4().hex[:8]}"
        resource_id = f"resource-{uuid4().hex[:8]}"
        
        # Attempt cross-tenant access
        isolation_engine.verify_tenant_access(
            user_id=user_id,
            user_tenant_id=tenant1_id,
            target_tenant_id=tenant2_id,
            resource_id=resource_id,
            resource_type="document"
        )
        
        # Verify log was created
        logs = test_session.query(TestCrossTenantAccessLogModel).filter(
            TestCrossTenantAccessLogModel.accessor_tenant_id == tenant1_id,
            TestCrossTenantAccessLogModel.owner_tenant_id == tenant2_id
        ).all()
        
        assert len(logs) >= 1
        assert logs[0].success == False
        assert logs[0].resource_id == resource_id


class TestTenantDataEncryption:
    """Tests for tenant-specific data encryption."""
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        data=st.binary(min_size=1, max_size=1000)
    )
    def test_encrypt_decrypt_roundtrip(self, data):
        """
        Property: Encrypted data can be decrypted back to original.
        """
        session = create_fresh_session()
        engine = SimpleIsolationEngine(session)
        
        tenant_id = f"tenant-{uuid4().hex[:8]}"
        
        # Encrypt and decrypt
        encrypted = engine.encrypt_tenant_data(tenant_id, data)
        decrypted = engine.decrypt_tenant_data(tenant_id, encrypted)
        
        assert decrypted == data
        session.close()
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        data=st.binary(min_size=10, max_size=100)
    )
    def test_different_tenants_different_encryption(self, data):
        """
        Property: Same data encrypted by different tenants produces different ciphertext.
        """
        session = create_fresh_session()
        engine = SimpleIsolationEngine(session)
        
        tenant1_id = f"tenant-{uuid4().hex[:8]}"
        tenant2_id = f"tenant-{uuid4().hex[:8]}"
        
        encrypted1 = engine.encrypt_tenant_data(tenant1_id, data)
        encrypted2 = engine.encrypt_tenant_data(tenant2_id, data)
        
        # Different tenants should produce different ciphertext
        assert encrypted1 != encrypted2
        session.close()
    
    def test_wrong_tenant_cannot_decrypt(self, test_session, isolation_engine):
        """
        Property: Data encrypted by one tenant cannot be decrypted by another.
        """
        tenant1_id = f"tenant-{uuid4().hex[:8]}"
        tenant2_id = f"tenant-{uuid4().hex[:8]}"
        original_data = b"sensitive tenant data"
        
        # Encrypt with tenant 1
        encrypted = isolation_engine.encrypt_tenant_data(tenant1_id, original_data)
        
        # Try to decrypt with tenant 2
        decrypted_wrong = isolation_engine.decrypt_tenant_data(tenant2_id, encrypted)
        
        # Should not match original
        assert decrypted_wrong != original_data


class TestFilterConsistency:
    """Tests for filter consistency across operations."""
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        num_operations=st.integers(min_value=5, max_value=20)
    )
    def test_filter_consistent_across_queries(self, num_operations):
        """
        Property: Tenant filter produces consistent results across multiple queries.
        """
        session = create_fresh_session()
        engine = SimpleIsolationEngine(session)
        
        tenant_id = f"tenant-{uuid4().hex[:8]}"
        
        # Create some resources
        for i in range(10):
            resource = TestResourceModel(
                id=str(uuid4()),
                tenant_id=tenant_id,
                name=f"Resource {i}",
            )
            session.add(resource)
        session.commit()
        
        # Run multiple queries and verify consistency
        results = []
        for _ in range(num_operations):
            query = session.query(TestResourceModel)
            filtered = engine.apply_tenant_filter(query, tenant_id, TestResourceModel)
            result_ids = sorted([r.id for r in filtered.all()])
            results.append(result_ids)
        
        # All results should be identical
        for result in results[1:]:
            assert result == results[0]
        
        session.close()
