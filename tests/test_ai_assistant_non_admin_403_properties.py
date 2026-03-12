"""
Property-based tests for AI Assistant Non-Admin Access Control.

Tests validate that non-admin users receive 403 status when attempting
to access role permission endpoints using hypothesis for comprehensive coverage.

Feature: ai-assistant-config-redesign, Property 5: 非管理员访问权限接口返回 403
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from uuid import uuid4

from src.models.ai_data_source_role_permission import AIDataSourceRolePermission
from src.security.models import UserModel
from src.api.ai_assistant import router as ai_assistant_router
from src.database.connection import get_db_session
from src.api.auth import get_current_user


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Create an in-memory SQLite database session for property tests.
    
    This fixture creates the necessary tables for testing.
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create the role permission table
    AIDataSourceRolePermission.__table__.create(bind=engine, checkfirst=True)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating non-admin role names
non_admin_role_strategy = st.sampled_from([
    "business_expert",
    "annotator",
    "viewer"
])

# Strategy for generating user data
def user_data_strategy(role: str):
    """Generate user data for a given role."""
    return st.builds(
        dict,
        user_id=st.uuids().map(str),
        username=st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
            min_size=3,
            max_size=20
        ).filter(lambda s: s and s[0].isalpha()),
        email=st.emails(),
        full_name=st.text(min_size=3, max_size=50),
        tenant_id=st.text(min_size=3, max_size=20),
        role=st.just(role)
    )


# Strategy for generating permission data for POST requests
permission_item_strategy = st.builds(
    dict,
    role=st.sampled_from(["admin", "business_expert", "annotator", "viewer"]),
    source_id=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="_-"
        ),
        min_size=3,
        max_size=50
    ).filter(lambda s: s and not s.startswith("-") and not s.startswith("_")),
    allowed=st.booleans()
)


def permissions_list_strategy(min_size=1, max_size=10):
    """Generate a list of permission items for POST request."""
    return st.lists(
        permission_item_strategy,
        min_size=min_size,
        max_size=max_size
    )


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_app(db_session: Session, current_user_data: dict) -> FastAPI:
    """
    Create a FastAPI test app with dependency overrides.
    
    Args:
        db_session: Database session to use
        current_user_data: User data dict with keys: user_id, username, email, 
                          full_name, tenant_id, role
    
    Returns:
        FastAPI app instance configured for testing
    """
    app = FastAPI()
    # Use the correct router path - no prefix needed as router already has it
    app.include_router(ai_assistant_router)
    
    # Override database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Override authentication dependency
    async def override_get_current_user():
        # Create a mock user object with the required attributes
        class MockUser:
            def __init__(self, data):
                self.id = data["user_id"]
                self.username = data["username"]
                self.email = data["email"]
                self.full_name = data["full_name"]
                self.tenant_id = data["tenant_id"]
                self.role = data["role"]
                self.is_active = True
        
        return MockUser(current_user_data)
    
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    return app


# ============================================================================
# Property 5: Non-Admin Access to Permission Endpoints Returns 403
# ============================================================================

class TestProperty5_NonAdminAccess403:
    """
    Feature: ai-assistant-config-redesign, Property 5: 非管理员访问权限接口返回 403
    
    **Validates: Requirements 6.4**
    
    For any non-admin role user (business_expert, annotator, viewer),
    calling GET/POST /data-sources/role-permissions endpoints should
    return HTTP 403 status code.
    """
    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=non_admin_role_strategy,
        user_data=st.data()
    )
    def test_non_admin_get_permissions_returns_403(
        self,
        db_session: Session,
        role: str,
        user_data
    ):
        """
        Property: Non-admin users receive 403 when calling GET /role-permissions.
        
        For any non-admin role (business_expert, annotator, viewer),
        attempting to retrieve role permissions should be denied with 403.
        """
        # Generate user data for the given role
        user_info = user_data.draw(user_data_strategy(role))
        
        # Create test app with non-admin user
        app = create_test_app(db_session, user_info)
        client = TestClient(app)
        
        # Act - Attempt to GET role permissions
        response = client.get("/api/v1/ai-assistant/data-sources/role-permissions")
        
        # Assert - Should receive 403 Forbidden
        assert response.status_code == 403, (
            f"Expected 403 for role '{role}', but got {response.status_code}. "
            f"User: {user_info['username']}, Response: {response.json()}"
        )
        
        # Verify error detail mentions admin access
        response_data = response.json()
        assert "detail" in response_data, "Response should contain error detail"
        assert "admin" in response_data["detail"].lower(), (
            f"Error message should mention admin requirement, got: {response_data['detail']}"
        )
    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=non_admin_role_strategy,
        user_data=st.data(),
        permissions=permissions_list_strategy(min_size=1, max_size=10)
    )
    def test_non_admin_post_permissions_returns_403(
        self,
        db_session: Session,
        role: str,
        user_data,
        permissions: list[dict]
    ):
        """
        Property: Non-admin users receive 403 when calling POST /role-permissions.
        
        For any non-admin role and any permission data payload,
        attempting to update role permissions should be denied with 403.
        """
        # Generate user data for the given role
        user_info = user_data.draw(user_data_strategy(role))
        
        # Create test app with non-admin user
        app = create_test_app(db_session, user_info)
        client = TestClient(app)
        
        # Prepare request payload
        payload = {"permissions": permissions}
        
        # Act - Attempt to POST role permissions
        response = client.post(
            "/api/v1/ai-assistant/data-sources/role-permissions",
            json=payload
        )
        
        # Assert - Should receive 403 Forbidden
        assert response.status_code == 403, (
            f"Expected 403 for role '{role}', but got {response.status_code}. "
            f"User: {user_info['username']}, Payload size: {len(permissions)}, "
            f"Response: {response.json()}"
        )
        
        # Verify error detail mentions admin access
        response_data = response.json()
        assert "detail" in response_data, "Response should contain error detail"
        assert "admin" in response_data["detail"].lower(), (
            f"Error message should mention admin requirement, got: {response_data['detail']}"
        )
    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=non_admin_role_strategy,
        user_data=st.data()
    )
    def test_non_admin_cannot_read_any_permissions(
        self,
        db_session: Session,
        role: str,
        user_data
    ):
        """
        Property: Non-admin users cannot read permissions even if data exists.
        
        Even when permission data exists in the database, non-admin users
        should still receive 403 when attempting to read it.
        """
        # Generate user data for the given role
        user_info = user_data.draw(user_data_strategy(role))
        
        # Arrange - Add some permission data to the database
        # Clear any existing data first
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        test_permission = AIDataSourceRolePermission(
            role="admin",
            source_id="test_source",
            allowed=True
        )
        db_session.add(test_permission)
        db_session.commit()
        
        # Create test app with non-admin user
        app = create_test_app(db_session, user_info)
        client = TestClient(app)
        
        # Act - Attempt to GET role permissions
        response = client.get("/api/v1/ai-assistant/data-sources/role-permissions")
        
        # Assert - Should still receive 403 (not 200 with data)
        assert response.status_code == 403, (
            f"Expected 403 for role '{role}' even with existing data, "
            f"but got {response.status_code}. User: {user_info['username']}"
        )
    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=non_admin_role_strategy,
        user_data=st.data(),
        permissions=permissions_list_strategy(min_size=1, max_size=5)
    )
    def test_non_admin_cannot_modify_any_permissions(
        self,
        db_session: Session,
        role: str,
        user_data,
        permissions: list[dict]
    ):
        """
        Property: Non-admin users cannot modify permissions regardless of payload.
        
        Non-admin users should be denied permission updates even with
        valid permission data payloads.
        """
        # Generate user data for the given role
        user_info = user_data.draw(user_data_strategy(role))
        
        # Arrange - Add existing permission data
        # Clear any existing data first
        db_session.query(AIDataSourceRolePermission).delete()
        db_session.commit()
        
        existing_permission = AIDataSourceRolePermission(
            role="viewer",
            source_id="existing_source",
            allowed=False
        )
        db_session.add(existing_permission)
        db_session.commit()
        
        # Create test app with non-admin user
        app = create_test_app(db_session, user_info)
        client = TestClient(app)
        
        # Prepare request payload
        payload = {"permissions": permissions}
        
        # Act - Attempt to POST role permissions
        response = client.post(
            "/api/v1/ai-assistant/data-sources/role-permissions",
            json=payload
        )
        
        # Assert - Should receive 403 (not 200 with success)
        assert response.status_code == 403, (
            f"Expected 403 for role '{role}' when modifying permissions, "
            f"but got {response.status_code}. User: {user_info['username']}"
        )
        
        # Verify database was not modified
        db_session.expire_all()
        all_permissions = db_session.query(AIDataSourceRolePermission).all()
        
        # Should only have the original permission, not the new ones
        assert len(all_permissions) == 1, (
            f"Database should not be modified by non-admin user, "
            f"but found {len(all_permissions)} permissions"
        )
        assert all_permissions[0].source_id == "existing_source", (
            "Original permission should remain unchanged"
        )
    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role1=non_admin_role_strategy,
        role2=non_admin_role_strategy,
        user_data=st.data()
    )
    def test_all_non_admin_roles_consistently_denied(
        self,
        db_session: Session,
        role1: str,
        role2: str,
        user_data
    ):
        """
        Property: All non-admin roles are consistently denied access.
        
        The 403 behavior should be consistent across all non-admin roles
        (business_expert, annotator, viewer) - no role should have special access.
        """
        # Test both roles
        for role in [role1, role2]:
            # Generate user data for the role
            user_info = user_data.draw(user_data_strategy(role))
            
            # Create test app with non-admin user
            app = create_test_app(db_session, user_info)
            client = TestClient(app)
            
            # Test GET endpoint
            get_response = client.get("/api/v1/ai-assistant/data-sources/role-permissions")
            assert get_response.status_code == 403, (
                f"GET should return 403 for role '{role}', got {get_response.status_code}"
            )
            
            # Test POST endpoint
            post_response = client.post(
                "/api/v1/ai-assistant/data-sources/role-permissions",
                json={"permissions": [{"role": "admin", "source_id": "test", "allowed": True}]}
            )
            assert post_response.status_code == 403, (
                f"POST should return 403 for role '{role}', got {post_response.status_code}"
            )
    
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        role=non_admin_role_strategy,
        user_data=st.data()
    )
    def test_403_response_structure(
        self,
        db_session: Session,
        role: str,
        user_data
    ):
        """
        Property: 403 responses have proper structure and error message.
        
        The 403 response should be a valid JSON with a "detail" field
        containing a meaningful error message about admin access requirement.
        """
        # Generate user data for the given role
        user_info = user_data.draw(user_data_strategy(role))
        
        # Create test app with non-admin user
        app = create_test_app(db_session, user_info)
        client = TestClient(app)
        
        # Test GET endpoint
        get_response = client.get("/api/v1/ai-assistant/data-sources/role-permissions")
        
        # Assert - Response should be valid JSON
        assert get_response.status_code == 403
        response_data = get_response.json()
        
        # Verify response structure
        assert isinstance(response_data, dict), "Response should be a JSON object"
        assert "detail" in response_data, "Response should contain 'detail' field"
        assert isinstance(response_data["detail"], str), "Detail should be a string"
        assert len(response_data["detail"]) > 0, "Detail should not be empty"
        
        # Verify error message is meaningful
        detail_lower = response_data["detail"].lower()
        assert any(keyword in detail_lower for keyword in ["admin", "permission", "access", "forbidden"]), (
            f"Error message should mention access control, got: {response_data['detail']}"
        )
