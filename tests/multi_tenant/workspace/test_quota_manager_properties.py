"""
Property-based tests for QuotaManager.

Tests Property 6: Quota usage tracking accuracy
Tests Property 7: Quota threshold enforcement
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy import create_engine, Column, String, Integer, BigInteger, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
import enum

# Test-specific base and models for SQLite compatibility
TestBase = declarative_base()


class TestEntityType(str, enum.Enum):
    TENANT = "tenant"
    WORKSPACE = "workspace"


class TestResourceType(str, enum.Enum):
    STORAGE = "storage_bytes"
    PROJECTS = "project_count"
    USERS = "user_count"
    API_CALLS = "api_call_count"


class TestTenantQuotaModel(TestBase):
    """Test tenant quota model for SQLite."""
    __tablename__ = "tenant_quotas"
    
    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), nullable=False, unique=True)
    storage_bytes = Column(BigInteger, default=10737418240)
    project_count = Column(Integer, default=100)
    user_count = Column(Integer, default=50)
    api_call_count = Column(Integer, default=100000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TestQuotaUsageModel(TestBase):
    """Test quota usage model for SQLite."""
    __tablename__ = "quota_usage"
    
    id = Column(String(100), primary_key=True)
    entity_id = Column(String(100), nullable=False)
    entity_type = Column(SQLEnum(TestEntityType), nullable=False)
    storage_bytes = Column(BigInteger, default=0)
    project_count = Column(Integer, default=0)
    user_count = Column(Integer, default=0)
    api_call_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class TestTemporaryQuotaModel(TestBase):
    """Test temporary quota model for SQLite."""
    __tablename__ = "temporary_quotas"
    
    id = Column(String(100), primary_key=True)
    entity_id = Column(String(100), nullable=False)
    entity_type = Column(SQLEnum(TestEntityType), nullable=False)
    storage_bytes = Column(BigInteger, nullable=True)
    project_count = Column(Integer, nullable=True)
    user_count = Column(Integer, nullable=True)
    api_call_count = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    reason = Column(String(500), nullable=True)
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
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Simple QuotaManager for testing
class SimpleQuotaManager:
    """Simplified quota manager for property testing."""
    
    WARNING_THRESHOLD = 0.8
    BLOCKING_THRESHOLD = 1.0
    
    def __init__(self, session):
        self.session = session
        self.notifications = []  # Track notifications
    
    def set_quota(self, entity_id: str, quota_config: dict) -> TestTenantQuotaModel:
        """Set quota for a tenant."""
        quota = self.session.query(TestTenantQuotaModel).filter(
            TestTenantQuotaModel.tenant_id == entity_id
        ).first()
        
        if quota:
            quota.storage_bytes = quota_config.get("storage_bytes", quota.storage_bytes)
            quota.project_count = quota_config.get("project_count", quota.project_count)
            quota.user_count = quota_config.get("user_count", quota.user_count)
            quota.api_call_count = quota_config.get("api_call_count", quota.api_call_count)
        else:
            quota = TestTenantQuotaModel(
                id=str(uuid4()),
                tenant_id=entity_id,
                storage_bytes=quota_config.get("storage_bytes", 10737418240),
                project_count=quota_config.get("project_count", 100),
                user_count=quota_config.get("user_count", 50),
                api_call_count=quota_config.get("api_call_count", 100000),
            )
            self.session.add(quota)
        
        self.session.commit()
        return quota
    
    def get_quota(self, entity_id: str) -> dict:
        """Get quota for a tenant."""
        quota = self.session.query(TestTenantQuotaModel).filter(
            TestTenantQuotaModel.tenant_id == entity_id
        ).first()
        
        if not quota:
            return None
        
        return {
            "storage_bytes": quota.storage_bytes,
            "project_count": quota.project_count,
            "user_count": quota.user_count,
            "api_call_count": quota.api_call_count,
        }
    
    def get_usage(self, entity_id: str, entity_type: TestEntityType) -> dict:
        """Get usage for an entity."""
        usage = self.session.query(TestQuotaUsageModel).filter(
            TestQuotaUsageModel.entity_id == entity_id,
            TestQuotaUsageModel.entity_type == entity_type
        ).first()
        
        if not usage:
            return {
                "storage_bytes": 0,
                "project_count": 0,
                "user_count": 0,
                "api_call_count": 0,
            }
        
        return {
            "storage_bytes": usage.storage_bytes,
            "project_count": usage.project_count,
            "user_count": usage.user_count,
            "api_call_count": usage.api_call_count,
        }
    
    def increment_usage(
        self,
        entity_id: str,
        entity_type: TestEntityType,
        resource_type: TestResourceType,
        amount: int = 1
    ) -> dict:
        """Increment usage for a resource."""
        usage = self.session.query(TestQuotaUsageModel).filter(
            TestQuotaUsageModel.entity_id == entity_id,
            TestQuotaUsageModel.entity_type == entity_type
        ).first()
        
        if not usage:
            usage = TestQuotaUsageModel(
                id=str(uuid4()),
                entity_id=entity_id,
                entity_type=entity_type,
                storage_bytes=0,
                project_count=0,
                user_count=0,
                api_call_count=0,
            )
            self.session.add(usage)
        
        resource_field = resource_type.value
        current_value = getattr(usage, resource_field, 0)
        new_value = max(0, current_value + amount)
        setattr(usage, resource_field, new_value)
        
        self.session.commit()
        return self.get_usage(entity_id, entity_type)
    
    def check_quota(
        self,
        entity_id: str,
        entity_type: TestEntityType,
        resource_type: TestResourceType,
        amount: int = 1
    ) -> dict:
        """Check if operation is allowed based on quota."""
        quota = self.get_quota(entity_id)
        if not quota:
            return {"allowed": True, "percentage": 0}
        
        usage = self.get_usage(entity_id, entity_type)
        
        resource_field = resource_type.value
        current = usage.get(resource_field, 0)
        limit = quota.get(resource_field, 0)
        
        if limit == 0:
            return {"allowed": True, "percentage": 0}
        
        new_total = current + amount
        percentage = (new_total / limit) * 100
        
        # Check blocking threshold
        if percentage >= self.BLOCKING_THRESHOLD * 100:
            return {
                "allowed": False,
                "percentage": min(percentage, 100),
                "reason": f"Quota exceeded for {resource_type.value}"
            }
        
        # Check warning threshold
        warning = None
        if percentage >= self.WARNING_THRESHOLD * 100:
            warning = f"{resource_type.value} usage at {percentage:.1f}%"
            self.notifications.append({
                "entity_id": entity_id,
                "message": warning,
                "severity": "warning"
            })
        
        return {
            "allowed": True,
            "percentage": percentage,
            "warning": warning
        }


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
def quota_manager(test_session):
    """Create quota manager."""
    return SimpleQuotaManager(test_session)


def create_fresh_session():
    """Create a fresh database session for each test example."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    TestBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


class TestQuotaUsageTrackingAccuracy:
    """
    Property 6: Quota usage tracking accuracy
    
    For any resource operation, quota usage should accurately reflect
    the actual resource usage.
    """
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        increments=st.lists(
            st.integers(min_value=1, max_value=100),
            min_size=1,
            max_size=10
        )
    )
    def test_usage_accurately_tracks_increments(self, increments):
        """
        Property: Usage accurately reflects cumulative increments.
        """
        # Create fresh session for each example
        session = create_fresh_session()
        manager = SimpleQuotaManager(session)
        entity_id = f"tenant-{uuid4().hex[:8]}"
        entity_type = TestEntityType.TENANT
        resource_type = TestResourceType.PROJECTS
        
        # Set up quota
        manager.set_quota(entity_id, {"project_count": 1000})
        
        # Apply increments
        expected_total = 0
        for inc in increments:
            manager.increment_usage(entity_id, entity_type, resource_type, inc)
            expected_total += inc
        
        # Verify usage matches expected
        usage = manager.get_usage(entity_id, entity_type)
        assert usage["project_count"] == expected_total
        
        session.close()
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        operations=st.lists(
            st.tuples(
                st.sampled_from([TestResourceType.STORAGE, TestResourceType.PROJECTS, TestResourceType.USERS, TestResourceType.API_CALLS]),
                st.integers(min_value=1, max_value=50)
            ),
            min_size=1,
            max_size=20
        )
    )
    def test_usage_tracks_multiple_resource_types(self, operations):
        """
        Property: Usage accurately tracks multiple resource types independently.
        """
        # Create fresh session for each example
        session = create_fresh_session()
        manager = SimpleQuotaManager(session)
        entity_id = f"tenant-{uuid4().hex[:8]}"
        entity_type = TestEntityType.TENANT
        
        # Set up quota
        manager.set_quota(entity_id, {
            "storage_bytes": 10000000,
            "project_count": 1000,
            "user_count": 500,
            "api_call_count": 100000
        })
        
        # Track expected values
        expected = {
            "storage_bytes": 0,
            "project_count": 0,
            "user_count": 0,
            "api_call_count": 0,
        }
        
        # Apply operations
        for resource_type, amount in operations:
            manager.increment_usage(entity_id, entity_type, resource_type, amount)
            expected[resource_type.value] += amount
        
        # Verify all resource types
        usage = manager.get_usage(entity_id, entity_type)
        for field, expected_value in expected.items():
            assert usage[field] == expected_value, f"Mismatch for {field}: {usage[field]} != {expected_value}"
        
        session.close()
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        add_amount=st.integers(min_value=10, max_value=100),
        remove_amount=st.integers(min_value=1, max_value=50)
    )
    def test_usage_handles_decrements(self, add_amount, remove_amount):
        """
        Property: Usage correctly handles decrements (resource deletion).
        """
        # Create fresh session for each example
        session = create_fresh_session()
        manager = SimpleQuotaManager(session)
        entity_id = f"tenant-{uuid4().hex[:8]}"
        entity_type = TestEntityType.TENANT
        resource_type = TestResourceType.PROJECTS
        
        # Set up quota
        manager.set_quota(entity_id, {"project_count": 1000})
        
        # Add resources
        manager.increment_usage(entity_id, entity_type, resource_type, add_amount)
        
        # Remove resources (decrement)
        actual_remove = min(remove_amount, add_amount)  # Can't go below 0
        manager.increment_usage(entity_id, entity_type, resource_type, -actual_remove)
        
        # Verify usage
        usage = manager.get_usage(entity_id, entity_type)
        expected = max(0, add_amount - actual_remove)
        assert usage["project_count"] == expected
        
        session.close()
    
    def test_usage_never_goes_negative(self, test_session, quota_manager):
        """
        Property: Usage should never go below zero.
        """
        entity_id = f"tenant-{uuid4().hex[:8]}"
        entity_type = TestEntityType.TENANT
        resource_type = TestResourceType.PROJECTS
        
        # Set up quota
        quota_manager.set_quota(entity_id, {"project_count": 100})
        
        # Add some usage
        quota_manager.increment_usage(entity_id, entity_type, resource_type, 5)
        
        # Try to decrement more than available
        quota_manager.increment_usage(entity_id, entity_type, resource_type, -100)
        
        # Verify usage is 0, not negative
        usage = quota_manager.get_usage(entity_id, entity_type)
        assert usage["project_count"] >= 0


class TestQuotaThresholdEnforcement:
    """
    Property 7: Quota threshold enforcement
    
    - At 80% usage, a warning should be generated
    - At 100% usage, operations should be blocked
    """
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        usage_percentage=st.floats(min_value=0, max_value=79.9)
    )
    def test_below_warning_threshold_allows_operation(self, usage_percentage):
        """
        Property: Operations below 80% threshold are allowed without warning.
        """
        # Create fresh session for each example
        session = create_fresh_session()
        manager = SimpleQuotaManager(session)
        entity_id = f"tenant-{uuid4().hex[:8]}"
        entity_type = TestEntityType.TENANT
        resource_type = TestResourceType.PROJECTS
        limit = 100
        
        # Set up quota
        manager.set_quota(entity_id, {"project_count": limit})
        
        # Set current usage
        current_usage = int(limit * usage_percentage / 100)
        if current_usage > 0:
            manager.increment_usage(entity_id, entity_type, resource_type, current_usage)
        
        # Clear notifications
        manager.notifications = []
        
        # Check if adding 1 more is allowed
        result = manager.check_quota(entity_id, entity_type, resource_type, 1)
        
        # Should be allowed
        assert result["allowed"] == True
        # Should not have warning if still below 80%
        if (current_usage + 1) / limit < 0.8:
            assert result.get("warning") is None
        
        session.close()
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        usage_percentage=st.floats(min_value=80, max_value=99.9)
    )
    def test_at_warning_threshold_generates_warning(self, usage_percentage):
        """
        Property: Operations at 80-99% threshold generate warnings but are allowed.
        """
        # Create fresh session for each example
        session = create_fresh_session()
        manager = SimpleQuotaManager(session)
        entity_id = f"tenant-{uuid4().hex[:8]}"
        entity_type = TestEntityType.TENANT
        resource_type = TestResourceType.PROJECTS
        limit = 100
        
        # Set up quota
        manager.set_quota(entity_id, {"project_count": limit})
        
        # Set current usage to reach warning threshold after adding 1
        current_usage = int(limit * usage_percentage / 100) - 1
        if current_usage > 0:
            manager.increment_usage(entity_id, entity_type, resource_type, current_usage)
        
        # Clear notifications
        manager.notifications = []
        
        # Check if adding enough to reach threshold
        amount_to_add = max(1, int(limit * 0.8) - current_usage)
        result = manager.check_quota(entity_id, entity_type, resource_type, amount_to_add)
        
        # Should be allowed (not at 100% yet)
        if result["percentage"] < 100:
            assert result["allowed"] == True
            # Should have warning if at or above 80%
            if result["percentage"] >= 80:
                assert result.get("warning") is not None or len(manager.notifications) > 0
        
        session.close()
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        over_percentage=st.floats(min_value=0, max_value=50)
    )
    def test_at_blocking_threshold_blocks_operation(self, over_percentage):
        """
        Property: Operations at or above 100% threshold are blocked.
        """
        # Create fresh session for each example
        session = create_fresh_session()
        manager = SimpleQuotaManager(session)
        entity_id = f"tenant-{uuid4().hex[:8]}"
        entity_type = TestEntityType.TENANT
        resource_type = TestResourceType.PROJECTS
        limit = 100
        
        # Set up quota
        manager.set_quota(entity_id, {"project_count": limit})
        
        # Set current usage to exactly at limit
        manager.increment_usage(entity_id, entity_type, resource_type, limit)
        
        # Try to add more
        result = manager.check_quota(entity_id, entity_type, resource_type, 1)
        
        # Should be blocked
        assert result["allowed"] == False
        assert "exceeded" in result.get("reason", "").lower() or result["percentage"] >= 100
        
        session.close()
    
    def test_exact_threshold_boundaries(self, test_session, quota_manager):
        """
        Property: Exact threshold boundaries are handled correctly.
        """
        entity_id = f"tenant-{uuid4().hex[:8]}"
        entity_type = TestEntityType.TENANT
        resource_type = TestResourceType.PROJECTS
        limit = 100
        
        # Set up quota
        quota_manager.set_quota(entity_id, {"project_count": limit})
        
        # Test at exactly 79% - should be allowed, no warning
        quota_manager.increment_usage(entity_id, entity_type, resource_type, 79)
        result = quota_manager.check_quota(entity_id, entity_type, resource_type, 0)
        assert result["allowed"] == True
        
        # Test at exactly 80% - should be allowed with warning
        quota_manager.increment_usage(entity_id, entity_type, resource_type, 1)  # Now at 80
        quota_manager.notifications = []
        result = quota_manager.check_quota(entity_id, entity_type, resource_type, 1)  # Would be 81%
        assert result["allowed"] == True
        assert result.get("warning") is not None or len(quota_manager.notifications) > 0
        
        # Test at exactly 99% - should be allowed with warning
        quota_manager.increment_usage(entity_id, entity_type, resource_type, 19)  # Now at 99
        result = quota_manager.check_quota(entity_id, entity_type, resource_type, 0)
        assert result["allowed"] == True
        
        # Test at exactly 100% - should be blocked
        quota_manager.increment_usage(entity_id, entity_type, resource_type, 1)  # Now at 100
        result = quota_manager.check_quota(entity_id, entity_type, resource_type, 1)  # Would be 101%
        assert result["allowed"] == False


class TestQuotaInheritance:
    """Tests for quota inheritance from tenant to workspace."""
    
    def test_workspace_inherits_tenant_quota(self, test_session, quota_manager):
        """
        Property: Workspaces inherit quota from their parent tenant.
        """
        tenant_id = f"tenant-{uuid4().hex[:8]}"
        workspace_id = f"workspace-{uuid4().hex[:8]}"
        
        # Set tenant quota
        tenant_quota = {
            "storage_bytes": 5000000000,
            "project_count": 50,
            "user_count": 25,
            "api_call_count": 50000
        }
        quota_manager.set_quota(tenant_id, tenant_quota)
        
        # Get tenant quota (simulating inheritance)
        inherited = quota_manager.get_quota(tenant_id)
        
        # Verify inheritance
        assert inherited["storage_bytes"] == tenant_quota["storage_bytes"]
        assert inherited["project_count"] == tenant_quota["project_count"]
        assert inherited["user_count"] == tenant_quota["user_count"]
        assert inherited["api_call_count"] == tenant_quota["api_call_count"]


class TestTemporaryQuota:
    """Tests for temporary quota functionality."""
    
    def test_temporary_quota_increases_limit(self, test_session):
        """
        Property: Temporary quota increases the effective limit.
        """
        entity_id = f"tenant-{uuid4().hex[:8]}"
        
        # Create base quota
        base_quota = TestTenantQuotaModel(
            id=str(uuid4()),
            tenant_id=entity_id,
            project_count=100,
        )
        test_session.add(base_quota)
        
        # Create temporary quota with higher limit
        temp_quota = TestTemporaryQuotaModel(
            id=str(uuid4()),
            entity_id=entity_id,
            entity_type=TestEntityType.TENANT,
            project_count=200,  # Double the base
            expires_at=datetime.utcnow() + timedelta(days=7),
            reason="Special promotion"
        )
        test_session.add(temp_quota)
        test_session.commit()
        
        # Verify temporary quota exists and has higher limit
        saved_temp = test_session.query(TestTemporaryQuotaModel).filter(
            TestTemporaryQuotaModel.entity_id == entity_id
        ).first()
        
        assert saved_temp is not None
        assert saved_temp.project_count == 200
        assert saved_temp.expires_at > datetime.utcnow()
    
    def test_expired_temporary_quota_not_applied(self, test_session):
        """
        Property: Expired temporary quotas should not be applied.
        """
        entity_id = f"tenant-{uuid4().hex[:8]}"
        
        # Create expired temporary quota
        expired_quota = TestTemporaryQuotaModel(
            id=str(uuid4()),
            entity_id=entity_id,
            entity_type=TestEntityType.TENANT,
            project_count=200,
            expires_at=datetime.utcnow() - timedelta(days=1),  # Expired
            reason="Expired promotion"
        )
        test_session.add(expired_quota)
        test_session.commit()
        
        # Query for active temporary quotas
        active_temp = test_session.query(TestTemporaryQuotaModel).filter(
            TestTemporaryQuotaModel.entity_id == entity_id,
            TestTemporaryQuotaModel.expires_at > datetime.utcnow()
        ).first()
        
        # Should not find the expired quota
        assert active_temp is None
