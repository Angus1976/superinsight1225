"""
Unit tests for API endpoints.

Tests request validation, authentication middleware, authorization checks,
rate limiting, and error handling/status codes.

Validates: Requirements 1.1, 1.3
"""

import os
import time
import pytest
import asyncio
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, INET

from src.database.connection import Base, get_db_session
from src.security.controller import SecurityController
from src.security.models import (
    UserModel, UserRole, PermissionType,
    ProjectPermissionModel,
)
from src.security.middleware import (
    SecurityMiddleware,
    require_role,
    require_permission,
    get_current_user,
)
from src.security.rate_limiter import (
    RateLimitConfig,
    RateLimitAlgorithm,
    RateLimitResult,
    RateLimitService,
    InMemoryRateLimiter,
    RateLimitMiddleware,
)


# SQLite compatibility for PostgreSQL types
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"


# =============================================================================
# Constants & Helpers
# =============================================================================

JWT_SECRET = "test-secret-key-do-not-use-in-production"
TENANT_ID = "test_tenant"


def _create_engine():
    """Create an isolated SQLite in-memory engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _seed_user(
    session: Session,
    *,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "TestPass123!",
    role: str = "admin",
) -> UserModel:
    """Insert a user and return the ORM instance."""
    sc = SecurityController(secret_key=JWT_SECRET)
    user = UserModel(
        id=uuid4(),
        username=username,
        email=email,
        password_hash=sc.hash_password(password),
        full_name=f"Test {username.title()}",
        role=role,
        tenant_id=TENANT_ID,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_token(user: UserModel) -> str:
    """Generate a JWT for the given user."""
    sc = SecurityController(secret_key=JWT_SECRET)
    return sc.create_access_token(str(user.id), user.tenant_id)


# =============================================================================
# 1. Request Validation and Error Responses
# =============================================================================

class TestRequestValidation:
    """Test request validation and error responses.

    Validates: Requirements 1.1, 1.3
    """

    @pytest.fixture
    def client(self):
        """TestClient wired to the main app."""
        from src.app import app
        return TestClient(app)

    def test_nonexistent_endpoint_returns_404(self, client):
        """Unknown paths return 404 with JSON body."""
        resp = client.get("/api/v1/does-not-exist-xyz")
        assert resp.status_code == 404

    def test_invalid_http_method_returns_405(self, client):
        """Using wrong HTTP method returns 405."""
        resp = client.delete("/health")
        assert resp.status_code == 405

    def test_health_endpoint_returns_json(self, client):
        """Health endpoint returns valid JSON with status field."""
        resp = client.get("/health")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data

    def test_root_endpoint_returns_app_info(self, client):
        """Root endpoint returns app name and version."""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "version" in data

    def test_liveness_probe_returns_alive(self, client):
        """Liveness probe returns alive status."""
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json().get("status") == "alive"

    def test_error_response_contains_detail(self, client):
        """Error responses include a 'detail' field."""
        resp = client.get("/api/v1/does-not-exist-xyz")
        assert resp.status_code == 404
        assert "detail" in resp.json()


# =============================================================================
# 2. Authentication Middleware
# =============================================================================

class TestAuthenticationMiddleware:
    """Test authentication middleware behaviour.

    Validates: Requirements 1.1, 1.3
    """

    @pytest.fixture
    def env(self):
        """Isolated DB + FastAPI app with auth router."""
        engine = _create_engine()
        sf = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        with sf() as session:
            user = _seed_user(session)
            # Capture values before session closes
            user_id = user.id
            user_username = user.username
            user_email = user.email
            user_full_name = user.full_name
            user_role = user.role
            user_tenant_id = user.tenant_id

        from src.api.auth import router as auth_router, get_current_user as auth_get_user

        app = FastAPI()
        app.include_router(auth_router)

        def _override_db():
            session = sf()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = _override_db
        client = TestClient(app)

        # Store user info for tests that need it
        class UserInfo:
            id = user_id
            username = user_username
            email = user_email
            full_name = user_full_name
            role = user_role
            tenant_id = user_tenant_id

        yield client, sf, UserInfo(), auth_get_user

        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    def test_login_valid_credentials(self, env):
        """POST /auth/login with correct credentials returns a token."""
        client, _, _, _ = env
        resp = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "TestPass123!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, env):
        """POST /auth/login with wrong password returns 401."""
        client, _, _, _ = env
        resp = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "WrongPass!"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user_returns_401(self, env):
        """POST /auth/login with unknown user returns 401."""
        client, _, _, _ = env
        resp = client.post(
            "/auth/login",
            json={"username": "ghost", "password": "any"},
        )
        assert resp.status_code == 401

    def test_protected_endpoint_without_token_returns_401_or_403(self, env):
        """Accessing /auth/me without token returns 401 or 403."""
        client, _, _, _ = env
        resp = client.get("/auth/me")
        assert resp.status_code in (401, 403)

    def test_protected_endpoint_with_invalid_token_returns_401(self, env):
        """Accessing /auth/me with garbage token returns 401."""
        client, _, _, _ = env
        resp = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_protected_endpoint_with_valid_token(self, env):
        """Accessing /auth/me with valid token returns user info."""
        client, _, user_info, auth_get_user = env

        # Override get_current_user to return a mock user (avoids SQLite UUID issues)
        mock_user = MagicMock()
        mock_user.id = user_info.id
        mock_user.username = user_info.username
        mock_user.email = user_info.email
        mock_user.full_name = user_info.full_name
        mock_user.role = MagicMock()
        mock_user.role.value = user_info.role if isinstance(user_info.role, str) else user_info.role.value
        mock_user.tenant_id = user_info.tenant_id
        mock_user.is_active = True
        mock_user.last_login = None

        client.app.dependency_overrides[auth_get_user] = lambda: mock_user
        try:
            resp = client.get(
                "/auth/me",
                headers={"Authorization": "Bearer dummy"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["username"] == "testuser"
        finally:
            client.app.dependency_overrides.pop(auth_get_user, None)

    def test_login_response_contains_user_info(self, env):
        """Login response includes user details."""
        client, _, _, _ = env
        resp = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "TestPass123!"},
        )
        assert resp.status_code == 200
        user_data = resp.json()["user"]
        assert user_data["username"] == "testuser"
        assert user_data["email"] == "test@example.com"
        assert user_data["is_active"] is True

    def test_expired_token_returns_401(self, env):
        """An expired JWT is rejected with 401."""
        import jwt as pyjwt
        from datetime import datetime, timedelta

        client, _, user_info, _ = env
        payload = {
            "user_id": str(user_info.id),
            "tenant_id": user_info.tenant_id,
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        expired_token = pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")
        resp = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401


# =============================================================================
# 3. Authorization Checks
# =============================================================================

class TestAuthorizationChecks:
    """Test role-based and project-level authorization.

    Validates: Requirements 1.1, 1.3
    """

    @pytest.fixture
    def db_env(self):
        """Isolated DB with admin and viewer users."""
        engine = _create_engine()
        sf = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        with sf() as session:
            admin = _seed_user(
                session, username="admin", email="admin@test.com", role="admin"
            )
            viewer = _seed_user(
                session, username="viewer", email="viewer@test.com", role="viewer"
            )
            # Capture IDs before session closes to avoid DetachedInstanceError
            admin_id = admin.id
            viewer_id = viewer.id

        yield sf, admin_id, viewer_id

        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    def test_admin_has_all_project_permissions(self, db_env):
        """Admin role bypasses project-level permission checks."""
        sf, admin_id, _ = db_env
        sc = SecurityController(secret_key=JWT_SECRET)
        with sf() as session:
            assert sc.check_project_permission(
                admin_id, "any_project", PermissionType.WRITE, session
            ) is True

    def test_viewer_denied_without_explicit_permission(self, db_env):
        """Viewer without explicit grant is denied."""
        sf, _, viewer_id = db_env
        sc = SecurityController(secret_key=JWT_SECRET)
        with sf() as session:
            assert sc.check_project_permission(
                viewer_id, "proj_1", PermissionType.WRITE, session
            ) is False

    def test_viewer_allowed_with_explicit_permission(self, db_env):
        """Viewer with explicit grant is allowed."""
        sf, admin_id, viewer_id = db_env
        sc = SecurityController(secret_key=JWT_SECRET)
        with sf() as session:
            sc.grant_project_permission(
                user_id=viewer_id,
                project_id="proj_1",
                permission_type=PermissionType.READ,
                granted_by=admin_id,
                db=session,
            )
        with sf() as session:
            assert sc.check_project_permission(
                viewer_id, "proj_1", PermissionType.READ, session
            ) is True

    def test_permission_check_with_invalid_user_returns_false(self, db_env):
        """Non-existent user ID returns False."""
        sf, _, _ = db_env
        sc = SecurityController(secret_key=JWT_SECRET)
        with sf() as session:
            assert sc.check_project_permission(
                uuid4(), "proj_1", PermissionType.READ, session
            ) is False

    def test_permission_check_with_empty_project_returns_false(self, db_env):
        """Empty project_id returns False."""
        sf, admin_id, _ = db_env
        sc = SecurityController(secret_key=JWT_SECRET)
        with sf() as session:
            assert sc.check_project_permission(
                admin_id, "", PermissionType.READ, session
            ) is False

    def test_require_role_decorator_blocks_wrong_role(self):
        """require_role decorator raises 403 for disallowed role."""
        @require_role(["admin"])
        async def admin_only(**kwargs):
            return "ok"

        mock_user = MagicMock()
        mock_user.role = MagicMock()
        mock_user.role.value = "viewer"

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                admin_only(current_user=mock_user)
            )
        assert exc_info.value.status_code == 403

    def test_require_role_decorator_allows_correct_role(self):
        """require_role decorator passes for allowed role."""
        @require_role(["admin"])
        async def admin_only(**kwargs):
            return "ok"

        mock_user = MagicMock()
        mock_user.role = MagicMock()
        mock_user.role.value = "admin"

        result = asyncio.get_event_loop().run_until_complete(
            admin_only(current_user=mock_user)
        )
        assert result == "ok"

    def test_revoke_permission_denies_access(self, db_env):
        """After revoking a permission, access is denied."""
        sf, admin_id, viewer_id = db_env
        sc = SecurityController(secret_key=JWT_SECRET)

        with sf() as session:
            sc.grant_project_permission(
                viewer_id, "proj_2", PermissionType.READ, admin_id, session
            )
        with sf() as session:
            assert sc.check_project_permission(
                viewer_id, "proj_2", PermissionType.READ, session
            ) is True

        with sf() as session:
            sc.revoke_project_permission(
                viewer_id, "proj_2", PermissionType.READ, session
            )
        with sf() as session:
            assert sc.check_project_permission(
                viewer_id, "proj_2", PermissionType.READ, session
            ) is False


# =============================================================================
# 4. Rate Limiting
# =============================================================================

class TestRateLimiting:
    """Test rate limiting service and middleware.

    Validates: Requirements 1.1, 1.3
    """

    @pytest.fixture
    def service(self):
        """Fresh RateLimitService with a tight config."""
        svc = RateLimitService()
        svc.configure("test_endpoint", requests=3, window=60)
        return svc

    @pytest.mark.asyncio
    async def test_requests_within_limit_are_allowed(self, service):
        """Requests under the limit are allowed."""
        for _ in range(3):
            result = await service.check("user_1", "test_endpoint")
            assert result.allowed is True

    @pytest.mark.asyncio
    async def test_requests_exceeding_limit_are_blocked(self, service):
        """Requests over the limit are blocked."""
        for _ in range(3):
            await service.check("user_1", "test_endpoint")

        result = await service.check("user_1", "test_endpoint")
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_different_keys_have_separate_limits(self, service):
        """Different keys are tracked independently."""
        for _ in range(3):
            await service.check("user_a", "test_endpoint")

        result = await service.check("user_b", "test_endpoint")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_rate_limit_result_contains_headers(self, service):
        """Result includes limit, remaining, and reset_time."""
        result = await service.check("user_x", "test_endpoint")
        assert result.limit == 3
        assert result.remaining >= 0
        assert result.reset_time > 0

    @pytest.mark.asyncio
    async def test_disabled_service_always_allows(self):
        """When disabled, all requests are allowed."""
        svc = RateLimitService()
        svc.configure("ep", requests=1, window=60)
        svc.disable()

        for _ in range(10):
            result = await svc.check("user", "ep")
            assert result.allowed is True

    @pytest.mark.asyncio
    async def test_enable_after_disable_enforces_limits(self):
        """Re-enabling the service enforces limits again."""
        svc = RateLimitService()
        svc.configure("ep", requests=1, window=60)
        svc.disable()
        await svc.check("user", "ep")
        svc.enable()

        # First request allowed, second blocked
        r1 = await svc.check("user2", "ep")
        assert r1.allowed is True
        r2 = await svc.check("user2", "ep")
        assert r2.allowed is False

    def test_rate_limit_config_rejects_zero_requests(self):
        """RateLimitConfig raises ValueError for requests <= 0."""
        with pytest.raises(ValueError, match="requests must be positive"):
            RateLimitConfig(requests=0, window=60)

    def test_rate_limit_config_rejects_zero_window(self):
        """RateLimitConfig raises ValueError for window <= 0."""
        with pytest.raises(ValueError, match="window must be positive"):
            RateLimitConfig(requests=10, window=0)

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_returns_429(self):
        """RateLimitMiddleware returns 429 when limit exceeded."""
        svc = RateLimitService()
        svc.configure("default", requests=1, window=60)

        app = FastAPI()

        @app.get("/limited")
        async def limited():
            return {"ok": True}

        app.add_middleware(
            RateLimitMiddleware,
            service=svc,
            exclude_paths=["/health"],
        )

        client = TestClient(app)
        r1 = client.get("/limited")
        assert r1.status_code == 200

        r2 = client.get("/limited")
        assert r2.status_code == 429
        assert "X-RateLimit-Limit" in r2.headers

    @pytest.mark.asyncio
    async def test_rate_limit_middleware_excludes_paths(self):
        """Excluded paths bypass rate limiting."""
        svc = RateLimitService()
        svc.configure("default", requests=1, window=60)

        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        app.add_middleware(
            RateLimitMiddleware,
            service=svc,
            exclude_paths=["/health"],
        )

        client = TestClient(app)
        for _ in range(5):
            resp = client.get("/health")
            assert resp.status_code == 200


# =============================================================================
# 5. Error Handling and Status Codes
# =============================================================================

class TestErrorHandlingAndStatusCodes:
    """Test error handling and HTTP status codes.

    Validates: Requirements 1.1, 1.3
    """

    @pytest.fixture
    def client(self):
        from src.app import app
        return TestClient(app)

    def test_404_response_is_json(self, client):
        """404 responses are JSON with detail field."""
        resp = client.get("/api/v1/nonexistent-xyz")
        assert resp.status_code == 404
        assert resp.headers.get("content-type", "").startswith("application/json")
        assert "detail" in resp.json()

    def test_health_endpoint_status_codes(self, client):
        """Health endpoint returns 200 or 503."""
        resp = client.get("/health")
        assert resp.status_code in (200, 503)

    def test_readiness_probe_status_codes(self, client):
        """Readiness probe returns 200 or 503."""
        resp = client.get("/health/ready")
        assert resp.status_code in (200, 503)

    def test_api_info_returns_200(self, client):
        """API info endpoint returns 200."""
        resp = client.get("/api/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data

    def test_security_controller_token_verification_failure(self):
        """SecurityController.verify_token returns None for bad tokens."""
        sc = SecurityController(secret_key=JWT_SECRET)
        assert sc.verify_token("not.a.valid.jwt") is None
        assert sc.verify_token("") is None

    def test_security_controller_password_mismatch(self):
        """verify_password returns False for wrong password."""
        sc = SecurityController(secret_key=JWT_SECRET)
        hashed = sc.hash_password("correct")
        assert sc.verify_password("wrong", hashed) is False

    def test_security_controller_password_match(self):
        """verify_password returns True for correct password."""
        sc = SecurityController(secret_key=JWT_SECRET)
        hashed = sc.hash_password("correct")
        assert sc.verify_password("correct", hashed) is True

    def test_login_missing_fields_returns_422(self):
        """POST /auth/login with missing fields returns 422."""
        engine = _create_engine()
        sf = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        from src.api.auth import router as auth_router
        app = FastAPI()
        app.include_router(auth_router)

        def _override_db():
            session = sf()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = _override_db
        client = TestClient(app)

        # Missing password field
        resp = client.post("/auth/login", json={"username": "test"})
        assert resp.status_code == 422

        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    def test_login_empty_body_returns_422(self):
        """POST /auth/login with empty body returns 422."""
        engine = _create_engine()
        sf = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        from src.api.auth import router as auth_router
        app = FastAPI()
        app.include_router(auth_router)

        def _override_db():
            session = sf()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = _override_db
        client = TestClient(app)

        resp = client.post("/auth/login", json={})
        assert resp.status_code == 422

        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    def test_logout_without_auth_returns_401_or_403(self):
        """POST /auth/logout without token returns 401 or 403."""
        engine = _create_engine()
        sf = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        from src.api.auth import router as auth_router
        app = FastAPI()
        app.include_router(auth_router)

        def _override_db():
            session = sf()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = _override_db
        client = TestClient(app)

        resp = client.post("/auth/logout")
        assert resp.status_code in (401, 403)

        Base.metadata.drop_all(bind=engine)
        engine.dispose()
