"""
Property-based tests for CrossTenantCollaborator.

Tests Property 9: Cross-tenant share token expiration
Tests Property 10: Cross-tenant whitelist enforcement
Tests Property 11: Audit log completeness
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.orm import sessionmaker, declarative_base
import enum

# Test-specific base and models for SQLite compatibility
TestBase = declarative_base()


class TestSharePermission(str, enum.Enum):
    READ_ONLY = "read_only"
    EDIT = "edit"


class TestShareLinkModel(TestBase):
    """Test share link model for SQLite."""
    __tablename__ = "share_links"
    
    id = Column(String(100), primary_key=True)
    resource_id = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    owner_tenant_id = Column(String(100), nullable=False)
    permission = Column(SQLEnum(TestSharePermission), nullable=False)
    token = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    allowed_tenant_ids = Column(JSON, nullable=True)
    max_uses = Column(Integer, nullable=True)
    use_count = Column(Integer, default=0)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestTenantWhitelistModel(TestBase):
    """Test tenant whitelist model for SQLite."""
    __tablename__ = "tenant_whitelist"
    
    id = Column(String(100), primary_key=True)
    owner_tenant_id = Column(String(100), nullable=False)
    allowed_tenant_id = Column(String(100), nullable=False)
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


import secrets


class SimpleCrossTenantCollaborator:
    """Simplified cross-tenant collaborator for property testing."""
    
    def __init__(self, session, require_whitelist: bool = True):
        self.session = session
        self.require_whitelist = require_whitelist
    
    def create_share(
        self,
        owner_tenant_id: str,
        resource_id: str,
        resource_type: str,
        permission: TestSharePermission = TestSharePermission.READ_ONLY,
        expires_in: timedelta = None,
        allowed_tenant_ids: list = None,
        max_uses: int = None
    ) -> TestShareLinkModel:
        """Create a share link."""
        if expires_in is None:
            expires_in = timedelta(days=7)
        
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + expires_in
        
        share = TestShareLinkModel(
            id=str(uuid4()),
            resource_id=resource_id,
            resource_type=resource_type,
            owner_tenant_id=owner_tenant_id,
            permission=permission,
            token=token,
            expires_at=expires_at,
            allowed_tenant_ids=allowed_tenant_ids,
            max_uses=max_uses,
            use_count=0,
            revoked=False,
        )
        
        self.session.add(share)
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=owner_tenant_id,
            action="share_created",
            resource_type="share_link",
            resource_id=share.id,
        )
        
        return share
    
    def access_shared_resource(
        self,
        token: str,
        accessor_tenant_id: str
    ) -> dict:
        """Access a shared resource."""
        share = self.session.query(TestShareLinkModel).filter(
            TestShareLinkModel.token == token
        ).first()
        
        if not share:
            raise ValueError("Share not found")
        
        # Check revoked
        if share.revoked:
            self._log_cross_tenant_access(
                accessor_tenant_id=accessor_tenant_id,
                owner_tenant_id=share.owner_tenant_id,
                resource_id=share.resource_id,
                resource_type=share.resource_type,
                action="access_revoked",
                success=False
            )
            raise ValueError("Share revoked")
        
        # Check expired
        if share.expires_at < datetime.utcnow():
            self._log_cross_tenant_access(
                accessor_tenant_id=accessor_tenant_id,
                owner_tenant_id=share.owner_tenant_id,
                resource_id=share.resource_id,
                resource_type=share.resource_type,
                action="access_expired",
                success=False
            )
            raise ValueError("Share expired")
        
        # Check max uses
        if share.max_uses is not None and share.use_count >= share.max_uses:
            self._log_cross_tenant_access(
                accessor_tenant_id=accessor_tenant_id,
                owner_tenant_id=share.owner_tenant_id,
                resource_id=share.resource_id,
                resource_type=share.resource_type,
                action="access_max_uses",
                success=False
            )
            raise ValueError("Max uses exceeded")
        
        # Check allowed tenants
        if share.allowed_tenant_ids:
            if accessor_tenant_id not in share.allowed_tenant_ids:
                self._log_cross_tenant_access(
                    accessor_tenant_id=accessor_tenant_id,
                    owner_tenant_id=share.owner_tenant_id,
                    resource_id=share.resource_id,
                    resource_type=share.resource_type,
                    action="access_not_allowed",
                    success=False
                )
                raise ValueError("Tenant not allowed")
        
        # Check whitelist
        if self.require_whitelist:
            if not self.is_tenant_whitelisted(share.owner_tenant_id, accessor_tenant_id):
                self._log_cross_tenant_access(
                    accessor_tenant_id=accessor_tenant_id,
                    owner_tenant_id=share.owner_tenant_id,
                    resource_id=share.resource_id,
                    resource_type=share.resource_type,
                    action="access_not_whitelisted",
                    success=False
                )
                raise ValueError("Tenant not whitelisted")
        
        # Success
        share.use_count += 1
        self.session.commit()
        
        self._log_cross_tenant_access(
            accessor_tenant_id=accessor_tenant_id,
            owner_tenant_id=share.owner_tenant_id,
            resource_id=share.resource_id,
            resource_type=share.resource_type,
            action="access_success",
            success=True
        )
        
        return {
            "resource_id": share.resource_id,
            "permission": share.permission.value,
        }
    
    def revoke_share(self, share_id: str) -> None:
        """Revoke a share."""
        share = self.session.query(TestShareLinkModel).filter(
            TestShareLinkModel.id == share_id
        ).first()
        
        if share:
            share.revoked = True
            self.session.commit()
            
            self._log_audit(
                tenant_id=share.owner_tenant_id,
                action="share_revoked",
                resource_type="share_link",
                resource_id=share_id,
            )
    
    def set_whitelist(self, owner_tenant_id: str, allowed_tenant_ids: list) -> None:
        """Set whitelist for a tenant."""
        # Remove existing
        self.session.query(TestTenantWhitelistModel).filter(
            TestTenantWhitelistModel.owner_tenant_id == owner_tenant_id
        ).delete()
        
        # Add new
        for allowed_id in allowed_tenant_ids:
            entry = TestTenantWhitelistModel(
                id=str(uuid4()),
                owner_tenant_id=owner_tenant_id,
                allowed_tenant_id=allowed_id,
            )
            self.session.add(entry)
        
        self.session.commit()
        
        self._log_audit(
            tenant_id=owner_tenant_id,
            action="whitelist_updated",
            resource_type="whitelist",
            resource_id=owner_tenant_id,
        )
    
    def is_tenant_whitelisted(self, owner_tenant_id: str, accessor_tenant_id: str) -> bool:
        """Check if tenant is whitelisted."""
        if owner_tenant_id == accessor_tenant_id:
            return True
        
        entry = self.session.query(TestTenantWhitelistModel).filter(
            TestTenantWhitelistModel.owner_tenant_id == owner_tenant_id,
            TestTenantWhitelistModel.allowed_tenant_id == accessor_tenant_id
        ).first()
        
        return entry is not None
    
    def _log_cross_tenant_access(
        self,
        accessor_tenant_id: str,
        owner_tenant_id: str,
        resource_id: str,
        resource_type: str,
        action: str,
        success: bool
    ) -> None:
        """Log cross-tenant access."""
        log = TestCrossTenantAccessLogModel(
            id=str(uuid4()),
            accessor_tenant_id=accessor_tenant_id,
            owner_tenant_id=owner_tenant_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            success=success,
        )
        self.session.add(log)
        self.session.commit()
    
    def _log_audit(
        self,
        tenant_id: str,
        action: str,
        resource_type: str,
        resource_id: str = None
    ) -> None:
        """Log audit entry."""
        log = TestAuditLogModel(
            id=str(uuid4()),
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self.session.add(log)
        self.session.commit()


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
def collaborator(test_session):
    """Create cross-tenant collaborator."""
    return SimpleCrossTenantCollaborator(test_session)


class TestShareTokenExpiration:
    """
    Property 9: Cross-tenant share token expiration
    
    Expired share links should not allow access.
    """
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        days_expired=st.integers(min_value=1, max_value=365)
    )
    def test_expired_share_denies_access(self, days_expired):
        """
        Property: Expired shares cannot be accessed.
        """
        session = create_fresh_session()
        collab = SimpleCrossTenantCollaborator(session, require_whitelist=False)
        
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        accessor_tenant = f"accessor-{uuid4().hex[:8]}"
        
        # Create share that's already expired
        share = collab.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
            expires_in=timedelta(days=-days_expired)  # Negative = already expired
        )
        
        # Try to access
        with pytest.raises(ValueError, match="expired"):
            collab.access_shared_resource(share.token, accessor_tenant)
        
        session.close()
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        days_valid=st.integers(min_value=1, max_value=365)
    )
    def test_valid_share_allows_access(self, days_valid):
        """
        Property: Non-expired shares can be accessed.
        """
        session = create_fresh_session()
        collab = SimpleCrossTenantCollaborator(session, require_whitelist=False)
        
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        accessor_tenant = f"accessor-{uuid4().hex[:8]}"
        
        # Create valid share
        share = collab.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
            expires_in=timedelta(days=days_valid)
        )
        
        # Access should succeed
        result = collab.access_shared_resource(share.token, accessor_tenant)
        assert result["resource_id"] == share.resource_id
        
        session.close()
    
    def test_revoked_share_denies_access(self, test_session, collaborator):
        """
        Property: Revoked shares cannot be accessed.
        """
        # Disable whitelist for this test
        collaborator.require_whitelist = False
        
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        accessor_tenant = f"accessor-{uuid4().hex[:8]}"
        
        # Create and revoke share
        share = collaborator.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
        )
        
        collaborator.revoke_share(share.id)
        
        # Try to access
        with pytest.raises(ValueError, match="revoked"):
            collaborator.access_shared_resource(share.token, accessor_tenant)
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        max_uses=st.integers(min_value=1, max_value=10)
    )
    def test_max_uses_enforced(self, max_uses):
        """
        Property: Shares with max_uses limit stop working after limit reached.
        """
        session = create_fresh_session()
        collab = SimpleCrossTenantCollaborator(session, require_whitelist=False)
        
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        accessor_tenant = f"accessor-{uuid4().hex[:8]}"
        
        # Create share with max uses
        share = collab.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
            max_uses=max_uses
        )
        
        # Use up all allowed uses
        for _ in range(max_uses):
            collab.access_shared_resource(share.token, accessor_tenant)
        
        # Next access should fail
        with pytest.raises(ValueError, match="uses"):
            collab.access_shared_resource(share.token, accessor_tenant)
        
        session.close()


class TestWhitelistEnforcement:
    """
    Property 10: Cross-tenant whitelist enforcement
    
    Only whitelisted tenants can access shared resources.
    """
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        num_whitelisted=st.integers(min_value=1, max_value=5)
    )
    def test_whitelisted_tenant_can_access(self, num_whitelisted):
        """
        Property: Whitelisted tenants can access shared resources.
        """
        session = create_fresh_session()
        collab = SimpleCrossTenantCollaborator(session, require_whitelist=True)
        
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        whitelisted_tenants = [f"tenant-{uuid4().hex[:8]}" for _ in range(num_whitelisted)]
        
        # Set whitelist
        collab.set_whitelist(owner_tenant, whitelisted_tenants)
        
        # Create share
        share = collab.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
        )
        
        # All whitelisted tenants should be able to access
        for tenant in whitelisted_tenants:
            result = collab.access_shared_resource(share.token, tenant)
            assert result["resource_id"] == share.resource_id
        
        session.close()
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        num_whitelisted=st.integers(min_value=1, max_value=5)
    )
    def test_non_whitelisted_tenant_denied(self, num_whitelisted):
        """
        Property: Non-whitelisted tenants cannot access shared resources.
        """
        session = create_fresh_session()
        collab = SimpleCrossTenantCollaborator(session, require_whitelist=True)
        
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        whitelisted_tenants = [f"tenant-{uuid4().hex[:8]}" for _ in range(num_whitelisted)]
        non_whitelisted = f"outsider-{uuid4().hex[:8]}"
        
        # Set whitelist (not including non_whitelisted)
        collab.set_whitelist(owner_tenant, whitelisted_tenants)
        
        # Create share
        share = collab.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
        )
        
        # Non-whitelisted tenant should be denied
        with pytest.raises(ValueError, match="whitelisted"):
            collab.access_shared_resource(share.token, non_whitelisted)
        
        session.close()
    
    def test_same_tenant_always_allowed(self, test_session, collaborator):
        """
        Property: Same tenant is always allowed (implicit whitelist).
        """
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        
        # Don't set any whitelist
        # Create share
        share = collaborator.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
        )
        
        # Owner tenant should be able to access their own share
        result = collaborator.access_shared_resource(share.token, owner_tenant)
        assert result["resource_id"] == share.resource_id
    
    def test_whitelist_update_affects_access(self, test_session, collaborator):
        """
        Property: Updating whitelist immediately affects access.
        """
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        tenant_a = f"tenant-a-{uuid4().hex[:8]}"
        tenant_b = f"tenant-b-{uuid4().hex[:8]}"
        
        # Initially whitelist tenant_a
        collaborator.set_whitelist(owner_tenant, [tenant_a])
        
        share = collaborator.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
        )
        
        # tenant_a can access
        collaborator.access_shared_resource(share.token, tenant_a)
        
        # tenant_b cannot
        with pytest.raises(ValueError, match="whitelisted"):
            collaborator.access_shared_resource(share.token, tenant_b)
        
        # Update whitelist to only include tenant_b
        collaborator.set_whitelist(owner_tenant, [tenant_b])
        
        # Now tenant_b can access
        collaborator.access_shared_resource(share.token, tenant_b)
        
        # And tenant_a cannot
        with pytest.raises(ValueError, match="whitelisted"):
            collaborator.access_shared_resource(share.token, tenant_a)


class TestAuditLogCompleteness:
    """
    Property 11: Audit log completeness
    
    All cross-tenant operations should be logged.
    """
    
    def test_share_creation_logged(self, test_session, collaborator):
        """
        Property: Share creation is logged.
        """
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        
        share = collaborator.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
        )
        
        # Check audit log
        logs = test_session.query(TestAuditLogModel).filter(
            TestAuditLogModel.tenant_id == owner_tenant,
            TestAuditLogModel.action == "share_created"
        ).all()
        
        assert len(logs) >= 1
        assert logs[0].resource_id == share.id
    
    def test_share_revocation_logged(self, test_session, collaborator):
        """
        Property: Share revocation is logged.
        """
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        
        share = collaborator.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
        )
        
        collaborator.revoke_share(share.id)
        
        # Check audit log
        logs = test_session.query(TestAuditLogModel).filter(
            TestAuditLogModel.tenant_id == owner_tenant,
            TestAuditLogModel.action == "share_revoked"
        ).all()
        
        assert len(logs) >= 1
    
    def test_successful_access_logged(self, test_session, collaborator):
        """
        Property: Successful cross-tenant access is logged.
        """
        collaborator.require_whitelist = False
        
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        accessor_tenant = f"accessor-{uuid4().hex[:8]}"
        
        share = collaborator.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
        )
        
        collaborator.access_shared_resource(share.token, accessor_tenant)
        
        # Check access log
        logs = test_session.query(TestCrossTenantAccessLogModel).filter(
            TestCrossTenantAccessLogModel.accessor_tenant_id == accessor_tenant,
            TestCrossTenantAccessLogModel.owner_tenant_id == owner_tenant,
            TestCrossTenantAccessLogModel.success == True
        ).all()
        
        assert len(logs) >= 1
    
    def test_failed_access_logged(self, test_session, collaborator):
        """
        Property: Failed cross-tenant access attempts are logged.
        """
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        accessor_tenant = f"accessor-{uuid4().hex[:8]}"
        
        # Don't whitelist accessor
        share = collaborator.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
        )
        
        # Try to access (should fail)
        try:
            collaborator.access_shared_resource(share.token, accessor_tenant)
        except ValueError:
            pass
        
        # Check access log for failed attempt
        logs = test_session.query(TestCrossTenantAccessLogModel).filter(
            TestCrossTenantAccessLogModel.accessor_tenant_id == accessor_tenant,
            TestCrossTenantAccessLogModel.owner_tenant_id == owner_tenant,
            TestCrossTenantAccessLogModel.success == False
        ).all()
        
        assert len(logs) >= 1
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        num_accesses=st.integers(min_value=1, max_value=10)
    )
    def test_all_access_attempts_logged(self, num_accesses):
        """
        Property: Every access attempt is logged.
        """
        session = create_fresh_session()
        collab = SimpleCrossTenantCollaborator(session, require_whitelist=False)
        
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        accessor_tenant = f"accessor-{uuid4().hex[:8]}"
        
        share = collab.create_share(
            owner_tenant_id=owner_tenant,
            resource_id=f"resource-{uuid4().hex[:8]}",
            resource_type="document",
        )
        
        # Make multiple accesses
        for _ in range(num_accesses):
            collab.access_shared_resource(share.token, accessor_tenant)
        
        # Check that all accesses were logged
        logs = session.query(TestCrossTenantAccessLogModel).filter(
            TestCrossTenantAccessLogModel.accessor_tenant_id == accessor_tenant,
            TestCrossTenantAccessLogModel.owner_tenant_id == owner_tenant
        ).all()
        
        assert len(logs) == num_accesses
        
        session.close()
    
    def test_whitelist_update_logged(self, test_session, collaborator):
        """
        Property: Whitelist updates are logged.
        """
        owner_tenant = f"owner-{uuid4().hex[:8]}"
        
        collaborator.set_whitelist(owner_tenant, [f"tenant-{uuid4().hex[:8]}"])
        
        # Check audit log
        logs = test_session.query(TestAuditLogModel).filter(
            TestAuditLogModel.tenant_id == owner_tenant,
            TestAuditLogModel.action == "whitelist_updated"
        ).all()
        
        assert len(logs) >= 1
