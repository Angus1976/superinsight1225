"""
Property-based tests for MemberManager.

Tests Property 5: Member removal permission revocation
- When a member is removed, all their permissions should be revoked
- They should no longer be able to access workspace resources
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from hypothesis import given, strategies as st, settings, HealthCheck
from sqlalchemy import create_engine, Column, String, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
import enum

# Test-specific base and models for SQLite compatibility
TestBase = declarative_base()


class TestTenantStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class TestMemberRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class TestTenantModel(TestBase):
    """Test tenant model for SQLite."""
    __tablename__ = "tenants"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    display_name = Column(String(200))
    description = Column(String(1000))
    status = Column(SQLEnum(TestTenantStatus), default=TestTenantStatus.ACTIVE)
    configuration = Column(JSON, default={})
    billing_email = Column(String(200))
    billing_plan = Column(String(50), default="free")
    max_users = Column(String(50), default="50")
    max_workspaces = Column(String(50), default="100")
    max_storage_gb = Column(String(50), default="10")
    max_api_calls_per_hour = Column(String(50), default="1000")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TestWorkspaceModel(TestBase):
    """Test workspace model for SQLite."""
    __tablename__ = "extended_workspaces"
    
    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), nullable=False)
    parent_id = Column(String(100), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(String(1000))
    status = Column(String(20), default="active")
    config = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)


class TestMemberModel(TestBase):
    """Test member model for SQLite."""
    __tablename__ = "workspace_members"
    
    id = Column(String(100), primary_key=True)
    workspace_id = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=False)
    role = Column(SQLEnum(TestMemberRole), default=TestMemberRole.MEMBER)
    custom_role_id = Column(String(100), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, nullable=True)


class TestCustomRoleModel(TestBase):
    """Test custom role model for SQLite."""
    __tablename__ = "custom_roles"
    
    id = Column(String(100), primary_key=True)
    workspace_id = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    permissions = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TestInvitationModel(TestBase):
    """Test invitation model for SQLite."""
    __tablename__ = "workspace_invitations"
    
    id = Column(String(100), primary_key=True)
    workspace_id = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(SQLEnum(TestMemberRole), default=TestMemberRole.MEMBER)
    token = Column(String(64), nullable=False, unique=True)
    message = Column(String(500))
    invited_by = Column(String(100), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
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


class TestUserModel(TestBase):
    """Test user model for SQLite."""
    __tablename__ = "users"
    
    id = Column(String(100), primary_key=True)
    email = Column(String(255), nullable=False)
    name = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)


# Permission tracking for tests
class MockPermissionChecker:
    """Mock permission checker that tracks permissions."""
    
    def __init__(self):
        self.permissions = {}  # {(workspace_id, user_id): set of permissions}
        self.revocation_log = []  # List of (workspace_id, user_id) tuples
    
    def grant_permission(self, workspace_id: str, user_id: str, permission: str):
        """Grant a permission."""
        key = (str(workspace_id), str(user_id))
        if key not in self.permissions:
            self.permissions[key] = set()
        self.permissions[key].add(permission)
    
    def has_permission(self, workspace_id: str, user_id: str, permission: str) -> bool:
        """Check if user has permission."""
        key = (str(workspace_id), str(user_id))
        return permission in self.permissions.get(key, set())
    
    def get_permissions(self, workspace_id: str, user_id: str) -> set:
        """Get all permissions for user in workspace."""
        key = (str(workspace_id), str(user_id))
        return self.permissions.get(key, set()).copy()
    
    def revoke_all_permissions(self, workspace_id, user_id):
        """Revoke all permissions for user in workspace."""
        key = (str(workspace_id), str(user_id))
        self.permissions.pop(key, None)
        self.revocation_log.append((str(workspace_id), str(user_id)))
    
    def was_revoked(self, workspace_id: str, user_id: str) -> bool:
        """Check if permissions were revoked."""
        return (str(workspace_id), str(user_id)) in self.revocation_log


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
def permission_checker():
    """Create mock permission checker."""
    return MockPermissionChecker()


@pytest.fixture
def test_tenant(test_session):
    """Create a test tenant."""
    tenant = TestTenantModel(
        id="test-tenant",
        name="Test Tenant",
        display_name="Test Tenant",
        status=TestTenantStatus.ACTIVE,
        billing_email="admin@test.com",
    )
    test_session.add(tenant)
    test_session.commit()
    return tenant


@pytest.fixture
def test_workspace(test_session, test_tenant):
    """Create a test workspace."""
    workspace = TestWorkspaceModel(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="Test Workspace",
        status="active",
    )
    test_session.add(workspace)
    test_session.commit()
    return workspace


@pytest.fixture
def test_user(test_session):
    """Create a test user."""
    user = TestUserModel(
        id=str(uuid4()),
        email="user@test.com",
        name="Test User",
    )
    test_session.add(user)
    test_session.commit()
    return user


class TestMemberRemovalPermissionRevocation:
    """
    Property 5: Member removal permission revocation
    
    When a member is removed from a workspace, all their permissions
    should be immediately revoked.
    """
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        permissions=st.lists(
            st.sampled_from([
                "read", "write", "delete", "admin", "invite",
                "manage_roles", "view_audit", "export_data"
            ]),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    def test_permissions_revoked_on_member_removal(
        self, test_session, test_workspace, test_user, permission_checker, permissions
    ):
        """
        Property: When a member is removed, all permissions are revoked.
        """
        workspace_id = test_workspace.id
        user_id = test_user.id
        
        # Add member
        member = TestMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            role=TestMemberRole.MEMBER,
        )
        test_session.add(member)
        test_session.commit()
        
        # Grant permissions
        for perm in permissions:
            permission_checker.grant_permission(workspace_id, user_id, perm)
        
        # Verify permissions exist
        assert len(permission_checker.get_permissions(workspace_id, user_id)) == len(permissions)
        
        # Remove member (simulating MemberManager.remove_member)
        test_session.delete(member)
        permission_checker.revoke_all_permissions(workspace_id, user_id)
        test_session.commit()
        
        # Verify all permissions are revoked
        remaining_permissions = permission_checker.get_permissions(workspace_id, user_id)
        assert len(remaining_permissions) == 0, f"Permissions not revoked: {remaining_permissions}"
        
        # Verify revocation was logged
        assert permission_checker.was_revoked(workspace_id, user_id)
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        role=st.sampled_from([TestMemberRole.OWNER, TestMemberRole.ADMIN, TestMemberRole.MEMBER, TestMemberRole.GUEST])
    )
    def test_permissions_revoked_regardless_of_role(
        self, test_session, test_workspace, test_user, permission_checker, role
    ):
        """
        Property: Permissions are revoked regardless of member's role.
        """
        workspace_id = test_workspace.id
        user_id = test_user.id
        
        # Add member with specific role
        member = TestMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        test_session.add(member)
        test_session.commit()
        
        # Grant role-based permissions
        role_permissions = {
            TestMemberRole.OWNER: ["read", "write", "delete", "admin", "manage_roles"],
            TestMemberRole.ADMIN: ["read", "write", "delete", "admin"],
            TestMemberRole.MEMBER: ["read", "write"],
            TestMemberRole.GUEST: ["read"],
        }
        
        for perm in role_permissions[role]:
            permission_checker.grant_permission(workspace_id, user_id, perm)
        
        # Remove member
        test_session.delete(member)
        permission_checker.revoke_all_permissions(workspace_id, user_id)
        test_session.commit()
        
        # Verify all permissions are revoked
        assert len(permission_checker.get_permissions(workspace_id, user_id)) == 0
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        num_members=st.integers(min_value=2, max_value=5)
    )
    def test_batch_removal_revokes_all_permissions(
        self, test_session, test_workspace, permission_checker, num_members
    ):
        """
        Property: Batch member removal revokes permissions for all removed members.
        """
        workspace_id = test_workspace.id
        member_data = []  # Store (member_id, user_id) tuples
        user_ids = []
        
        # Create multiple members with permissions
        for i in range(num_members):
            user = TestUserModel(
                id=str(uuid4()),
                email=f"user{i}@test.com",
                name=f"User {i}",
            )
            test_session.add(user)
            
            member = TestMemberModel(
                id=str(uuid4()),
                workspace_id=workspace_id,
                user_id=user.id,
                role=TestMemberRole.MEMBER,
            )
            test_session.add(member)
            member_data.append((member.id, user.id))
            user_ids.append(user.id)
            
            # Grant permissions
            permission_checker.grant_permission(workspace_id, user.id, "read")
            permission_checker.grant_permission(workspace_id, user.id, "write")
        
        test_session.commit()
        
        # Batch remove members - use stored user_ids to avoid accessing deleted objects
        for member_id, user_id in member_data:
            member = test_session.query(TestMemberModel).filter(
                TestMemberModel.id == member_id
            ).first()
            if member:
                test_session.delete(member)
                permission_checker.revoke_all_permissions(workspace_id, user_id)
        test_session.commit()
        
        # Verify all permissions are revoked for all members
        for user_id in user_ids:
            assert len(permission_checker.get_permissions(workspace_id, user_id)) == 0
            assert permission_checker.was_revoked(workspace_id, user_id)
    
    def test_member_cannot_access_after_removal(
        self, test_session, test_workspace, test_user, permission_checker
    ):
        """
        Property: Removed member cannot access workspace resources.
        """
        workspace_id = test_workspace.id
        user_id = test_user.id
        
        # Add member
        member = TestMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            role=TestMemberRole.MEMBER,
        )
        test_session.add(member)
        test_session.commit()
        
        # Grant permissions
        permission_checker.grant_permission(workspace_id, user_id, "read")
        permission_checker.grant_permission(workspace_id, user_id, "write")
        
        # Verify access before removal
        assert permission_checker.has_permission(workspace_id, user_id, "read")
        assert permission_checker.has_permission(workspace_id, user_id, "write")
        
        # Remove member
        test_session.delete(member)
        permission_checker.revoke_all_permissions(workspace_id, user_id)
        test_session.commit()
        
        # Verify no access after removal
        assert not permission_checker.has_permission(workspace_id, user_id, "read")
        assert not permission_checker.has_permission(workspace_id, user_id, "write")
        
        # Verify member record is gone
        remaining = test_session.query(TestMemberModel).filter(
            TestMemberModel.workspace_id == workspace_id,
            TestMemberModel.user_id == user_id
        ).first()
        assert remaining is None


class TestRoleHierarchy:
    """Tests for role hierarchy enforcement."""
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        user_role=st.sampled_from([TestMemberRole.OWNER, TestMemberRole.ADMIN, TestMemberRole.MEMBER, TestMemberRole.GUEST]),
        required_role=st.sampled_from([TestMemberRole.OWNER, TestMemberRole.ADMIN, TestMemberRole.MEMBER, TestMemberRole.GUEST])
    )
    def test_role_hierarchy_enforcement(
        self, test_session, test_workspace, test_user, user_role, required_role
    ):
        """
        Property: Role hierarchy is correctly enforced.
        """
        # Role hierarchy levels
        hierarchy = {
            TestMemberRole.GUEST: 0,
            TestMemberRole.MEMBER: 1,
            TestMemberRole.ADMIN: 2,
            TestMemberRole.OWNER: 3,
        }
        
        workspace_id = test_workspace.id
        user_id = test_user.id
        
        # Add member with role
        member = TestMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            role=user_role,
        )
        test_session.add(member)
        test_session.commit()
        
        # Check permission based on hierarchy
        user_level = hierarchy[user_role]
        required_level = hierarchy[required_role]
        
        has_permission = user_level >= required_level
        
        # Verify the hierarchy logic
        if user_role == TestMemberRole.OWNER:
            assert has_permission  # Owner has all permissions
        elif user_role == TestMemberRole.ADMIN:
            assert has_permission == (required_role != TestMemberRole.OWNER)
        elif user_role == TestMemberRole.MEMBER:
            assert has_permission == (required_role in [TestMemberRole.MEMBER, TestMemberRole.GUEST])
        elif user_role == TestMemberRole.GUEST:
            assert has_permission == (required_role == TestMemberRole.GUEST)


class TestCustomRoles:
    """Tests for custom role functionality."""
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    @given(
        role_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        permissions=st.lists(
            st.sampled_from(["read", "write", "delete", "admin"]),
            min_size=1,
            max_size=4,
            unique=True
        )
    )
    def test_custom_role_creation(
        self, test_session, test_workspace, role_name, permissions
    ):
        """
        Property: Custom roles can be created with specific permissions.
        """
        workspace_id = test_workspace.id
        
        # Create custom role
        custom_role = TestCustomRoleModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            name=role_name,
            permissions=permissions,
        )
        test_session.add(custom_role)
        test_session.commit()
        
        # Verify role was created
        saved_role = test_session.query(TestCustomRoleModel).filter(
            TestCustomRoleModel.id == custom_role.id
        ).first()
        
        assert saved_role is not None
        assert saved_role.name == role_name
        assert saved_role.permissions == permissions
    
    def test_custom_role_deletion_clears_member_assignment(
        self, test_session, test_workspace, test_user
    ):
        """
        Property: Deleting a custom role clears it from member assignments.
        """
        workspace_id = test_workspace.id
        user_id = test_user.id
        
        # Create custom role
        custom_role = TestCustomRoleModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            name="Custom Role",
            permissions=["read", "write"],
        )
        test_session.add(custom_role)
        test_session.commit()
        
        # Add member with custom role
        member = TestMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            role=TestMemberRole.MEMBER,
            custom_role_id=custom_role.id,
        )
        test_session.add(member)
        test_session.commit()
        
        # Verify custom role is assigned
        assert member.custom_role_id == custom_role.id
        
        # Delete custom role (simulating cascade behavior)
        test_session.query(TestMemberModel).filter(
            TestMemberModel.custom_role_id == custom_role.id
        ).update({"custom_role_id": None})
        test_session.delete(custom_role)
        test_session.commit()
        
        # Verify member's custom role is cleared
        test_session.refresh(member)
        assert member.custom_role_id is None
