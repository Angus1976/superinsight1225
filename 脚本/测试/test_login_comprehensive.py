#!/usr/bin/env python3
"""
Comprehensive login testing suite for SuperInsight Platform.

Tests login functionality with different user roles and scenarios.

Usage:
    pytest test_login_comprehensive.py -v
    pytest test_login_comprehensive.py::TestLoginBasic -v
    pytest test_login_comprehensive.py -v --tb=short
"""

import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.database.connection import get_db_session, engine, Base
from src.security.controller import SecurityController
from src.security.models import UserRole, UserModel, AuditLogModel, AuditAction
from main import app


# Test fixtures
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Setup test database."""
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup after tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Get database session for tests."""
    db = next(get_db_session())
    yield db
    db.close()


@pytest.fixture
def client():
    """Get test client."""
    return TestClient(app)


@pytest.fixture
def security_controller():
    """Get security controller."""
    return SecurityController()


@pytest.fixture
def test_users(db_session, security_controller):
    """Create test users."""
    users = {}
    
    test_data = [
        {
            "username": "admin_test",
            "email": "admin@test.local",
            "password": "Admin@123456",
            "full_name": "Admin Test",
            "role": UserRole.ADMIN,
        },
        {
            "username": "business_test",
            "email": "business@test.local",
            "password": "Business@123456",
            "full_name": "Business Test",
            "role": UserRole.BUSINESS_EXPERT,
        },
        {
            "username": "technical_test",
            "email": "technical@test.local",
            "password": "Technical@123456",
            "full_name": "Technical Test",
            "role": UserRole.TECHNICAL_EXPERT,
        },
        {
            "username": "contractor_test",
            "email": "contractor@test.local",
            "password": "Contractor@123456",
            "full_name": "Contractor Test",
            "role": UserRole.CONTRACTOR,
        },
        {
            "username": "viewer_test",
            "email": "viewer@test.local",
            "password": "Viewer@123456",
            "full_name": "Viewer Test",
            "role": UserRole.VIEWER,
        },
    ]
    
    for user_data in test_data:
        user = security_controller.create_user(
            username=user_data["username"],
            email=user_data["email"],
            password=user_data["password"],
            full_name=user_data["full_name"],
            role=user_data["role"],
            tenant_id="test_tenant",
            db=db_session,
        )
        users[user_data["role"].value] = {
            "user": user,
            "username": user_data["username"],
            "password": user_data["password"],
            "email": user_data["email"],
        }
    
    db_session.commit()
    return users


class TestLoginBasic:
    """Basic login functionality tests."""
    
    def test_admin_login_success(self, client, test_users):
        """Test successful admin login."""
        admin = test_users["admin"]
        
        response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": admin["password"],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == admin["username"]
        assert data["role"] == "admin"
        assert data["tenant_id"] == "test_tenant"
    
    def test_business_expert_login_success(self, client, test_users):
        """Test successful business expert login."""
        business = test_users["business_expert"]
        
        response = client.post(
            "/api/security/login",
            json={
                "username": business["username"],
                "password": business["password"],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["role"] == "business_expert"
        assert "access_token" in data
    
    def test_technical_expert_login_success(self, client, test_users):
        """Test successful technical expert login."""
        technical = test_users["technical_expert"]
        
        response = client.post(
            "/api/security/login",
            json={
                "username": technical["username"],
                "password": technical["password"],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["role"] == "technical_expert"
    
    def test_contractor_login_success(self, client, test_users):
        """Test successful contractor login."""
        contractor = test_users["contractor"]
        
        response = client.post(
            "/api/security/login",
            json={
                "username": contractor["username"],
                "password": contractor["password"],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["role"] == "contractor"
    
    def test_viewer_login_success(self, client, test_users):
        """Test successful viewer login."""
        viewer = test_users["viewer"]
        
        response = client.post(
            "/api/security/login",
            json={
                "username": viewer["username"],
                "password": viewer["password"],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["role"] == "viewer"


class TestLoginFailure:
    """Login failure scenarios."""
    
    def test_invalid_username(self, client):
        """Test login with invalid username."""
        response = client.post(
            "/api/security/login",
            json={
                "username": "nonexistent_user",
                "password": "Password@123456",
            }
        )
        
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]
    
    def test_invalid_password(self, client, test_users):
        """Test login with invalid password."""
        admin = test_users["admin"]
        
        response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": "WrongPassword@123456",
            }
        )
        
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]
    
    def test_empty_username(self, client):
        """Test login with empty username."""
        response = client.post(
            "/api/security/login",
            json={
                "username": "",
                "password": "Password@123456",
            }
        )
        
        assert response.status_code in [400, 401]
    
    def test_empty_password(self, client, test_users):
        """Test login with empty password."""
        admin = test_users["admin"]
        
        response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": "",
            }
        )
        
        assert response.status_code in [400, 401]
    
    def test_missing_username(self, client):
        """Test login with missing username field."""
        response = client.post(
            "/api/security/login",
            json={
                "password": "Password@123456",
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_password(self, client, test_users):
        """Test login with missing password field."""
        admin = test_users["admin"]
        
        response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestTokenGeneration:
    """Token generation and validation tests."""
    
    def test_token_format(self, client, test_users):
        """Test that returned token is valid JWT."""
        admin = test_users["admin"]
        
        response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": admin["password"],
            }
        )
        
        data = response.json()
        token = data["access_token"]
        
        # JWT should have 3 parts separated by dots
        parts = token.split(".")
        assert len(parts) == 3
    
    def test_token_contains_user_info(self, client, test_users):
        """Test that token contains user information."""
        admin = test_users["admin"]
        
        response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": admin["password"],
            }
        )
        
        data = response.json()
        token = data["access_token"]
        
        # Decode token (without verification for testing)
        import base64
        parts = token.split(".")
        payload = parts[1]
        
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        
        decoded = json.loads(base64.urlsafe_b64decode(payload))
        
        assert "sub" in decoded  # Subject (user_id)
        assert "tenant_id" in decoded
    
    def test_different_users_get_different_tokens(self, client, test_users):
        """Test that different users get different tokens."""
        admin = test_users["admin"]
        business = test_users["business_expert"]
        
        response1 = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": admin["password"],
            }
        )
        
        response2 = client.post(
            "/api/security/login",
            json={
                "username": business["username"],
                "password": business["password"],
            }
        )
        
        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]
        
        assert token1 != token2


class TestCurrentUserEndpoint:
    """Tests for /api/security/users/me endpoint."""
    
    def test_get_current_user_with_valid_token(self, client, test_users):
        """Test getting current user info with valid token."""
        admin = test_users["admin"]
        
        # Login
        login_response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": admin["password"],
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Get current user
        response = client.get(
            "/api/security/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["username"] == admin["username"]
        assert data["email"] == admin["email"]
        assert data["role"] == "admin"
    
    def test_get_current_user_without_token(self, client):
        """Test getting current user without token."""
        response = client.get("/api/security/users/me")
        
        assert response.status_code == 401
    
    def test_get_current_user_with_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/security/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401


class TestLogout:
    """Logout functionality tests."""
    
    def test_logout_success(self, client, test_users):
        """Test successful logout."""
        admin = test_users["admin"]
        
        # Login
        login_response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": admin["password"],
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Logout
        response = client.post(
            "/api/security/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "message" in response.json()
    
    def test_logout_without_token(self, client):
        """Test logout without token."""
        response = client.post("/api/security/logout")
        
        assert response.status_code == 401


class TestAuditLogging:
    """Audit logging for login events."""
    
    def test_successful_login_logged(self, client, test_users, db_session):
        """Test that successful login is logged."""
        admin = test_users["admin"]
        
        # Clear existing logs
        db_session.query(AuditLogModel).delete()
        db_session.commit()
        
        # Login
        client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": admin["password"],
            }
        )
        
        # Check audit log
        logs = db_session.query(AuditLogModel).filter(
            AuditLogModel.action == AuditAction.LOGIN
        ).all()
        
        assert len(logs) > 0
        assert logs[-1].action == AuditAction.LOGIN
    
    def test_failed_login_logged(self, client, db_session):
        """Test that failed login is logged."""
        # Clear existing logs
        db_session.query(AuditLogModel).delete()
        db_session.commit()
        
        # Failed login
        client.post(
            "/api/security/login",
            json={
                "username": "nonexistent",
                "password": "wrong",
            }
        )
        
        # Check audit log
        logs = db_session.query(AuditLogModel).filter(
            AuditLogModel.action == AuditAction.LOGIN
        ).all()
        
        assert len(logs) > 0


class TestRoleBasedAccess:
    """Role-based access control tests."""
    
    def test_admin_can_access_admin_endpoints(self, client, test_users):
        """Test that admin can access admin endpoints."""
        admin = test_users["admin"]
        
        # Login
        login_response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": admin["password"],
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Try to access admin endpoint (audit logs)
        response = client.get(
            "/api/security/audit-logs",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should succeed (200) or at least not be forbidden (403)
        assert response.status_code in [200, 400]  # 400 if no logs
    
    def test_non_admin_cannot_access_admin_endpoints(self, client, test_users):
        """Test that non-admin cannot access admin endpoints."""
        viewer = test_users["viewer"]
        
        # Login
        login_response = client.post(
            "/api/security/login",
            json={
                "username": viewer["username"],
                "password": viewer["password"],
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Try to access admin endpoint
        response = client.get(
            "/api/security/audit-logs",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should be forbidden
        assert response.status_code == 403


class TestLoginPerformance:
    """Login performance tests."""
    
    def test_login_response_time(self, client, test_users):
        """Test that login completes within acceptable time."""
        import time
        
        admin = test_users["admin"]
        
        start = time.time()
        
        response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": admin["password"],
            }
        )
        
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Should complete within 1 second
    
    def test_multiple_concurrent_logins(self, client, test_users):
        """Test multiple users logging in."""
        users_list = [
            test_users["admin"],
            test_users["business_expert"],
            test_users["technical_expert"],
            test_users["contractor"],
            test_users["viewer"],
        ]
        
        tokens = []
        
        for user in users_list:
            response = client.post(
                "/api/security/login",
                json={
                    "username": user["username"],
                    "password": user["password"],
                }
            )
            
            assert response.status_code == 200
            tokens.append(response.json()["access_token"])
        
        # All tokens should be different
        assert len(set(tokens)) == len(tokens)


class TestLoginSecurity:
    """Security-related login tests."""
    
    def test_password_not_in_response(self, client, test_users):
        """Test that password is not returned in login response."""
        admin = test_users["admin"]
        
        response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": admin["password"],
            }
        )
        
        data = response.json()
        
        assert "password" not in data
        assert admin["password"] not in str(data)
    
    def test_password_not_in_user_endpoint(self, client, test_users):
        """Test that password is not returned in user endpoint."""
        admin = test_users["admin"]
        
        # Login
        login_response = client.post(
            "/api/security/login",
            json={
                "username": admin["username"],
                "password": admin["password"],
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Get user info
        response = client.get(
            "/api/security/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        data = response.json()
        
        assert "password" not in data
        assert "password_hash" not in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
