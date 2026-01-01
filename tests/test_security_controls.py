"""
Security Controls Tests.

Tests for authentication, authorization, and security protection including:
- API Key authentication
- JWT token authentication
- HMAC signature verification
- Permission control
- DDoS protection
- SQL injection detection
- XSS protection
- IP access control
"""

import time
import pytest
import jwt
import hmac
import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.sync.gateway.auth import (
    AuthMethod,
    PermissionLevel,
    ResourceType,
    Permission,
    AuthToken,
    TokenPayload,
    AuthConfig,
    SyncAuthHandler,
)
from src.sync.gateway.security import (
    ThreatLevel,
    ThreatType,
    ThreatEvent,
    IPAccessRule,
    SecurityConfig,
    SyncSecurityHandler,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def auth_config():
    """Create test auth configuration."""
    return AuthConfig(
        jwt_secret_key="test-secret-key-for-testing",
        jwt_algorithm="HS256",
        jwt_expiry_minutes=60,
        jwt_refresh_expiry_days=7,
        api_key_prefix="sk_test_"
    )


@pytest.fixture
def auth_handler(auth_config):
    """Create auth handler for testing."""
    return SyncAuthHandler(config=auth_config)


@pytest.fixture
def security_config():
    """Create test security configuration."""
    return SecurityConfig(
        ddos_protection_enabled=True,
        ddos_threshold_requests=10,  # Low threshold for testing
        ddos_block_duration=60,
        sql_injection_protection=True,
        xss_protection=True,
        path_traversal_protection=True,
        command_injection_protection=True,
        block_suspicious_agents=True
    )


@pytest.fixture
def security_handler(security_config):
    """Create security handler for testing."""
    return SyncSecurityHandler(config=security_config)


@pytest.fixture
def sample_permissions():
    """Create sample permissions."""
    return [
        Permission(
            resource_type=ResourceType.SYNC_JOB,
            level=PermissionLevel.WRITE
        ),
        Permission(
            resource_type=ResourceType.DATA_SOURCE,
            level=PermissionLevel.READ
        )
    ]


# =============================================================================
# Permission Tests
# =============================================================================

class TestPermission:
    """Tests for Permission class."""

    def test_permission_creation(self):
        """Test creating a permission."""
        perm = Permission(
            resource_type=ResourceType.SYNC_JOB,
            level=PermissionLevel.ADMIN
        )

        assert perm.resource_type == ResourceType.SYNC_JOB
        assert perm.level == PermissionLevel.ADMIN
        assert perm.resource_id is None

    def test_permission_with_resource_id(self):
        """Test permission for specific resource."""
        perm = Permission(
            resource_type=ResourceType.SYNC_JOB,
            level=PermissionLevel.WRITE,
            resource_id="job_123"
        )

        assert perm.resource_id == "job_123"


# =============================================================================
# AuthToken Tests
# =============================================================================

class TestAuthToken:
    """Tests for AuthToken class."""

    def test_auth_token_creation(self, sample_permissions):
        """Test creating an auth token."""
        token = AuthToken(
            token_id="token_001",
            user_id="user_001",
            tenant_id="tenant_001",
            auth_method=AuthMethod.JWT,
            permissions=sample_permissions,
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )

        assert token.token_id == "token_001"
        assert token.user_id == "user_001"
        assert token.tenant_id == "tenant_001"
        assert len(token.permissions) == 2

    def test_is_expired_not_expired(self, sample_permissions):
        """Test token is not expired."""
        token = AuthToken(
            token_id="token_001",
            user_id="user_001",
            tenant_id="tenant_001",
            auth_method=AuthMethod.JWT,
            permissions=sample_permissions,
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )

        assert token.is_expired is False

    def test_is_expired_expired(self, sample_permissions):
        """Test token is expired."""
        token = AuthToken(
            token_id="token_001",
            user_id="user_001",
            tenant_id="tenant_001",
            auth_method=AuthMethod.JWT,
            permissions=sample_permissions,
            issued_at=datetime.utcnow() - timedelta(hours=2),
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )

        assert token.is_expired is True

    def test_has_permission_exact_match(self, sample_permissions):
        """Test permission check with exact match."""
        token = AuthToken(
            token_id="token_001",
            user_id="user_001",
            tenant_id="tenant_001",
            auth_method=AuthMethod.JWT,
            permissions=sample_permissions,
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )

        assert token.has_permission(ResourceType.SYNC_JOB, PermissionLevel.WRITE) is True
        assert token.has_permission(ResourceType.DATA_SOURCE, PermissionLevel.READ) is True

    def test_has_permission_higher_level_grants_lower(self, sample_permissions):
        """Test that higher permission level grants lower level access."""
        token = AuthToken(
            token_id="token_001",
            user_id="user_001",
            tenant_id="tenant_001",
            auth_method=AuthMethod.JWT,
            permissions=sample_permissions,
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )

        # WRITE permission should grant READ access
        assert token.has_permission(ResourceType.SYNC_JOB, PermissionLevel.READ) is True

    def test_has_permission_insufficient_level(self, sample_permissions):
        """Test permission check with insufficient level."""
        token = AuthToken(
            token_id="token_001",
            user_id="user_001",
            tenant_id="tenant_001",
            auth_method=AuthMethod.JWT,
            permissions=sample_permissions,
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )

        # READ permission should not grant WRITE access
        assert token.has_permission(ResourceType.DATA_SOURCE, PermissionLevel.WRITE) is False

    def test_has_permission_missing_resource(self, sample_permissions):
        """Test permission check for missing resource type."""
        token = AuthToken(
            token_id="token_001",
            user_id="user_001",
            tenant_id="tenant_001",
            auth_method=AuthMethod.JWT,
            permissions=sample_permissions,
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )

        # No permission for AUDIT_LOG
        assert token.has_permission(ResourceType.AUDIT_LOG, PermissionLevel.READ) is False


# =============================================================================
# SyncAuthHandler API Key Tests
# =============================================================================

class TestSyncAuthHandlerAPIKey:
    """Tests for API Key authentication."""

    def test_generate_api_key(self, auth_handler, sample_permissions):
        """Test generating an API key."""
        api_key, key_id = auth_handler.generate_api_key(
            user_id="user_001",
            tenant_id="tenant_001",
            permissions=sample_permissions,
            name="Test Key"
        )

        assert api_key.startswith("sk_test_")
        assert key_id is not None
        assert len(api_key) > 20

    def test_validate_api_key_success(self, auth_handler, sample_permissions):
        """Test validating a valid API key."""
        api_key, _ = auth_handler.generate_api_key(
            user_id="user_001",
            tenant_id="tenant_001",
            permissions=sample_permissions
        )

        auth_token = auth_handler.validate_api_key(api_key)

        assert auth_token is not None
        assert auth_token.user_id == "user_001"
        assert auth_token.tenant_id == "tenant_001"
        assert auth_token.auth_method == AuthMethod.API_KEY

    def test_validate_api_key_invalid(self, auth_handler):
        """Test validating an invalid API key."""
        auth_token = auth_handler.validate_api_key("sk_test_invalid_key")

        assert auth_token is None

    def test_validate_api_key_wrong_prefix(self, auth_handler):
        """Test validating a key with wrong prefix."""
        auth_token = auth_handler.validate_api_key("wrong_prefix_key")

        assert auth_token is None

    def test_validate_api_key_expired(self, auth_handler, sample_permissions):
        """Test validating an expired API key."""
        api_key, _ = auth_handler.generate_api_key(
            user_id="user_001",
            tenant_id="tenant_001",
            permissions=sample_permissions,
            expires_days=0  # Expires immediately
        )

        # Manually expire the key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        auth_handler._api_keys[key_hash]["expires_at"] = datetime.utcnow() - timedelta(days=1)

        auth_token = auth_handler.validate_api_key(api_key)

        assert auth_token is None

    def test_revoke_api_key(self, auth_handler, sample_permissions):
        """Test revoking an API key."""
        api_key, key_id = auth_handler.generate_api_key(
            user_id="user_001",
            tenant_id="tenant_001",
            permissions=sample_permissions
        )

        # Key should be valid
        assert auth_handler.validate_api_key(api_key) is not None

        # Revoke the key
        result = auth_handler.revoke_api_key(key_id)
        assert result is True

        # Key should now be invalid
        assert auth_handler.validate_api_key(api_key) is None

    def test_revoke_nonexistent_key(self, auth_handler):
        """Test revoking a non-existent key."""
        result = auth_handler.revoke_api_key("nonexistent_key_id")

        assert result is False


# =============================================================================
# SyncAuthHandler JWT Tests
# =============================================================================

class TestSyncAuthHandlerJWT:
    """Tests for JWT token authentication."""

    def test_generate_jwt_token(self, auth_handler, sample_permissions):
        """Test generating JWT tokens."""
        access_token, refresh_token = auth_handler.generate_jwt_token(
            user_id="user_001",
            tenant_id="tenant_001",
            permissions=sample_permissions
        )

        assert access_token is not None
        assert refresh_token is not None
        assert len(access_token) > 50
        assert len(refresh_token) > 50

    def test_validate_jwt_token_success(self, auth_handler, sample_permissions):
        """Test validating a valid JWT token."""
        access_token, _ = auth_handler.generate_jwt_token(
            user_id="user_001",
            tenant_id="tenant_001",
            permissions=sample_permissions
        )

        auth_token = auth_handler.validate_jwt_token(access_token)

        assert auth_token is not None
        assert auth_token.user_id == "user_001"
        assert auth_token.tenant_id == "tenant_001"
        assert auth_token.auth_method == AuthMethod.JWT
        assert len(auth_token.permissions) == 2

    def test_validate_jwt_token_invalid(self, auth_handler):
        """Test validating an invalid JWT token."""
        auth_token = auth_handler.validate_jwt_token("invalid_token")

        assert auth_token is None

    def test_validate_jwt_token_expired(self, auth_handler, sample_permissions):
        """Test validating an expired JWT token."""
        # Create a token that's already expired
        now = datetime.utcnow()
        payload = {
            "sub": "user_001",
            "tenant_id": "tenant_001",
            "permissions": [],
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
            "jti": "expired_token",
            "metadata": {}
        }

        expired_token = jwt.encode(
            payload,
            auth_handler.config.jwt_secret_key,
            algorithm=auth_handler.config.jwt_algorithm
        )

        auth_token = auth_handler.validate_jwt_token(expired_token)

        assert auth_token is None

    def test_validate_jwt_token_revoked(self, auth_handler, sample_permissions):
        """Test validating a revoked JWT token."""
        access_token, _ = auth_handler.generate_jwt_token(
            user_id="user_001",
            tenant_id="tenant_001",
            permissions=sample_permissions
        )

        # Decode to get token ID
        payload = jwt.decode(
            access_token,
            auth_handler.config.jwt_secret_key,
            algorithms=[auth_handler.config.jwt_algorithm]
        )

        # Revoke the token
        auth_handler.revoke_jwt_token(payload["jti"])

        # Token should now be invalid
        auth_token = auth_handler.validate_jwt_token(access_token)

        assert auth_token is None

    def test_refresh_jwt_token_success(self, auth_handler, sample_permissions):
        """Test refreshing JWT tokens."""
        _, refresh_token = auth_handler.generate_jwt_token(
            user_id="user_001",
            tenant_id="tenant_001",
            permissions=sample_permissions
        )

        result = auth_handler.refresh_jwt_token(refresh_token)

        assert result is not None
        new_access, new_refresh = result
        assert len(new_access) > 50
        assert len(new_refresh) > 50

    def test_refresh_jwt_token_invalid(self, auth_handler):
        """Test refreshing with invalid refresh token."""
        result = auth_handler.refresh_jwt_token("invalid_refresh_token")

        assert result is None

    def test_refresh_jwt_token_wrong_type(self, auth_handler):
        """Test refreshing with access token instead of refresh token."""
        access_token, _ = auth_handler.generate_jwt_token(
            user_id="user_001",
            tenant_id="tenant_001",
            permissions=[]
        )

        result = auth_handler.refresh_jwt_token(access_token)

        assert result is None


# =============================================================================
# SyncAuthHandler HMAC Tests
# =============================================================================

class TestSyncAuthHandlerHMAC:
    """Tests for HMAC signature validation."""

    def test_validate_hmac_success(self, auth_handler):
        """Test validating valid HMAC signature."""
        secret_key = "shared_secret"
        body = b'{"data": "test"}'
        timestamp = str(int(time.time()))

        message = f"{timestamp}.{body.decode()}"
        signature = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        result = auth_handler.validate_hmac_signature(
            request_body=body,
            signature=signature,
            timestamp=timestamp,
            secret_key=secret_key
        )

        assert result is True

    def test_validate_hmac_wrong_signature(self, auth_handler):
        """Test validating wrong HMAC signature."""
        result = auth_handler.validate_hmac_signature(
            request_body=b'{"data": "test"}',
            signature="wrong_signature",
            timestamp=str(int(time.time())),
            secret_key="shared_secret"
        )

        assert result is False

    def test_validate_hmac_timestamp_too_old(self, auth_handler):
        """Test validating HMAC with old timestamp."""
        secret_key = "shared_secret"
        body = b'{"data": "test"}'
        old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago

        message = f"{old_timestamp}.{body.decode()}"
        signature = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        result = auth_handler.validate_hmac_signature(
            request_body=body,
            signature=signature,
            timestamp=old_timestamp,
            secret_key=secret_key
        )

        assert result is False


# =============================================================================
# IPAccessRule Tests
# =============================================================================

class TestIPAccessRule:
    """Tests for IP access rules."""

    def test_exact_ip_match(self):
        """Test exact IP matching."""
        rule = IPAccessRule(
            ip_pattern="192.168.1.100",
            is_whitelist=True
        )

        assert rule.matches("192.168.1.100") is True
        assert rule.matches("192.168.1.101") is False

    def test_cidr_match(self):
        """Test CIDR range matching."""
        rule = IPAccessRule(
            ip_pattern="192.168.1.0/24",
            is_whitelist=True
        )

        assert rule.matches("192.168.1.1") is True
        assert rule.matches("192.168.1.254") is True
        assert rule.matches("192.168.2.1") is False

    def test_invalid_ip_pattern(self):
        """Test handling invalid IP pattern."""
        rule = IPAccessRule(
            ip_pattern="invalid_pattern",
            is_whitelist=True
        )

        assert rule.matches("192.168.1.1") is False


# =============================================================================
# SyncSecurityHandler IP Access Tests
# =============================================================================

class TestSecurityHandlerIPAccess:
    """Tests for IP access control."""

    def test_add_to_whitelist(self, security_handler):
        """Test adding IP to whitelist."""
        rule = security_handler.add_whitelist(
            "192.168.1.100",
            description="Test whitelist"
        )

        assert rule.ip_pattern == "192.168.1.100"
        assert rule.is_whitelist is True

    def test_add_to_blacklist(self, security_handler):
        """Test adding IP to blacklist."""
        rule = security_handler.add_blacklist(
            "10.0.0.1",
            description="Malicious IP"
        )

        assert rule.ip_pattern == "10.0.0.1"
        assert rule.is_whitelist is False

    def test_check_ip_access_blacklisted(self, security_handler):
        """Test checking blacklisted IP."""
        security_handler.add_blacklist("10.0.0.1", description="Blocked")

        allowed, reason = security_handler.check_ip_access("10.0.0.1")

        assert allowed is False
        assert reason == "Blocked"

    def test_check_ip_access_not_blacklisted(self, security_handler):
        """Test checking non-blacklisted IP."""
        allowed, reason = security_handler.check_ip_access("192.168.1.1")

        assert allowed is True
        assert reason is None

    def test_check_ip_access_temporarily_blocked(self, security_handler):
        """Test checking temporarily blocked IP."""
        # Manually add to blocked IPs
        security_handler._blocked_ips["10.0.0.1"] = datetime.utcnow() + timedelta(hours=1)

        allowed, reason = security_handler.check_ip_access("10.0.0.1")

        assert allowed is False
        assert "temporarily blocked" in reason

    def test_remove_from_whitelist(self, security_handler):
        """Test removing IP from whitelist."""
        security_handler.add_whitelist("192.168.1.100")

        result = security_handler.remove_from_whitelist("192.168.1.100")

        assert result is True

    def test_remove_from_blacklist(self, security_handler):
        """Test removing IP from blacklist."""
        security_handler.add_blacklist("10.0.0.1")

        result = security_handler.remove_from_blacklist("10.0.0.1")

        assert result is True


# =============================================================================
# SyncSecurityHandler DDoS Protection Tests
# =============================================================================

class TestSecurityHandlerDDoS:
    """Tests for DDoS protection."""

    def test_ddos_normal_traffic(self, security_handler):
        """Test normal traffic is not blocked."""
        for _ in range(5):
            blocked = security_handler.check_ddos("192.168.1.1")
            assert blocked is False

    def test_ddos_exceeds_threshold(self, security_handler):
        """Test DDoS detection when threshold exceeded."""
        # Send requests up to threshold
        for _ in range(11):  # Threshold is 10
            security_handler.check_ddos("192.168.1.1")

        # Next request should be blocked
        blocked = security_handler.check_ddos("192.168.1.1")

        assert blocked is True
        assert "192.168.1.1" in security_handler._blocked_ips

    def test_ddos_different_ips(self, security_handler):
        """Test that different IPs are tracked separately."""
        for i in range(11):
            security_handler.check_ddos(f"192.168.1.{i}")

        # No single IP should be blocked
        for i in range(11):
            blocked = security_handler.check_ddos(f"192.168.1.{i}")
            assert blocked is False


# =============================================================================
# SyncSecurityHandler Attack Detection Tests
# =============================================================================

class TestSecurityHandlerAttackDetection:
    """Tests for attack pattern detection."""

    def test_sql_injection_detection(self, security_handler):
        """Test SQL injection detection."""
        threats = [
            "SELECT * FROM users",
            "1 OR 1=1",
            "admin'--",
            "'; DROP TABLE users;--"
        ]

        for content in threats:
            event = security_handler.check_sql_injection(content)
            assert event is not None
            assert event.threat_type == ThreatType.SQL_INJECTION

    def test_sql_injection_clean_content(self, security_handler):
        """Test that clean content passes SQL injection check."""
        clean_contents = [
            "Hello World",
            "User name is John",
            "Order total: 100"
        ]

        for content in clean_contents:
            event = security_handler.check_sql_injection(content)
            assert event is None

    def test_xss_detection(self, security_handler):
        """Test XSS detection."""
        threats = [
            "<script>alert('xss')</script>",
            "javascript:void(0)",
            "onclick=alert(1)",
            "<iframe src='evil.com'>"
        ]

        for content in threats:
            event = security_handler.check_xss(content)
            assert event is not None
            assert event.threat_type == ThreatType.XSS

    def test_xss_clean_content(self, security_handler):
        """Test that clean content passes XSS check."""
        clean_contents = [
            "Hello World",
            "This is a paragraph",
            "Click here for more info"
        ]

        for content in clean_contents:
            event = security_handler.check_xss(content)
            assert event is None

    def test_path_traversal_detection(self, security_handler):
        """Test path traversal detection."""
        threats = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "%2e%2e%2f",
            "..%2fetc%2fpasswd"
        ]

        for path in threats:
            event = security_handler.check_path_traversal(path)
            assert event is not None
            assert event.threat_type == ThreatType.PATH_TRAVERSAL

    def test_path_traversal_clean_path(self, security_handler):
        """Test that clean paths pass path traversal check."""
        clean_paths = [
            "/api/users",
            "/sync/jobs/123",
            "/data/export"
        ]

        for path in clean_paths:
            event = security_handler.check_path_traversal(path)
            assert event is None

    def test_command_injection_detection(self, security_handler):
        """Test command injection detection."""
        threats = [
            "value; rm -rf /",
            "test | cat /etc/passwd",
            "$(whoami)",
            "input && ls"
        ]

        for content in threats:
            event = security_handler.check_command_injection(content)
            assert event is not None
            assert event.threat_type == ThreatType.COMMAND_INJECTION

    def test_command_injection_clean_content(self, security_handler):
        """Test that clean content passes command injection check."""
        clean_contents = [
            "Hello World",
            "test@example.com",
            "User 123"
        ]

        for content in clean_contents:
            event = security_handler.check_command_injection(content)
            assert event is None

    def test_suspicious_agent_detection(self, security_handler):
        """Test suspicious user agent detection."""
        threats = [
            "sqlmap/1.0",
            "Nikto scanner",
            "nmap/7.80",
            "gobuster/3.0"
        ]

        for agent in threats:
            event = security_handler.check_user_agent(agent)
            assert event is not None
            assert event.threat_type == ThreatType.SUSPICIOUS_AGENT

    def test_legitimate_user_agent(self, security_handler):
        """Test that legitimate user agents pass."""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
            "Python-requests/2.25.1",
            "curl/7.68.0"
        ]

        for agent in agents:
            event = security_handler.check_user_agent(agent)
            assert event is None


# =============================================================================
# SyncSecurityHandler Threat Recording Tests
# =============================================================================

class TestSecurityHandlerThreatRecording:
    """Tests for threat event recording and retrieval."""

    def test_record_threat(self, security_handler):
        """Test recording a threat event."""
        event = ThreatEvent(
            id="threat_001",
            threat_type=ThreatType.SQL_INJECTION,
            level=ThreatLevel.HIGH,
            ip_address="10.0.0.1",
            path="/api/users",
            method="GET",
            details={"pattern": "SELECT"},
            timestamp=datetime.utcnow(),
            blocked=True
        )

        security_handler.record_threat(event)

        threats = security_handler.get_threats(limit=10)
        assert len(threats) >= 1
        assert threats[-1].threat_type == ThreatType.SQL_INJECTION

    def test_get_threats_with_type_filter(self, security_handler):
        """Test getting threats filtered by type."""
        # Record different types of threats
        sql_event = ThreatEvent(
            id="threat_001",
            threat_type=ThreatType.SQL_INJECTION,
            level=ThreatLevel.HIGH,
            ip_address="10.0.0.1",
            path="/api",
            method="GET",
            details={},
            timestamp=datetime.utcnow()
        )
        xss_event = ThreatEvent(
            id="threat_002",
            threat_type=ThreatType.XSS,
            level=ThreatLevel.MEDIUM,
            ip_address="10.0.0.2",
            path="/api",
            method="POST",
            details={},
            timestamp=datetime.utcnow()
        )

        security_handler.record_threat(sql_event)
        security_handler.record_threat(xss_event)

        sql_threats = security_handler.get_threats(
            threat_type=ThreatType.SQL_INJECTION
        )

        assert all(t.threat_type == ThreatType.SQL_INJECTION for t in sql_threats)

    def test_get_threats_with_min_level_filter(self, security_handler):
        """Test getting threats filtered by minimum level."""
        low_event = ThreatEvent(
            id="threat_001",
            threat_type=ThreatType.INVALID_INPUT,
            level=ThreatLevel.LOW,
            ip_address="10.0.0.1",
            path="/api",
            method="GET",
            details={},
            timestamp=datetime.utcnow()
        )
        high_event = ThreatEvent(
            id="threat_002",
            threat_type=ThreatType.SQL_INJECTION,
            level=ThreatLevel.HIGH,
            ip_address="10.0.0.2",
            path="/api",
            method="POST",
            details={},
            timestamp=datetime.utcnow()
        )

        security_handler.record_threat(low_event)
        security_handler.record_threat(high_event)

        high_threats = security_handler.get_threats(min_level=ThreatLevel.HIGH)

        level_order = [
            ThreatLevel.NONE,
            ThreatLevel.LOW,
            ThreatLevel.MEDIUM,
            ThreatLevel.HIGH,
            ThreatLevel.CRITICAL
        ]
        high_idx = level_order.index(ThreatLevel.HIGH)

        assert all(
            level_order.index(t.level) >= high_idx
            for t in high_threats
        )

    def test_get_threats_with_ip_filter(self, security_handler):
        """Test getting threats filtered by IP."""
        event1 = ThreatEvent(
            id="threat_001",
            threat_type=ThreatType.SQL_INJECTION,
            level=ThreatLevel.HIGH,
            ip_address="10.0.0.1",
            path="/api",
            method="GET",
            details={},
            timestamp=datetime.utcnow()
        )
        event2 = ThreatEvent(
            id="threat_002",
            threat_type=ThreatType.XSS,
            level=ThreatLevel.MEDIUM,
            ip_address="10.0.0.2",
            path="/api",
            method="POST",
            details={},
            timestamp=datetime.utcnow()
        )

        security_handler.record_threat(event1)
        security_handler.record_threat(event2)

        threats = security_handler.get_threats(ip_address="10.0.0.1")

        assert all(t.ip_address == "10.0.0.1" for t in threats)


# =============================================================================
# SyncSecurityHandler Request Validation Tests
# =============================================================================

class TestSecurityHandlerRequestValidation:
    """Tests for request validation."""

    @pytest.mark.asyncio
    async def test_validate_request_clean(self, security_handler):
        """Test validating a clean request."""
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/users"
        request.method = "GET"
        request.headers = {"user-agent": "Mozilla/5.0"}
        request.url = MagicMock()
        request.url.__str__ = MagicMock(return_value="http://example.com/api/users")
        request.query_params = {}

        valid, threat = await security_handler.validate_request(request)

        assert valid is True
        assert threat is None

    @pytest.mark.asyncio
    async def test_validate_request_suspicious_agent(self, security_handler):
        """Test validating request with suspicious user agent."""
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/users"
        request.method = "GET"
        request.headers = {"user-agent": "sqlmap/1.0"}
        request.url = MagicMock()
        request.url.__str__ = MagicMock(return_value="http://example.com/api/users")
        request.query_params = {}

        # Ensure IP is not blocked
        security_handler._blocked_ips.clear()
        security_handler._ip_blacklist.clear()

        valid, threat = await security_handler.validate_request(request)

        assert valid is False
        assert threat is not None
        assert threat.threat_type == ThreatType.SUSPICIOUS_AGENT

    @pytest.mark.asyncio
    async def test_validate_request_path_traversal(self, security_handler):
        """Test validating request with path traversal."""
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/../../../etc/passwd"
        request.method = "GET"
        request.headers = {"user-agent": "Mozilla/5.0"}
        request.url = MagicMock()
        request.url.__str__ = MagicMock(return_value="http://example.com/api")
        request.query_params = {}

        valid, threat = await security_handler.validate_request(request)

        assert valid is False
        assert threat is not None
        assert threat.threat_type == ThreatType.PATH_TRAVERSAL

    @pytest.mark.asyncio
    async def test_validate_request_sql_injection_in_query(self, security_handler):
        """Test validating request with SQL injection in query params."""
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.url.path = "/api/users"
        request.method = "GET"
        request.headers = {"user-agent": "Mozilla/5.0"}
        request.url = MagicMock()
        request.url.__str__ = MagicMock(return_value="http://example.com/api/users")
        request.query_params = {"id": "1 OR 1=1"}

        valid, threat = await security_handler.validate_request(request)

        assert valid is False
        assert threat is not None
        assert threat.threat_type == ThreatType.SQL_INJECTION


# =============================================================================
# ThreatEvent Tests
# =============================================================================

class TestThreatEvent:
    """Tests for ThreatEvent class."""

    def test_threat_event_creation(self):
        """Test creating a threat event."""
        event = ThreatEvent(
            id="threat_001",
            threat_type=ThreatType.SQL_INJECTION,
            level=ThreatLevel.HIGH,
            ip_address="10.0.0.1",
            path="/api/users",
            method="POST",
            details={"query": "SELECT * FROM users"},
            timestamp=datetime.utcnow(),
            tenant_id="tenant_001",
            user_id="user_001",
            blocked=True
        )

        assert event.threat_type == ThreatType.SQL_INJECTION
        assert event.level == ThreatLevel.HIGH
        assert event.blocked is True


# =============================================================================
# SecurityConfig Tests
# =============================================================================

class TestSecurityConfig:
    """Tests for SecurityConfig class."""

    def test_default_config(self):
        """Test default security configuration."""
        config = SecurityConfig()

        assert config.ddos_protection_enabled is True
        assert config.sql_injection_protection is True
        assert config.xss_protection is True
        assert config.ddos_threshold_requests == 1000

    def test_custom_config(self):
        """Test custom security configuration."""
        config = SecurityConfig(
            ddos_threshold_requests=500,
            max_request_size=5 * 1024 * 1024
        )

        assert config.ddos_threshold_requests == 500
        assert config.max_request_size == 5 * 1024 * 1024


# =============================================================================
# AuthConfig Tests
# =============================================================================

class TestAuthConfig:
    """Tests for AuthConfig class."""

    def test_default_config(self):
        """Test default auth configuration."""
        config = AuthConfig()

        assert config.jwt_algorithm == "HS256"
        assert config.jwt_expiry_minutes == 60
        assert config.api_key_prefix == "sk_"

    def test_custom_config(self):
        """Test custom auth configuration."""
        config = AuthConfig(
            jwt_secret_key="custom_secret",
            jwt_expiry_minutes=30
        )

        assert config.jwt_secret_key == "custom_secret"
        assert config.jwt_expiry_minutes == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
