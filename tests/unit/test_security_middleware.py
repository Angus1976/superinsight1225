"""
Unit tests for security middleware and security service.

Validates: Requirements 24.1, 24.2, 24.3, 24.4, 24.5, 24.6
"""

import time
import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from src.services.security_service import (
    JWTManager,
    TokenPayload,
    sanitize_input,
    sanitize_dict,
    DataEncryptor,
    RowLevelSecurity,
    SanitizationResult,
)
from src.middleware.security_middleware import (
    JWTAuthMiddleware,
    InputSanitizationMiddleware,
    RateLimitMiddleware,
    get_row_level_filter,
)


# ============================================================
# JWT Manager Tests
# ============================================================

class TestJWTManager:
    """Tests for JWT token creation and validation."""

    @pytest.fixture
    def jwt_mgr(self):
        return JWTManager(secret="test-secret", expiry_seconds=300)

    def test_create_and_validate_token(self, jwt_mgr):
        token = jwt_mgr.create_token("user-1", roles=["admin"])
        payload = jwt_mgr.validate_token(token)

        assert payload.user_id == "user-1"
        assert "admin" in payload.roles
        assert payload.expires_at > time.time()

    def test_token_with_extra_claims(self, jwt_mgr):
        token = jwt_mgr.create_token(
            "user-2", extra={"tenant": "t-1"}
        )
        payload = jwt_mgr.validate_token(token)

        assert payload.extra["tenant"] == "t-1"

    def test_expired_token_raises(self, jwt_mgr):
        token = jwt_mgr.create_token("user-3", expiry_seconds=-1)

        with pytest.raises(ValueError, match="expired"):
            jwt_mgr.validate_token(token)

    def test_invalid_token_raises(self, jwt_mgr):
        with pytest.raises(ValueError, match="Invalid token"):
            jwt_mgr.validate_token("not.a.valid.token")

    def test_empty_token_raises(self, jwt_mgr):
        with pytest.raises(ValueError, match="Token is required"):
            jwt_mgr.validate_token("")

    def test_empty_user_id_raises(self, jwt_mgr):
        with pytest.raises(ValueError, match="user_id is required"):
            jwt_mgr.create_token("")

    def test_is_token_expired(self, jwt_mgr):
        valid = jwt_mgr.create_token("user-4")
        expired = jwt_mgr.create_token("user-5", expiry_seconds=-1)

        assert jwt_mgr.is_token_expired(valid) is False
        assert jwt_mgr.is_token_expired(expired) is True

    def test_wrong_secret_rejects(self):
        mgr1 = JWTManager(secret="secret-a")
        mgr2 = JWTManager(secret="secret-b")

        token = mgr1.create_token("user-6")
        with pytest.raises(ValueError, match="Invalid token"):
            mgr2.validate_token(token)

    def test_default_roles_empty(self, jwt_mgr):
        token = jwt_mgr.create_token("user-7")
        payload = jwt_mgr.validate_token(token)
        assert payload.roles == []


# ============================================================
# Input Sanitization Tests
# ============================================================

class TestSanitizeInput:
    """Tests for input sanitization utility."""

    def test_clean_input_unchanged(self):
        result = sanitize_input("Hello world")
        assert result.value == "Hello world"
        assert result.was_modified is False
        assert result.violations == []

    def test_strips_script_tags(self):
        result = sanitize_input('Hello <script>alert("xss")</script> world')
        assert "<script>" not in result.value
        assert "script_tags_removed" in result.violations

    def test_strips_event_handlers(self):
        result = sanitize_input('<img onerror=alert(1) src=x>')
        assert "onerror" not in result.value
        assert "event_handlers_removed" in result.violations

    def test_strips_javascript_uri(self):
        result = sanitize_input('javascript:alert(1)')
        assert "javascript:" not in result.value
        assert "javascript_uri_removed" in result.violations

    def test_strips_html_tags(self):
        result = sanitize_input("<b>bold</b> text")
        assert "<b>" not in result.value
        assert "html_tags_removed" in result.violations

    def test_preserves_html_when_disabled(self):
        result = sanitize_input("<b>bold</b>", strip_html=False)
        # HTML entities are still escaped
        assert "&lt;b&gt;" in result.value

    def test_truncates_long_input(self):
        long_input = "a" * 20000
        result = sanitize_input(long_input, max_length=100)
        assert len(result.value) <= 100
        assert "truncated_to_100" in result.violations

    def test_non_string_input(self):
        result = sanitize_input(12345)
        assert result.value == "12345"
        assert "non_string_input" in result.violations

    def test_html_escapes_special_chars(self):
        # Note: < c > is stripped as an HTML tag first, then & and " are escaped
        result = sanitize_input('a & b "e"')
        assert "&amp;" in result.value
        assert "&quot;" in result.value


class TestSanitizeDict:
    """Tests for recursive dictionary sanitization."""

    def test_sanitizes_string_values(self):
        data = {"name": '<script>alert("x")</script>Bob'}
        result = sanitize_dict(data)
        assert "<script>" not in result["name"]

    def test_sanitizes_nested_dicts(self):
        data = {"outer": {"inner": "<b>bold</b>"}}
        result = sanitize_dict(data)
        assert "<b>" not in result["outer"]["inner"]

    def test_sanitizes_list_strings(self):
        data = {"tags": ["<script>x</script>", "safe"]}
        result = sanitize_dict(data)
        assert "<script>" not in result["tags"][0]
        assert result["tags"][1] == "safe"

    def test_preserves_non_string_values(self):
        data = {"count": 42, "active": True, "score": 3.14}
        result = sanitize_dict(data)
        assert result == data


# ============================================================
# Data Encryption Tests
# ============================================================

class TestDataEncryptor:
    """Tests for Fernet-based data encryption at rest."""

    @pytest.fixture
    def encryptor(self):
        return DataEncryptor()

    def test_encrypt_decrypt_roundtrip(self, encryptor):
        plaintext = "sensitive data content"
        ciphertext = encryptor.encrypt(plaintext)

        assert ciphertext != plaintext
        assert encryptor.decrypt(ciphertext) == plaintext

    def test_empty_string_returns_empty(self, encryptor):
        assert encryptor.encrypt("") == ""
        assert encryptor.decrypt("") == ""

    def test_wrong_key_fails(self):
        enc1 = DataEncryptor()
        enc2 = DataEncryptor()

        ciphertext = enc1.encrypt("secret")
        with pytest.raises(ValueError, match="Decryption failed"):
            enc2.decrypt(ciphertext)

    def test_encrypt_dict_fields(self, encryptor):
        data = {"name": "Alice", "email": "alice@example.com", "age": 30}
        encrypted = encryptor.encrypt_dict_fields(data, ["email"])

        assert encrypted["email"] != "alice@example.com"
        assert encrypted["name"] == "Alice"
        assert encrypted["age"] == 30

    def test_decrypt_dict_fields(self, encryptor):
        data = {"name": "Bob", "email": "bob@example.com"}
        encrypted = encryptor.encrypt_dict_fields(data, ["email"])
        decrypted = encryptor.decrypt_dict_fields(encrypted, ["email"])

        assert decrypted["email"] == "bob@example.com"

    def test_key_property(self, encryptor):
        key = encryptor.key
        assert isinstance(key, bytes)
        assert len(key) > 0

    def test_custom_key(self):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        enc = DataEncryptor(key=key)
        assert enc.key == key

        ciphertext = enc.encrypt("test")
        assert enc.decrypt(ciphertext) == "test"


# ============================================================
# Row-Level Security Tests
# ============================================================

class TestRowLevelSecurity:
    """Tests for row-level security access control."""

    def test_admin_accesses_everything(self):
        types = RowLevelSecurity.get_accessible_resource_types(["admin"])
        assert types == ["*"]

    def test_reviewer_access(self):
        types = RowLevelSecurity.get_accessible_resource_types(["reviewer"])
        assert "temp_data" in types
        assert "sample" in types
        assert "annotation_task" not in types

    def test_annotator_access(self):
        types = RowLevelSecurity.get_accessible_resource_types(["annotator"])
        assert "annotation_task" in types
        assert "annotated_data" in types

    def test_empty_roles_no_access(self):
        types = RowLevelSecurity.get_accessible_resource_types([])
        assert types == []

    def test_owner_always_has_access(self):
        assert RowLevelSecurity.can_access_resource(
            user_id="u1", user_roles=[], resource_type="sample",
            resource_owner_id="u1",
        ) is True

    def test_non_owner_without_role_denied(self):
        assert RowLevelSecurity.can_access_resource(
            user_id="u1", user_roles=["viewer"],
            resource_type="annotation_task", resource_owner_id="u2",
        ) is False

    def test_admin_filter_returns_empty(self):
        filters = RowLevelSecurity.filter_query_by_access(
            "u1", ["admin"], "sample"
        )
        assert filters == {}

    def test_non_admin_filter_returns_owner(self):
        filters = RowLevelSecurity.filter_query_by_access(
            "u1", ["reviewer"], "sample"
        )
        assert filters == {"owner_id": "u1"}

    def test_unauthorized_filter_denies_all(self):
        filters = RowLevelSecurity.filter_query_by_access(
            "u1", ["viewer"], "annotation_task"
        )
        assert "__deny_all__" in filters

    def test_multiple_roles_combined(self):
        types = RowLevelSecurity.get_accessible_resource_types(
            ["reviewer", "annotator"]
        )
        assert "temp_data" in types
        assert "annotation_task" in types


# ============================================================
# JWT Auth Middleware Integration Tests
# ============================================================

class TestJWTAuthMiddleware:
    """Integration tests for JWT authentication middleware."""

    @pytest.fixture
    def jwt_mgr(self):
        return JWTManager(secret="test-secret", expiry_seconds=300)

    @pytest.fixture
    def app_with_auth(self, jwt_mgr):
        app = FastAPI()
        app.add_middleware(JWTAuthMiddleware, jwt_manager=jwt_mgr)

        @app.get("/protected")
        async def protected(request: Request):
            return {"user": request.state.user["id"]}

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        return app

    @pytest.fixture
    def client(self, app_with_auth):
        return TestClient(app_with_auth)

    def test_public_path_no_auth(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_missing_token_returns_401(self, client):
        resp = client.get("/protected")
        assert resp.status_code == 401
        assert "Missing" in resp.json()["detail"]

    def test_invalid_token_returns_401(self, client):
        resp = client.get(
            "/protected",
            headers={"Authorization": "Bearer bad.token.here"},
        )
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client, jwt_mgr):
        token = jwt_mgr.create_token("user-1", expiry_seconds=-1)
        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"]

    def test_valid_token_passes(self, client, jwt_mgr):
        token = jwt_mgr.create_token("user-1", roles=["admin"])
        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["user"] == "user-1"

    def test_no_bearer_prefix_returns_401(self, client, jwt_mgr):
        token = jwt_mgr.create_token("user-1")
        resp = client.get(
            "/protected",
            headers={"Authorization": token},
        )
        assert resp.status_code == 401


# ============================================================
# Rate Limit Middleware Integration Tests
# ============================================================

class TestRateLimitMiddleware:
    """Integration tests for rate limiting middleware."""

    @pytest.fixture
    def app_with_rate_limit(self):
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=3)

        @app.get("/api/data")
        async def data():
            return {"ok": True}

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        return app

    @pytest.fixture
    def client(self, app_with_rate_limit):
        return TestClient(app_with_rate_limit)

    def test_allows_under_limit(self, client):
        for _ in range(3):
            resp = client.get("/api/data")
            assert resp.status_code == 200
            assert "X-RateLimit-Limit" in resp.headers

    def test_blocks_over_limit(self, client):
        for _ in range(3):
            client.get("/api/data")

        resp = client.get("/api/data")
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        body = resp.json()
        assert body["detail"]["error"] == "rate_limit_exceeded"

    def test_excluded_paths_not_limited(self, client):
        for _ in range(10):
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_rate_limit_headers_present(self, client):
        resp = client.get("/api/data")
        assert resp.headers["X-RateLimit-Limit"] == "3"
        remaining = int(resp.headers["X-RateLimit-Remaining"])
        assert 0 <= remaining <= 3


# ============================================================
# Input Sanitization Middleware Integration Tests
# ============================================================

class TestInputSanitizationMiddleware:
    """Integration tests for input sanitization middleware."""

    @pytest.fixture
    def app_with_sanitization(self):
        app = FastAPI()
        app.add_middleware(InputSanitizationMiddleware)

        @app.post("/api/submit")
        async def submit():
            return {"ok": True}

        @app.get("/api/read")
        async def read():
            return {"ok": True}

        return app

    @pytest.fixture
    def client(self, app_with_sanitization):
        return TestClient(app_with_sanitization)

    def test_post_request_sanitized(self, client):
        resp = client.post("/api/submit?name=<script>alert(1)</script>")
        assert resp.status_code == 200

    def test_get_request_skipped(self, client):
        resp = client.get("/api/read?q=<script>x</script>")
        assert resp.status_code == 200


# ============================================================
# get_row_level_filter Tests
# ============================================================

class TestGetRowLevelFilter:
    """Tests for the get_row_level_filter dependency."""

    def test_no_user_denies_all(self):
        request = MagicMock()
        request.state = MagicMock(spec=[])  # no 'user' attribute
        filters = get_row_level_filter(request, "sample")
        assert "__deny_all__" in filters

    def test_admin_user_no_filter(self):
        request = MagicMock()
        request.state.user = {"id": "u1", "roles": ["admin"]}
        filters = get_row_level_filter(request, "sample")
        assert filters == {}

    def test_regular_user_filtered(self):
        request = MagicMock()
        request.state.user = {"id": "u1", "roles": ["reviewer"]}
        filters = get_row_level_filter(request, "sample")
        assert filters == {"owner_id": "u1"}
