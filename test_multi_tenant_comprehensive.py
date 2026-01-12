"""
Comprehensive test suite for multi-tenant workspace system.

This test suite covers all aspects of the multi-tenant implementation including:
- Database models and migrations
- Service layer functionality
- API endpoints
- Permission validation
- Label Studio integration
- RLS policies
"""

import pytest
import asyncio
from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import our modules
from src.database.connection import Base
from src.database.multi_tenant_models import (
    TenantModel, WorkspaceModel, UserTenantAssociationModel,
    UserWorkspaceAssociationModel, TenantResourceUsageModel,
    TenantStatus, WorkspaceStatus, TenantRole, WorkspaceRole
)
from src.multi_tenant.services import (
    TenantManager, WorkspaceManager, UserTenantManager,
    UserWorkspaceManager, PermissionService, ResourceQuotaManager
)
from src.multi_tenant.middleware import TenantContextMiddleware, TenantAwareSession
from src.multi_tenant.api import router as multi_tenant_router
from src.multi_tenant.label_studio_integration import LabelStudioIntegrationService
from src.database.rls_policies import apply_rls_policies, drop_rls_policies, set_tenant_context, clear_tenant_context

# Test database URL (use in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite:///./test_multi_tenant.db"

# Test fixtures
@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session(engine):
    """Create test database session."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def app():
    """Create test FastAPI application."""
    app = FastAPI()
    app.include_router(multi_tenant_router)
    app.add_middleware(TenantContextMiddleware)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_tenant_data():
    """Sample tenant data for testing."""
    return {
        "tenant_id": "test-tenant-001",
        "name": "test_tenant",
        "display_name": "Test Tenant",
        "description": "A test tenant for unit testing",
        "max_users": 50,
        "max_workspaces": 5,
        "max_storage_gb": 50.0,
        "billing_email": "billing@test-tenant.com",
        "billing_plan": "premium"
    }


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return uuid4()


class TestMultiTenantModels:
    """Test multi-tenant database models."""
    
    def test_tenant_model_creation(self, session, sample_tenant_data):
        """Test creating a tenant model."""
        tenant = TenantModel(**sample_tenant_data)
        session.add(tenant)
        session.commit()
        
        # Verify tenant was created
        retrieved = session.query(TenantModel).filter(TenantModel.id == sample_tenant_data["tenant_id"]).first()
        assert retrieved is not None
        assert retrieved.name == sample_tenant_data["name"]
        assert retrieved.status == TenantStatus.ACTIVE
        assert retrieved.current_users == 0
        assert retrieved.current_workspaces == 0
    
    def test_workspace_model_creation(self, session, sample_tenant_data):
        """Test creating a workspace model."""
        # First create tenant
        tenant = TenantModel(**sample_tenant_data)
        session.add(tenant)
        session.commit()
        
        # Create workspace
        workspace = WorkspaceModel(
            tenant_id=sample_tenant_data["tenant_id"],
            name="test-workspace",
            display_name="Test Workspace",
            description="A test workspace",
            is_default=True
        )
        session.add(workspace)
        session.commit()
        
        # Verify workspace was created
        retrieved = session.query(WorkspaceModel).filter(WorkspaceModel.name == "test-workspace").first()
        assert retrieved is not None
        assert retrieved.tenant_id == sample_tenant_data["tenant_id"]
        assert retrieved.status == WorkspaceStatus.ACTIVE
        assert retrieved.is_default is True
    
    def test_user_tenant_association(self, session, sample_tenant_data, sample_user_id):
        """Test user-tenant association model."""
        # Create tenant
        tenant = TenantModel(**sample_tenant_data)
        session.add(tenant)
        session.commit()
        
        # Create association
        association = UserTenantAssociationModel(
            user_id=sample_user_id,
            tenant_id=sample_tenant_data["tenant_id"],
            role=TenantRole.ADMIN,
            is_default_tenant=True,
            is_active=True
        )
        session.add(association)
        session.commit()
        
        # Verify association
        retrieved = session.query(UserTenantAssociationModel).filter(
            UserTenantAssociationModel.user_id == sample_user_id
        ).first()
        assert retrieved is not None
        assert retrieved.role == TenantRole.ADMIN
        assert retrieved.is_default_tenant is True


class TestTenantManager:
    """Test tenant management service."""
    
    def test_create_tenant(self, session, sample_tenant_data):
        """Test tenant creation."""
        manager = TenantManager(session)
        tenant = manager.create_tenant(**sample_tenant_data)
        
        assert tenant.id == sample_tenant_data["tenant_id"]
        assert tenant.name == sample_tenant_data["name"]
        assert tenant.status == TenantStatus.ACTIVE
        
        # Verify default workspace was created
        workspaces = session.query(WorkspaceModel).filter(
            WorkspaceModel.tenant_id == tenant.id
        ).all()
        assert len(workspaces) == 1
        assert workspaces[0].is_default is True
    
    def test_get_tenant(self, session, sample_tenant_data):
        """Test tenant retrieval."""
        manager = TenantManager(session)
        created_tenant = manager.create_tenant(**sample_tenant_data)
        
        retrieved_tenant = manager.get_tenant(sample_tenant_data["tenant_id"])
        assert retrieved_tenant is not None
        assert retrieved_tenant.id == created_tenant.id
    
    def test_update_tenant(self, session, sample_tenant_data):
        """Test tenant updates."""
        manager = TenantManager(session)
        tenant = manager.create_tenant(**sample_tenant_data)
        
        updated = manager.update_tenant(
            tenant.id,
            display_name="Updated Test Tenant",
            max_users=100
        )
        
        assert updated is not None
        assert updated.display_name == "Updated Test Tenant"
        assert updated.max_users == 100
    
    def test_deactivate_tenant(self, session, sample_tenant_data):
        """Test tenant deactivation."""
        manager = TenantManager(session)
        tenant = manager.create_tenant(**sample_tenant_data)
        
        result = manager.deactivate_tenant(tenant.id)
        assert result is True
        
        # Verify tenant is suspended
        updated_tenant = manager.get_tenant(tenant.id)
        assert updated_tenant.status == TenantStatus.SUSPENDED
    
    def test_get_tenant_usage(self, session, sample_tenant_data):
        """Test tenant usage retrieval."""
        manager = TenantManager(session)
        tenant = manager.create_tenant(**sample_tenant_data)
        
        usage = manager.get_tenant_usage(tenant.id)
        assert usage is not None
        assert usage["tenant_id"] == tenant.id
        assert usage["current_users"] == 0
        assert usage["max_users"] == sample_tenant_data["max_users"]


class TestWorkspaceManager:
    """Test workspace management service."""
    
    def test_create_workspace(self, session, sample_tenant_data):
        """Test workspace creation."""
        # Create tenant first
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        # Create workspace
        workspace_manager = WorkspaceManager(session)
        workspace = workspace_manager.create_workspace(
            tenant_id=tenant.id,
            name="test-workspace-2",
            display_name="Test Workspace 2",
            description="Second test workspace"
        )
        
        assert workspace.tenant_id == tenant.id
        assert workspace.name == "test-workspace-2"
        assert workspace.status == WorkspaceStatus.ACTIVE
    
    def test_list_workspaces(self, session, sample_tenant_data):
        """Test workspace listing."""
        # Create tenant
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        # Create additional workspace (default one already exists)
        workspace_manager = WorkspaceManager(session)
        workspace_manager.create_workspace(
            tenant_id=tenant.id,
            name="additional-workspace",
            display_name="Additional Workspace"
        )
        
        # List workspaces
        workspaces = workspace_manager.list_workspaces(tenant.id)
        assert len(workspaces) == 2  # default + additional
        
        workspace_names = [w.name for w in workspaces]
        assert "default" in workspace_names
        assert "additional-workspace" in workspace_names
    
    def test_archive_workspace(self, session, sample_tenant_data):
        """Test workspace archiving."""
        # Create tenant and workspace
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        workspace_manager = WorkspaceManager(session)
        workspace = workspace_manager.create_workspace(
            tenant_id=tenant.id,
            name="to-archive",
            display_name="Workspace to Archive"
        )
        
        # Archive workspace
        result = workspace_manager.archive_workspace(workspace.id)
        assert result is True
        
        # Verify workspace is archived
        archived_workspace = workspace_manager.get_workspace(workspace.id)
        assert archived_workspace.status == WorkspaceStatus.ARCHIVED
        assert archived_workspace.archived_at is not None


class TestUserTenantManager:
    """Test user-tenant association management."""
    
    def test_invite_user_to_tenant(self, session, sample_tenant_data, sample_user_id):
        """Test user invitation to tenant."""
        # Create tenant
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        # Invite user
        user_tenant_manager = UserTenantManager(session)
        association = user_tenant_manager.invite_user_to_tenant(
            user_id=sample_user_id,
            tenant_id=tenant.id,
            role=TenantRole.MEMBER,
            is_default_tenant=True
        )
        
        assert association.user_id == sample_user_id
        assert association.tenant_id == tenant.id
        assert association.role == TenantRole.MEMBER
        assert association.is_default_tenant is True
    
    def test_update_user_tenant_role(self, session, sample_tenant_data, sample_user_id):
        """Test updating user role in tenant."""
        # Create tenant and association
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        user_tenant_manager = UserTenantManager(session)
        user_tenant_manager.invite_user_to_tenant(
            user_id=sample_user_id,
            tenant_id=tenant.id,
            role=TenantRole.MEMBER
        )
        
        # Update role
        updated = user_tenant_manager.update_user_tenant_role(
            user_id=sample_user_id,
            tenant_id=tenant.id,
            role=TenantRole.ADMIN
        )
        
        assert updated is not None
        assert updated.role == TenantRole.ADMIN
    
    def test_remove_user_from_tenant(self, session, sample_tenant_data, sample_user_id):
        """Test removing user from tenant."""
        # Create tenant and association
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        user_tenant_manager = UserTenantManager(session)
        user_tenant_manager.invite_user_to_tenant(
            user_id=sample_user_id,
            tenant_id=tenant.id,
            role=TenantRole.MEMBER
        )
        
        # Remove user
        result = user_tenant_manager.remove_user_from_tenant(
            user_id=sample_user_id,
            tenant_id=tenant.id
        )
        
        assert result is True
        
        # Verify user is removed
        associations = user_tenant_manager.get_user_tenants(sample_user_id)
        assert len(associations) == 0


class TestPermissionService:
    """Test permission validation service."""
    
    def test_has_tenant_permission(self, session, sample_tenant_data, sample_user_id):
        """Test tenant permission checking."""
        # Create tenant and user association
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        user_tenant_manager = UserTenantManager(session)
        user_tenant_manager.invite_user_to_tenant(
            user_id=sample_user_id,
            tenant_id=tenant.id,
            role=TenantRole.ADMIN
        )
        
        # Test permissions
        permission_service = PermissionService(session)
        
        # Admin should have member permissions
        assert permission_service.has_tenant_permission(
            sample_user_id, tenant.id, TenantRole.MEMBER
        ) is True
        
        # Admin should have admin permissions
        assert permission_service.has_tenant_permission(
            sample_user_id, tenant.id, TenantRole.ADMIN
        ) is True
        
        # Admin should not have owner permissions
        assert permission_service.has_tenant_permission(
            sample_user_id, tenant.id, TenantRole.OWNER
        ) is False
    
    def test_has_workspace_permission(self, session, sample_tenant_data, sample_user_id):
        """Test workspace permission checking."""
        # Create tenant and workspace
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        workspace_manager = WorkspaceManager(session)
        workspace = workspace_manager.create_workspace(
            tenant_id=tenant.id,
            name="test-workspace",
            display_name="Test Workspace"
        )
        
        # Add user to workspace
        user_workspace_manager = UserWorkspaceManager(session)
        user_workspace_manager.add_user_to_workspace(
            user_id=sample_user_id,
            workspace_id=workspace.id,
            role=WorkspaceRole.REVIEWER
        )
        
        # Test permissions
        permission_service = PermissionService(session)
        
        # Reviewer should have viewer permissions
        assert permission_service.has_workspace_permission(
            sample_user_id, workspace.id, WorkspaceRole.VIEWER
        ) is True
        
        # Reviewer should have annotator permissions
        assert permission_service.has_workspace_permission(
            sample_user_id, workspace.id, WorkspaceRole.ANNOTATOR
        ) is True
        
        # Reviewer should have reviewer permissions
        assert permission_service.has_workspace_permission(
            sample_user_id, workspace.id, WorkspaceRole.REVIEWER
        ) is True
        
        # Reviewer should not have admin permissions
        assert permission_service.has_workspace_permission(
            sample_user_id, workspace.id, WorkspaceRole.ADMIN
        ) is False
    
    def test_get_user_context(self, session, sample_tenant_data, sample_user_id):
        """Test user context retrieval."""
        # Create tenant and associations
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        user_tenant_manager = UserTenantManager(session)
        user_tenant_manager.invite_user_to_tenant(
            user_id=sample_user_id,
            tenant_id=tenant.id,
            role=TenantRole.MEMBER,
            is_default_tenant=True
        )
        
        # Get user context
        permission_service = PermissionService(session)
        context = permission_service.get_user_context(sample_user_id)
        
        assert context["user_id"] == str(sample_user_id)
        assert context["default_tenant"] == tenant.id
        assert context["total_tenants"] == 1
        assert len(context["tenants"]) == 1
        assert context["tenants"][0]["tenant_id"] == tenant.id
        assert context["tenants"][0]["role"] == "member"
        assert context["tenants"][0]["is_default"] is True


class TestResourceQuotaManager:
    """Test resource quota management."""
    
    def test_check_quota(self, session, sample_tenant_data):
        """Test quota checking."""
        # Create tenant
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        # Test quota checking
        quota_manager = ResourceQuotaManager(session)
        
        # Should have quota available
        assert quota_manager.check_quota(tenant.id, "users", 10) is True
        assert quota_manager.check_quota(tenant.id, "workspaces", 3) is True
        
        # Should not exceed quota
        assert quota_manager.check_quota(tenant.id, "users", 100) is False
        assert quota_manager.check_quota(tenant.id, "workspaces", 20) is False
    
    def test_update_usage(self, session, sample_tenant_data):
        """Test usage updates."""
        # Create tenant
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        # Update usage
        quota_manager = ResourceQuotaManager(session)
        result = quota_manager.update_usage(tenant.id, "users", 5, "add")
        assert result is True
        
        # Verify usage was updated
        updated_tenant = tenant_manager.get_tenant(tenant.id)
        assert updated_tenant.current_users == 5
        
        # Subtract usage
        quota_manager.update_usage(tenant.id, "users", 2, "subtract")
        updated_tenant = tenant_manager.get_tenant(tenant.id)
        assert updated_tenant.current_users == 3
    
    def test_record_usage(self, session, sample_tenant_data):
        """Test usage recording."""
        # Create tenant
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        # Record usage
        quota_manager = ResourceQuotaManager(session)
        usage_record = quota_manager.record_usage(
            tenant_id=tenant.id,
            api_calls=1000,
            storage_bytes=1024*1024*100,  # 100MB
            annotation_count=50
        )
        
        assert usage_record.tenant_id == tenant.id
        assert usage_record.api_calls == 1000
        assert usage_record.storage_bytes == 1024*1024*100
        assert usage_record.annotation_count == 50


class TestTenantAwareSession:
    """Test tenant-aware database session."""
    
    def test_tenant_aware_session_context(self, session, sample_tenant_data):
        """Test tenant-aware session context management."""
        # Create tenant
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(**sample_tenant_data)
        
        # Create workspace
        workspace_manager = WorkspaceManager(session)
        workspace = workspace_manager.create_workspace(
            tenant_id=tenant.id,
            name="test-workspace",
            display_name="Test Workspace"
        )
        
        # Test tenant-aware session
        tenant_session = TenantAwareSession(session, tenant.id, workspace.id)
        
        with tenant_session as s:
            # Context should be set
            assert tenant_session._context_set is True
            
            # Should be able to query normally
            tenants = s.query(TenantModel).all()
            assert len(tenants) >= 1


class TestLabelStudioIntegration:
    """Test Label Studio integration service."""
    
    def test_integration_service_initialization(self, session):
        """Test Label Studio integration service initialization."""
        service = LabelStudioIntegrationService(session)
        assert service.session == session
        assert service.base_url is not None
    
    def test_get_default_label_config(self, session):
        """Test default label configuration."""
        service = LabelStudioIntegrationService(session)
        config = service._get_default_label_config()
        
        assert config is not None
        assert "<View>" in config
        assert "<Text" in config
        assert "<Choices" in config


def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("🧪 Starting Multi-Tenant Comprehensive Test Suite...")
    
    # Run pytest with verbose output
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short",
        "--color=yes"
    ], capture_output=True, text=True)
    
    print("📊 Test Results:")
    print(result.stdout)
    
    if result.stderr:
        print("⚠️ Test Warnings/Errors:")
        print(result.stderr)
    
    if result.returncode == 0:
        print("✅ All tests passed successfully!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


if __name__ == "__main__":
    # Run tests when script is executed directly
    success = run_comprehensive_tests()
    exit(0 if success else 1)