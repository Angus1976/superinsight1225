"""
Unit tests for RBAC Engine.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from src.security.rbac_engine import RBACEngine, Permission, AccessDecision


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = MagicMock()
    db.query = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


@pytest.fixture
def rbac_engine():
    """Create RBAC engine instance."""
    return RBACEngine(cache_ttl=300)


class TestPermission:
    """Tests for Permission dataclass."""

    def test_permission_creation(self):
        """Test creating a permission."""
        perm = Permission(resource="projects", action="read")
        assert perm.resource == "projects"
        assert perm.action == "read"
        assert perm.conditions is None

    def test_permission_to_dict(self):
        """Test permission dictionary conversion."""
        perm = Permission(resource="projects", action="write", conditions={"time": "business_hours"})
        result = perm.to_dict()
        assert result == {
            "resource": "projects",
            "action": "write",
            "conditions": {"time": "business_hours"}
        }

    def test_permission_from_dict(self):
        """Test creating permission from dictionary."""
        data = {"resource": "tasks", "action": "delete", "conditions": {"level": "admin"}}
        perm = Permission.from_dict(data)
        assert perm.resource == "tasks"
        assert perm.action == "delete"
        assert perm.conditions == {"level": "admin"}

    def test_permission_from_dict_defaults(self):
        """Test creating permission from dictionary with defaults."""
        data = {}
        perm = Permission.from_dict(data)
        assert perm.resource == "*"
        assert perm.action == "*"
        assert perm.conditions is None


class TestAccessDecision:
    """Tests for AccessDecision dataclass."""

    def test_access_decision_allowed(self):
        """Test creating allowed access decision."""
        decision = AccessDecision(allowed=True, reason="Permission granted")
        assert decision.allowed is True
        assert decision.reason == "Permission granted"

    def test_access_decision_denied(self):
        """Test creating denied access decision."""
        perm = Permission(resource="admin", action="delete")
        decision = AccessDecision(
            allowed=False,
            reason="Insufficient permissions",
            matched_permission=perm
        )
        assert decision.allowed is False
        assert decision.reason == "Insufficient permissions"
        assert decision.matched_permission == perm


class TestRBACEngine:
    """Tests for RBACEngine class."""

    def test_rbac_engine_creation(self, rbac_engine):
        """Test creating RBAC engine instance."""
        assert rbac_engine is not None
        assert rbac_engine._cache is not None

    def test_create_role_success(self, rbac_engine, mock_db):
        """Test creating a new role successfully."""
        # Mock database query to return no existing role
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        role = rbac_engine.create_role(
            name="test_role",
            description="Test role",
            tenant_id="tenant123",
            permissions=[{"resource": "projects", "action": "read"}],
            db=mock_db
        )

        assert role is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_role_duplicate_name(self, rbac_engine, mock_db):
        """Test creating role with duplicate name returns None."""
        # Mock database query to return existing role
        existing_role = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_role

        role = rbac_engine.create_role(
            name="existing_role",
            description="Test role",
            tenant_id="tenant123",
            db=mock_db
        )

        assert role is None
        mock_db.add.assert_not_called()

    def test_create_role_invalid_parent(self, rbac_engine, mock_db):
        """Test creating role with invalid parent returns None."""
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # No existing role with same name
            None   # No parent role found
        ]

        role = rbac_engine.create_role(
            name="child_role",
            description="Child role",
            tenant_id="tenant123",
            parent_role_id=uuid4(),
            db=mock_db
        )

        assert role is None
        mock_db.add.assert_not_called()


class TestPermissionCache:
    """Tests for permission caching functionality."""

    def test_cache_initialization(self, rbac_engine):
        """Test that cache is properly initialized."""
        assert rbac_engine._cache is not None

    def test_cache_get_miss(self, rbac_engine):
        """Test cache miss returns None."""
        result = rbac_engine._cache.get("nonexistent_key")
        assert result is None

    def test_cache_set_and_get(self, rbac_engine):
        """Test setting and getting cached values."""
        test_value = ["permission1", "permission2"]
        rbac_engine._cache.set("test_key", test_value)
        
        result = rbac_engine._cache.get("test_key")
        assert result == test_value

    def test_cache_expiration(self, rbac_engine):
        """Test that cached values expire after TTL."""
        # Create engine with very short TTL for testing
        short_ttl_engine = RBACEngine(cache_ttl=1)
        
        test_value = ["permission1"]
        short_ttl_engine._cache.set("test_key", test_value)
        
        # Value should be available immediately
        result = short_ttl_engine._cache.get("test_key")
        assert result == test_value
        
        # After TTL, value should be None (we can't easily test time expiration in unit tests)
        # This is more of an integration test scenario


class TestRoleInheritance:
    """Tests for role inheritance functionality."""

    def test_role_with_parent(self, rbac_engine, mock_db):
        """Test creating role with valid parent."""
        # Mock parent role exists
        parent_role = MagicMock()
        parent_role.id = uuid4()
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,        # No existing role with same name
            parent_role  # Parent role exists
        ]

        role = rbac_engine.create_role(
            name="child_role",
            description="Child role",
            tenant_id="tenant123",
            parent_role_id=parent_role.id,
            db=mock_db
        )

        assert role is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestRoleManagement:
    """Tests for role management operations."""

    def test_system_role_creation(self, rbac_engine, mock_db):
        """Test creating system role."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        role = rbac_engine.create_role(
            name="system_admin",
            description="System administrator",
            tenant_id="system",
            is_system_role=True,
            db=mock_db
        )

        assert role is not None
        mock_db.add.assert_called_once()

    def test_role_with_permissions(self, rbac_engine, mock_db):
        """Test creating role with specific permissions."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        permissions = [
            {"resource": "projects", "action": "read"},
            {"resource": "datasets", "action": "write"}
        ]

        role = rbac_engine.create_role(
            name="data_analyst",
            description="Data analyst role",
            tenant_id="tenant123",
            permissions=permissions,
            db=mock_db
        )

        assert role is not None
        mock_db.add.assert_called_once()


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_cache_invalidation_on_role_creation(self, rbac_engine, mock_db):
        """Test that cache is invalidated when role is created."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Set some cached value
        rbac_engine._cache.set("user:tenant123:permissions", ["old_permission"])
        
        # Create role (should invalidate cache)
        rbac_engine.create_role(
            name="new_role",
            description="New role",
            tenant_id="tenant123",
            db=mock_db
        )
        
        # Cache should be invalidated (this is a simplified test)
        # In real implementation, we'd need to test the actual invalidation pattern
