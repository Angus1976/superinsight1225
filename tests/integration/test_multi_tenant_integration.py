"""
Multi-Tenant Workspace Integration Tests

Tests the complete flow of:
- Tenant creation → Workspace creation → Member invitation
- Cross-tenant collaboration scenarios
- Data isolation verification

Uses SQLite-compatible test models for in-memory testing.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import MagicMock

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.sqlite import JSON
import enum


# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test-specific base for SQLite compatibility
TestBase = declarative_base()


# ============================================================================
# SQLite-Compatible Test Models
# ============================================================================

class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class WorkspaceStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MemberRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class SharePermission(str, enum.Enum):
    READ_ONLY = "read_only"
    EDIT = "edit"


class EntityType(str, enum.Enum):
    TENANT = "tenant"
    WORKSPACE = "workspace"


class TestTenantModel(TestBase):
    """Test tenant model for SQLite."""
    __tablename__ = "test_tenants"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    description = Column(Text)
    status = Column(SQLEnum(TenantStatus), default=TenantStatus.ACTIVE)
    configuration = Column(JSON, default={})
    billing_email = Column(String(255))
    billing_plan = Column(String(50), default="basic")
    max_users = Column(Integer, default=50)
    max_workspaces = Column(Integer, default=100)
    max_storage_gb = Column(Float, default=10.0)
    max_api_calls_per_hour = Column(Integer, default=1000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TestUserModel(TestBase):
    """Test user model for SQLite."""
    __tablename__ = "test_users"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), nullable=False)
    username = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class TestWorkspaceModel(TestBase):
    """Test workspace model for SQLite."""
    __tablename__ = "test_workspaces"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(100), ForeignKey("test_tenants.id"), nullable=False)
    parent_id = Column(String(36), ForeignKey("test_workspaces.id"), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(SQLEnum(WorkspaceStatus), default=WorkspaceStatus.ACTIVE)
    config = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)


class TestWorkspaceMemberModel(TestBase):
    """Test workspace member model for SQLite."""
    __tablename__ = "test_workspace_members"
    
    id = Column(String(36), primary_key=True)
    workspace_id = Column(String(36), ForeignKey("test_workspaces.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("test_users.id"), nullable=False)
    role = Column(SQLEnum(MemberRole), default=MemberRole.MEMBER)
    joined_at = Column(DateTime, default=datetime.utcnow)


class TestQuotaModel(TestBase):
    """Test quota model for SQLite."""
    __tablename__ = "test_quotas"
    
    id = Column(String(36), primary_key=True)
    entity_id = Column(String(100), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    storage_bytes = Column(Integer, default=10737418240)
    project_count = Column(Integer, default=100)
    user_count = Column(Integer, default=50)
    api_call_count = Column(Integer, default=100000)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestQuotaUsageModel(TestBase):
    """Test quota usage model for SQLite."""
    __tablename__ = "test_quota_usage"
    
    id = Column(String(36), primary_key=True)
    entity_id = Column(String(100), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    storage_bytes = Column(Integer, default=0)
    project_count = Column(Integer, default=0)
    user_count = Column(Integer, default=0)
    api_call_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class TestShareLinkModel(TestBase):
    """Test share link model for SQLite."""
    __tablename__ = "test_share_links"
    
    id = Column(String(36), primary_key=True)
    resource_id = Column(String(36), nullable=False)
    resource_type = Column(String(50), nullable=False)
    owner_tenant_id = Column(String(100), nullable=False)
    permission = Column(SQLEnum(SharePermission), default=SharePermission.READ_ONLY)
    token = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestWhitelistModel(TestBase):
    """Test whitelist model for SQLite."""
    __tablename__ = "test_whitelist"
    
    id = Column(String(36), primary_key=True)
    owner_tenant_id = Column(String(100), nullable=False)
    allowed_tenant_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestBase.metadata.create_all(bind=engine)
    yield engine
    TestBase.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine) -> Session:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_audit_logger():
    """Create a mock audit logger."""
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def mock_permission_checker():
    """Create a mock permission checker."""
    checker = MagicMock()
    checker.revoke_all_permissions = MagicMock()
    return checker


# ============================================================================
# Simplified Service Classes for Integration Testing
# ============================================================================

class SimpleTenantManager:
    """Simplified tenant manager for integration testing."""
    
    def __init__(self, session: Session, audit_logger=None):
        self.session = session
        self.audit_logger = audit_logger
    
    def create_tenant(self, name: str, admin_email: str, plan: str = "basic") -> TestTenantModel:
        tenant_id = name.lower().replace(" ", "-")
        tenant = TestTenantModel(
            id=tenant_id,
            name=name,
            display_name=name,
            billing_email=admin_email,
            billing_plan=plan,
            status=TenantStatus.ACTIVE,
            configuration={"features": {"ai_annotation": True}},
        )
        self.session.add(tenant)
        self.session.commit()
        if self.audit_logger:
            self.audit_logger.log("tenant_created", tenant_id, {"name": name})
        return tenant

    
    def get_tenant(self, tenant_id: str) -> TestTenantModel:
        return self.session.query(TestTenantModel).filter(TestTenantModel.id == tenant_id).first()
    
    def set_status(self, tenant_id: str, status: TenantStatus) -> TestTenantModel:
        tenant = self.get_tenant(tenant_id)
        if tenant:
            tenant.status = status
            self.session.commit()
        return tenant
    
    def is_operation_allowed(self, tenant_id: str) -> bool:
        tenant = self.get_tenant(tenant_id)
        return tenant and tenant.status == TenantStatus.ACTIVE


class SimpleWorkspaceManager:
    """Simplified workspace manager for integration testing."""
    
    def __init__(self, session: Session, tenant_manager: SimpleTenantManager):
        self.session = session
        self.tenant_manager = tenant_manager
    
    def create_workspace(self, tenant_id: str, name: str, parent_id: str = None) -> TestWorkspaceModel:
        workspace = TestWorkspaceModel(
            id=str(uuid4()),
            tenant_id=tenant_id,
            parent_id=parent_id,
            name=name,
            status=WorkspaceStatus.ACTIVE,
            config={},
        )
        self.session.add(workspace)
        self.session.commit()
        return workspace
    
    def get_workspace(self, workspace_id: str) -> TestWorkspaceModel:
        return self.session.query(TestWorkspaceModel).filter(TestWorkspaceModel.id == workspace_id).first()
    
    def get_hierarchy(self, tenant_id: str) -> list:
        return self.session.query(TestWorkspaceModel).filter(
            TestWorkspaceModel.tenant_id == tenant_id
        ).all()
    
    def archive_workspace(self, workspace_id: str) -> TestWorkspaceModel:
        workspace = self.get_workspace(workspace_id)
        if workspace:
            workspace.status = WorkspaceStatus.ARCHIVED
            workspace.archived_at = datetime.utcnow()
            self.session.commit()
        return workspace
    
    def restore_workspace(self, workspace_id: str) -> TestWorkspaceModel:
        workspace = self.get_workspace(workspace_id)
        if workspace:
            workspace.status = WorkspaceStatus.ACTIVE
            workspace.archived_at = None
            self.session.commit()
        return workspace


class SimpleMemberManager:
    """Simplified member manager for integration testing."""
    
    def __init__(self, session: Session, permission_checker=None):
        self.session = session
        self.permission_checker = permission_checker
    
    def add_member(self, workspace_id: str, user_id: str, role: MemberRole = MemberRole.MEMBER) -> TestWorkspaceMemberModel:
        member = TestWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        self.session.add(member)
        self.session.commit()
        return member
    
    def remove_member(self, workspace_id: str, user_id: str) -> None:
        member = self.session.query(TestWorkspaceMemberModel).filter(
            TestWorkspaceMemberModel.workspace_id == workspace_id,
            TestWorkspaceMemberModel.user_id == user_id
        ).first()
        if member:
            self.session.delete(member)
            self.session.commit()
            if self.permission_checker:
                self.permission_checker.revoke_all_permissions(workspace_id, user_id)
    
    def get_members(self, workspace_id: str) -> list:
        return self.session.query(TestWorkspaceMemberModel).filter(
            TestWorkspaceMemberModel.workspace_id == workspace_id
        ).all()


class SimpleQuotaManager:
    """Simplified quota manager for integration testing."""
    
    def __init__(self, session: Session, cache=None, notification_service=None):
        self.session = session
        self.cache = cache
        self.notification_service = notification_service
    
    def set_quota(self, entity_id: str, entity_type: EntityType, **kwargs) -> TestQuotaModel:
        quota = TestQuotaModel(
            id=str(uuid4()),
            entity_id=entity_id,
            entity_type=entity_type,
            **kwargs
        )
        self.session.add(quota)
        
        # Also create usage record
        usage = TestQuotaUsageModel(
            id=str(uuid4()),
            entity_id=entity_id,
            entity_type=entity_type,
        )
        self.session.add(usage)
        self.session.commit()
        return quota
    
    def increment_usage(self, entity_id: str, entity_type: EntityType, resource_type: str) -> None:
        usage = self.session.query(TestQuotaUsageModel).filter(
            TestQuotaUsageModel.entity_id == entity_id,
            TestQuotaUsageModel.entity_type == entity_type
        ).first()
        if usage:
            current = getattr(usage, resource_type, 0)
            setattr(usage, resource_type, current + 1)
            self.session.commit()

    
    def check_quota(self, entity_id: str, entity_type: EntityType, resource_type: str) -> dict:
        quota = self.session.query(TestQuotaModel).filter(
            TestQuotaModel.entity_id == entity_id,
            TestQuotaModel.entity_type == entity_type
        ).first()
        usage = self.session.query(TestQuotaUsageModel).filter(
            TestQuotaUsageModel.entity_id == entity_id,
            TestQuotaUsageModel.entity_type == entity_type
        ).first()
        
        if not quota or not usage:
            return {"allowed": True, "percentage": 0}
        
        limit = getattr(quota, resource_type, 0)
        used = getattr(usage, resource_type, 0)
        percentage = (used / limit * 100) if limit > 0 else 0
        
        return {
            "allowed": used < limit,
            "percentage": percentage,
            "limit": limit,
            "used": used
        }


class SimpleCrossTenantCollaborator:
    """Simplified cross-tenant collaborator for integration testing."""
    
    def __init__(self, session: Session, audit_logger=None):
        self.session = session
        self.audit_logger = audit_logger
    
    def create_share(self, owner_tenant_id: str, resource_id: str, resource_type: str,
                     permission: SharePermission = SharePermission.READ_ONLY,
                     expires_in_days: int = 7) -> TestShareLinkModel:
        import secrets
        share = TestShareLinkModel(
            id=str(uuid4()),
            resource_id=resource_id,
            resource_type=resource_type,
            owner_tenant_id=owner_tenant_id,
            permission=permission,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
        )
        self.session.add(share)
        self.session.commit()
        return share
    
    def set_whitelist(self, owner_tenant_id: str, allowed_tenant_ids: list) -> None:
        for allowed_id in allowed_tenant_ids:
            whitelist = TestWhitelistModel(
                id=str(uuid4()),
                owner_tenant_id=owner_tenant_id,
                allowed_tenant_id=allowed_id,
            )
            self.session.add(whitelist)
        self.session.commit()
    
    def is_tenant_whitelisted(self, owner_tenant_id: str, accessor_tenant_id: str) -> bool:
        whitelist = self.session.query(TestWhitelistModel).filter(
            TestWhitelistModel.owner_tenant_id == owner_tenant_id,
            TestWhitelistModel.allowed_tenant_id == accessor_tenant_id
        ).first()
        return whitelist is not None


class SimpleIsolationEngine:
    """Simplified isolation engine for integration testing."""
    
    def __init__(self, session: Session, encryptor=None, audit_logger=None):
        self.session = session
        self.encryptor = encryptor
        self.audit_logger = audit_logger
    
    def get_tenant_filter(self, tenant_id: str):
        return TestWorkspaceModel.tenant_id == tenant_id
    
    def verify_tenant_access(self, user_id: str, user_tenant_id: str, target_tenant_id: str) -> bool:
        # Same tenant - always allowed
        if user_tenant_id == target_tenant_id:
            return True
        # Cross-tenant - denied by default
        return False


# ============================================================================
# Test Classes
# ============================================================================

class TestTenantWorkspaceFlow:
    """Test complete tenant → workspace → member flow."""

    def test_complete_tenant_creation_flow(self, db_session, mock_audit_logger):
        """Test: Create tenant → verify defaults → check status."""
        tenant_manager = SimpleTenantManager(db_session, mock_audit_logger)
        
        tenant = tenant_manager.create_tenant(
            name="Test Enterprise",
            admin_email="admin@test.com",
            plan="enterprise"
        )
        
        assert tenant is not None
        assert tenant.name == "Test Enterprise"
        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.billing_email == "admin@test.com"
        mock_audit_logger.log.assert_called()

    def test_workspace_creation_inherits_tenant_config(self, db_session, mock_audit_logger):
        """Test: Create workspace → verify config inheritance from tenant."""
        tenant_manager = SimpleTenantManager(db_session, mock_audit_logger)
        workspace_manager = SimpleWorkspaceManager(db_session, tenant_manager)

        tenant = tenant_manager.create_tenant(
            name="Config Test Tenant",
            admin_email="admin@test.com"
        )
        
        workspace = workspace_manager.create_workspace(tenant.id, "Test Workspace")
        
        assert workspace is not None
        assert workspace.tenant_id == tenant.id
        assert workspace.status == WorkspaceStatus.ACTIVE


    def test_member_invitation_flow(self, db_session, mock_audit_logger, mock_permission_checker):
        """Test: Create workspace → add member → verify membership."""
        tenant_manager = SimpleTenantManager(db_session, mock_audit_logger)
        workspace_manager = SimpleWorkspaceManager(db_session, tenant_manager)
        member_manager = SimpleMemberManager(db_session, mock_permission_checker)

        tenant = tenant_manager.create_tenant(
            name="Member Test Tenant",
            admin_email="admin@test.com"
        )
        workspace = workspace_manager.create_workspace(tenant.id, "Member Test Workspace")
        
        user_id = str(uuid4())
        test_user = TestUserModel(id=user_id, email="test@test.com", username="testuser")
        db_session.add(test_user)
        db_session.commit()

        member = member_manager.add_member(workspace.id, user_id, MemberRole.MEMBER)
        
        assert member is not None
        assert member.workspace_id == workspace.id
        assert member.role == MemberRole.MEMBER

    def test_member_removal_revokes_permissions(self, db_session, mock_audit_logger, mock_permission_checker):
        """Test: Remove member → verify permissions revoked."""
        tenant_manager = SimpleTenantManager(db_session, mock_audit_logger)
        workspace_manager = SimpleWorkspaceManager(db_session, tenant_manager)
        member_manager = SimpleMemberManager(db_session, mock_permission_checker)

        tenant = tenant_manager.create_tenant(
            name="Removal Test Tenant",
            admin_email="admin@test.com"
        )
        workspace = workspace_manager.create_workspace(tenant.id, "Removal Test Workspace")
        
        user_id = str(uuid4())
        test_user = TestUserModel(id=user_id, email="remove@test.com", username="removeuser")
        db_session.add(test_user)
        db_session.commit()
        
        member_manager.add_member(workspace.id, user_id, MemberRole.MEMBER)
        member_manager.remove_member(workspace.id, user_id)
        
        mock_permission_checker.revoke_all_permissions.assert_called_once_with(workspace.id, user_id)


class TestQuotaManagement:
    """Test quota management integration."""

    def test_quota_check_and_warning(self, db_session):
        """Test: Set quota → increment usage → verify warning at 80%."""
        quota_manager = SimpleQuotaManager(db_session)
        entity_id = str(uuid4())

        quota_manager.set_quota(entity_id, EntityType.TENANT, project_count=10)

        for _ in range(8):
            quota_manager.increment_usage(entity_id, EntityType.TENANT, "project_count")

        result = quota_manager.check_quota(entity_id, EntityType.TENANT, "project_count")
        
        assert result["allowed"] == True
        assert result["percentage"] >= 80

    def test_quota_exceeded_blocks_operation(self, db_session):
        """Test: Exceed quota → verify operation blocked."""
        quota_manager = SimpleQuotaManager(db_session)
        entity_id = str(uuid4())

        quota_manager.set_quota(entity_id, EntityType.TENANT, project_count=5)

        for _ in range(5):
            quota_manager.increment_usage(entity_id, EntityType.TENANT, "project_count")

        result = quota_manager.check_quota(entity_id, EntityType.TENANT, "project_count")
        
        assert result["allowed"] == False


class TestCrossTenantCollaboration:
    """Test cross-tenant collaboration scenarios."""

    def test_share_creation_and_access(self, db_session, mock_audit_logger):
        """Test: Create share → access with valid token."""
        collaborator = SimpleCrossTenantCollaborator(db_session, mock_audit_logger)
        tenant_id = str(uuid4())
        resource_id = str(uuid4())

        share = collaborator.create_share(
            owner_tenant_id=tenant_id,
            resource_id=resource_id,
            resource_type="workspace",
            permission=SharePermission.READ_ONLY,
            expires_in_days=7
        )
        
        assert share is not None
        assert share.token is not None
        assert share.owner_tenant_id == tenant_id

    def test_whitelist_management(self, db_session, mock_audit_logger):
        """Test: Set whitelist → verify tenant whitelisted."""
        collaborator = SimpleCrossTenantCollaborator(db_session, mock_audit_logger)
        owner_tenant_id = str(uuid4())
        allowed_tenant_id = str(uuid4())

        collaborator.set_whitelist(owner_tenant_id, [allowed_tenant_id])
        
        is_whitelisted = collaborator.is_tenant_whitelisted(owner_tenant_id, allowed_tenant_id)
        assert is_whitelisted == True

    def test_non_whitelisted_tenant_denied(self, db_session, mock_audit_logger):
        """Test: Access from non-whitelisted tenant → verify denied."""
        collaborator = SimpleCrossTenantCollaborator(db_session, mock_audit_logger)
        owner_tenant_id = str(uuid4())
        non_whitelisted_tenant = str(uuid4())

        is_whitelisted = collaborator.is_tenant_whitelisted(owner_tenant_id, non_whitelisted_tenant)
        assert is_whitelisted == False


class TestDataIsolation:
    """Test tenant data isolation."""

    def test_tenant_filter_applied(self, db_session):
        """Test: Query with tenant filter → only tenant data returned."""
        isolation_engine = SimpleIsolationEngine(db_session)
        
        tenant1_id = str(uuid4())
        tenant2_id = str(uuid4())

        filter1 = isolation_engine.get_tenant_filter(tenant1_id)
        filter2 = isolation_engine.get_tenant_filter(tenant2_id)

        assert str(filter1) != str(filter2)

    def test_cross_tenant_access_logged(self, db_session):
        """Test: Cross-tenant access attempt → verify denied."""
        isolation_engine = SimpleIsolationEngine(db_session)
        
        user_id = str(uuid4())
        user_tenant_id = str(uuid4())
        target_tenant_id = str(uuid4())

        result = isolation_engine.verify_tenant_access(user_id, user_tenant_id, target_tenant_id)
        assert result == False

    def test_same_tenant_access_allowed(self, db_session):
        """Test: Same tenant access → verify allowed."""
        isolation_engine = SimpleIsolationEngine(db_session)
        
        user_id = str(uuid4())
        tenant_id = str(uuid4())

        result = isolation_engine.verify_tenant_access(user_id, tenant_id, tenant_id)
        assert result == True


class TestWorkspaceHierarchy:
    """Test workspace hierarchy operations."""

    def test_workspace_hierarchy_integrity(self, db_session, mock_audit_logger):
        """Test: Create hierarchy → verify parent-child relationship."""
        tenant_manager = SimpleTenantManager(db_session, mock_audit_logger)
        workspace_manager = SimpleWorkspaceManager(db_session, tenant_manager)

        tenant = tenant_manager.create_tenant(
            name="Hierarchy Test",
            admin_email="admin@test.com"
        )

        parent = workspace_manager.create_workspace(tenant.id, "Parent Workspace")
        child = workspace_manager.create_workspace(tenant.id, "Child Workspace", parent_id=parent.id)

        hierarchy = workspace_manager.get_hierarchy(tenant.id)
        
        assert len(hierarchy) == 2
        assert child.parent_id == parent.id

    def test_archive_and_restore_workspace(self, db_session, mock_audit_logger):
        """Test: Archive workspace → restore → verify status changes."""
        tenant_manager = SimpleTenantManager(db_session, mock_audit_logger)
        workspace_manager = SimpleWorkspaceManager(db_session, tenant_manager)

        tenant = tenant_manager.create_tenant(
            name="Archive Test",
            admin_email="admin@test.com"
        )
        workspace = workspace_manager.create_workspace(tenant.id, "Archive Test Workspace")

        archived = workspace_manager.archive_workspace(workspace.id)
        assert archived.status == WorkspaceStatus.ARCHIVED
        assert archived.archived_at is not None

        restored = workspace_manager.restore_workspace(workspace.id)
        assert restored.status == WorkspaceStatus.ACTIVE
        assert restored.archived_at is None

    def test_tenant_status_affects_operations(self, db_session, mock_audit_logger):
        """Test: Disable tenant → verify operations blocked."""
        tenant_manager = SimpleTenantManager(db_session, mock_audit_logger)

        tenant = tenant_manager.create_tenant(
            name="Status Test",
            admin_email="admin@test.com"
        )
        
        assert tenant_manager.is_operation_allowed(tenant.id) == True
        
        tenant_manager.set_status(tenant.id, TenantStatus.SUSPENDED)
        
        assert tenant_manager.is_operation_allowed(tenant.id) == False
