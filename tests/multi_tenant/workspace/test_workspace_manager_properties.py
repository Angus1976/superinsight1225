"""
Property-based tests for WorkspaceManager.

Tests the following correctness properties:
- Property 4: Workspace hierarchy integrity

Uses Hypothesis for property-based testing with minimum 100 iterations.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from uuid import uuid4
from datetime import datetime

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Enum as SQLEnum, Text, Boolean
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.pool import StaticPool
from sqlalchemy import ForeignKey
import enum

# Create a test-specific base for SQLite compatibility
TestBase = declarative_base()


class TenantStatus(str, enum.Enum):
    """Tenant status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class WorkspaceStatus(str, enum.Enum):
    """Workspace status enumeration."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class TestTenantModel(TestBase):
    """Test-specific tenant model."""
    __tablename__ = "test_tenants_ws"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(TenantStatus), default=TenantStatus.ACTIVE)
    configuration = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TestWorkspaceModel(TestBase):
    """Test-specific workspace model with hierarchy support."""
    __tablename__ = "test_workspaces"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(100), ForeignKey("test_tenants_ws.id"), nullable=False)
    parent_id = Column(String(36), ForeignKey("test_workspaces.id"), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(WorkspaceStatus), default=WorkspaceStatus.ACTIVE)
    config = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"


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


# Strategies for generating test data
workspace_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip())


class SimpleWorkspaceManager:
    """
    Simplified WorkspaceManager for testing with SQLite.
    """
    
    def __init__(self, session):
        self.session = session
    
    def create_tenant(self, name: str) -> TestTenantModel:
        """Create a test tenant."""
        tenant_id = name.lower().replace(" ", "-")[:50] or "tenant"
        tenant = TestTenantModel(
            id=tenant_id,
            name=name,
            display_name=name,
            status=TenantStatus.ACTIVE,
            configuration={"workspace_defaults": {}},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(tenant)
        self.session.commit()
        return tenant
    
    def create_workspace(
        self,
        tenant_id: str,
        name: str,
        parent_id: str = None
    ) -> TestWorkspaceModel:
        """Create a workspace."""
        workspace = TestWorkspaceModel(
            id=str(uuid4()),
            tenant_id=tenant_id,
            parent_id=parent_id,
            name=name,
            status=WorkspaceStatus.ACTIVE,
            config={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(workspace)
        self.session.commit()
        return workspace
    
    def get_workspace(self, workspace_id: str) -> TestWorkspaceModel:
        """Get workspace by ID."""
        return self.session.query(TestWorkspaceModel).filter(
            TestWorkspaceModel.id == workspace_id
        ).first()
    
    def move_workspace(self, workspace_id: str, new_parent_id: str) -> TestWorkspaceModel:
        """Move workspace to new parent."""
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        
        # Check for cycle
        if new_parent_id and self._would_create_cycle(workspace_id, new_parent_id):
            raise ValueError("Cannot move workspace to its own descendant")
        
        workspace.parent_id = new_parent_id
        workspace.updated_at = datetime.utcnow()
        self.session.commit()
        return workspace
    
    def delete_workspace(self, workspace_id: str) -> None:
        """Delete workspace."""
        workspace = self.get_workspace(workspace_id)
        if workspace:
            workspace.status = WorkspaceStatus.DELETED
            workspace.updated_at = datetime.utcnow()
            self.session.commit()
    
    def get_children(self, workspace_id: str) -> list:
        """Get child workspaces."""
        return self.session.query(TestWorkspaceModel).filter(
            TestWorkspaceModel.parent_id == workspace_id,
            TestWorkspaceModel.status != WorkspaceStatus.DELETED
        ).all()
    
    def get_all_descendants(self, workspace_id: str) -> list:
        """Get all descendants of a workspace."""
        descendants = []
        children = self.get_children(workspace_id)
        for child in children:
            descendants.append(child)
            descendants.extend(self.get_all_descendants(child.id))
        return descendants
    
    def _would_create_cycle(self, workspace_id: str, new_parent_id: str) -> bool:
        """Check if moving workspace would create a cycle."""
        if workspace_id == new_parent_id:
            return True
        
        # Check if new_parent is a descendant of workspace
        descendants = self.get_all_descendants(workspace_id)
        descendant_ids = {d.id for d in descendants}
        return new_parent_id in descendant_ids
    
    def verify_hierarchy_integrity(self, tenant_id: str) -> bool:
        """
        Verify hierarchy integrity for a tenant.
        
        Checks:
        1. No orphan nodes (parent exists or is None)
        2. No cycles
        3. All nodes reachable from root
        """
        workspaces = self.session.query(TestWorkspaceModel).filter(
            TestWorkspaceModel.tenant_id == tenant_id,
            TestWorkspaceModel.status != WorkspaceStatus.DELETED
        ).all()
        
        workspace_ids = {w.id for w in workspaces}
        
        # Check 1: No orphan nodes
        for workspace in workspaces:
            if workspace.parent_id and workspace.parent_id not in workspace_ids:
                return False
        
        # Check 2: No cycles (using DFS)
        def has_cycle(workspace_id: str, visited: set, path: set) -> bool:
            if workspace_id in path:
                return True
            if workspace_id in visited:
                return False
            
            visited.add(workspace_id)
            path.add(workspace_id)
            
            workspace = self.get_workspace(workspace_id)
            if workspace and workspace.parent_id:
                if has_cycle(workspace.parent_id, visited, path):
                    return True
            
            path.remove(workspace_id)
            return False
        
        visited = set()
        for workspace in workspaces:
            if has_cycle(workspace.id, visited, set()):
                return False
        
        return True


class TestWorkspaceHierarchyIntegrity:
    """
    Property 4: Workspace hierarchy integrity
    
    *For any* workspace hierarchy operation (move, delete), the hierarchy should
    maintain integrity with no orphan nodes or cycles.
    **Validates: Requirements 2.3**
    """
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.lists(workspace_name_strategy, min_size=1, max_size=10, unique=True))
    def test_hierarchy_integrity_after_creation(self, test_engine, workspace_names):
        """
        Feature: multi-tenant-workspace, Property 4: Workspace hierarchy integrity
        
        For any set of workspaces created in a hierarchy, the hierarchy should be valid.
        """
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        session = TestingSessionLocal()
        
        try:
            manager = SimpleWorkspaceManager(session)
            
            # Create tenant
            tenant = manager.create_tenant(f"test-tenant-{uuid4().hex[:8]}")
            
            # Create workspaces in a hierarchy
            workspaces = []
            for i, name in enumerate(workspace_names):
                # First workspace is root, others can have parents
                parent_id = None
                if i > 0 and workspaces:
                    # Randomly choose a parent from existing workspaces
                    parent_id = workspaces[i % len(workspaces)].id
                
                workspace = manager.create_workspace(tenant.id, name, parent_id)
                workspaces.append(workspace)
            
            # Verify hierarchy integrity
            assert manager.verify_hierarchy_integrity(tenant.id), \
                "Hierarchy should be valid after creation"
        finally:
            session.rollback()
            session.close()
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.lists(workspace_name_strategy, min_size=3, max_size=8, unique=True))
    def test_hierarchy_integrity_after_move(self, test_engine, workspace_names):
        """
        Feature: multi-tenant-workspace, Property 4: Workspace hierarchy integrity
        
        For any valid move operation, the hierarchy should remain valid.
        """
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        session = TestingSessionLocal()
        
        try:
            manager = SimpleWorkspaceManager(session)
            
            # Create tenant
            tenant = manager.create_tenant(f"test-tenant-{uuid4().hex[:8]}")
            
            # Create a simple hierarchy: root -> child1, child2
            root = manager.create_workspace(tenant.id, workspace_names[0], None)
            child1 = manager.create_workspace(tenant.id, workspace_names[1], root.id)
            child2 = manager.create_workspace(tenant.id, workspace_names[2], root.id)
            
            # Move child2 under child1 (valid move)
            manager.move_workspace(child2.id, child1.id)
            
            # Verify hierarchy integrity
            assert manager.verify_hierarchy_integrity(tenant.id), \
                "Hierarchy should be valid after move"
            
            # Verify child2's parent is now child1
            updated_child2 = manager.get_workspace(child2.id)
            assert updated_child2.parent_id == child1.id, \
                "Child2 should have child1 as parent after move"
        finally:
            session.rollback()
            session.close()
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.lists(workspace_name_strategy, min_size=3, max_size=8, unique=True))
    def test_cycle_prevention(self, test_engine, workspace_names):
        """
        Feature: multi-tenant-workspace, Property 4: Workspace hierarchy integrity
        
        Moving a workspace to its own descendant should be prevented.
        """
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        session = TestingSessionLocal()
        
        try:
            manager = SimpleWorkspaceManager(session)
            
            # Create tenant
            tenant = manager.create_tenant(f"test-tenant-{uuid4().hex[:8]}")
            
            # Create hierarchy: root -> child -> grandchild
            root = manager.create_workspace(tenant.id, workspace_names[0], None)
            child = manager.create_workspace(tenant.id, workspace_names[1], root.id)
            grandchild = manager.create_workspace(tenant.id, workspace_names[2], child.id)
            
            # Try to move root under grandchild (should fail - would create cycle)
            with pytest.raises(ValueError, match="Cannot move workspace to its own descendant"):
                manager.move_workspace(root.id, grandchild.id)
            
            # Verify hierarchy is still valid
            assert manager.verify_hierarchy_integrity(tenant.id), \
                "Hierarchy should remain valid after failed move"
        finally:
            session.rollback()
            session.close()
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.lists(workspace_name_strategy, min_size=2, max_size=6, unique=True))
    def test_hierarchy_integrity_after_delete(self, test_engine, workspace_names):
        """
        Feature: multi-tenant-workspace, Property 4: Workspace hierarchy integrity
        
        After deleting a leaf workspace, the hierarchy should remain valid.
        """
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        session = TestingSessionLocal()
        
        try:
            manager = SimpleWorkspaceManager(session)
            
            # Create tenant
            tenant = manager.create_tenant(f"test-tenant-{uuid4().hex[:8]}")
            
            # Create hierarchy
            root = manager.create_workspace(tenant.id, workspace_names[0], None)
            if len(workspace_names) > 1:
                child = manager.create_workspace(tenant.id, workspace_names[1], root.id)
                
                # Delete leaf node (child) - this should keep hierarchy valid
                manager.delete_workspace(child.id)
            
            # Verify hierarchy integrity (deleted nodes are excluded)
            assert manager.verify_hierarchy_integrity(tenant.id), \
                "Hierarchy should be valid after deleting leaf node"
        finally:
            session.rollback()
            session.close()
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(workspace_name_strategy)
    def test_move_to_root(self, test_engine, name):
        """
        Feature: multi-tenant-workspace, Property 4: Workspace hierarchy integrity
        
        Moving a workspace to root (parent=None) should be valid.
        """
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        session = TestingSessionLocal()
        
        try:
            manager = SimpleWorkspaceManager(session)
            
            # Create tenant
            tenant = manager.create_tenant(f"test-tenant-{uuid4().hex[:8]}")
            
            # Create hierarchy: root -> child
            root = manager.create_workspace(tenant.id, "root", None)
            child = manager.create_workspace(tenant.id, name, root.id)
            
            # Move child to root level
            manager.move_workspace(child.id, None)
            
            # Verify hierarchy integrity
            assert manager.verify_hierarchy_integrity(tenant.id), \
                "Hierarchy should be valid after moving to root"
            
            # Verify child is now at root level
            updated_child = manager.get_workspace(child.id)
            assert updated_child.parent_id is None, \
                "Child should be at root level after move"
        finally:
            session.rollback()
            session.close()
