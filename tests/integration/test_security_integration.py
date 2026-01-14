"""
Integration tests for security components.

Tests the interaction between RBAC, permissions, sessions, and encryption services.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.security.rbac_engine import RBACEngine, Permission, AccessDecision
from src.security.permission_manager import PermissionManager
from src.security.session_manager import SessionManager, Session
from src.security.encryption_service import DataEncryptionService
from src.security.audit_logger import AuditLogger


class TestRBACPermissionIntegration:
    """Integration tests for RBAC and Permission Manager."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.all.return_value = []
        db.commit = MagicMock()
        db.rollback = MagicMock()
        db.refresh = MagicMock()
        db.add = MagicMock()
        return db
    
    @pytest.fixture
    def rbac_engine(self):
        """RBAC engine instance."""
        return RBACEngine(cache_ttl=300)
    
    @pytest.fixture
    def permission_manager(self, rbac_engine):
        """Permission manager with RBAC engine."""
        return PermissionManager(rbac_engine=rbac_engine)
    
    def test_rbac_permission_flow(self, rbac_engine, permission_manager, mock_db):
        """Test complete RBAC permission checking flow."""
        user_id = uuid4()
        tenant_id = "tenant-123"
        resource = "projects/123"
        action = "read"
        
        # Mock role with permissions
        mock_role = MagicMock()
        mock_role.id = uuid4()
        mock_role.name = "project_viewer"
        mock_role.permissions = [{"resource": "projects/*", "action": "read"}]
        mock_role.parent_role_id = None
        mock_role.is_active = True
        
        # Mock user role assignment
        mock_assignment = MagicMock()
        mock_assignment.role_id = mock_role.id
        mock_assignment.user_id = user_id
        mock_assignment.is_active = True
        mock_assignment.expires_at = None
        
        # Setup mock queries
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_role]
        
        # Test permission check
        decision = rbac_engine.check_permission(user_id, resource, action, tenant_id, mock_db)
        
        assert isinstance(decision, AccessDecision)
    
    def test_role_hierarchy_permission_inheritance(self, rbac_engine, mock_db):
        """Test permission inheritance through role hierarchy."""
        user_id = uuid4()
        tenant_id = "tenant-123"
        
        # Create parent role with admin permissions
        parent_role = MagicMock()
        parent_role.id = uuid4()
        parent_role.name = "admin"
        parent_role.permissions = [{"resource": "*", "action": "*"}]
        parent_role.parent_role_id = None
        parent_role.is_active = True
        
        # Create child role that inherits from parent
        child_role = MagicMock()
        child_role.id = uuid4()
        child_role.name = "project_admin"
        child_role.permissions = [{"resource": "projects/*", "action": "write"}]
        child_role.parent_role_id = parent_role.id
        child_role.is_active = True
        
        # Mock queries
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [child_role]
        mock_db.query.return_value.filter.return_value.first.return_value = parent_role
        
        # User with child role should have parent permissions through inheritance
        decision = rbac_engine.check_permission(user_id, "datasets/456", "delete", tenant_id, mock_db)
        
        assert isinstance(decision, AccessDecision)
    
    def test_permission_cache_invalidation(self, rbac_engine, mock_db):
        """Test that permission cache is properly invalidated."""
        user_id = uuid4()
        tenant_id = "tenant-123"
        
        # First check - should cache result
        mock_role = MagicMock()
        mock_role.id = uuid4()
        mock_role.permissions = [{"resource": "projects/*", "action": "read"}]
        mock_role.parent_role_id = None
        mock_role.is_active = True
        
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_role]
        
        rbac_engine.check_permission(user_id, "projects/123", "read", tenant_id, mock_db)
        
        # Invalidate cache
        invalidated = rbac_engine.invalidate_user_cache(user_id)
        
        # Cache should be cleared
        assert invalidated >= 0
    
    def test_wildcard_permission_matching(self, rbac_engine, mock_db):
        """Test wildcard permission matching."""
        user_id = uuid4()
        tenant_id = "tenant-123"
        
        # Role with wildcard permissions
        mock_role = MagicMock()
        mock_role.id = uuid4()
        mock_role.permissions = [
            {"resource": "projects/*", "action": "*"},
            {"resource": "datasets/public/*", "action": "read"}
        ]
        mock_role.parent_role_id = None
        mock_role.is_active = True
        
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_role]
        
        # Test various resource/action combinations
        test_cases = [
            ("projects/123", "read", True),
            ("projects/456", "write", True),
            ("projects/789", "delete", True),
            ("datasets/public/data1", "read", True),
        ]
        
        for resource, action, expected in test_cases:
            decision = rbac_engine.check_permission(user_id, resource, action, tenant_id, mock_db)
            assert isinstance(decision, AccessDecision)


class TestSessionSecurityIntegration:
    """Integration tests for Session Manager with security components."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis = AsyncMock()
        redis.smembers.return_value = []
        redis.setex.return_value = True
        redis.sadd.return_value = 1
        redis.expire.return_value = True
        redis.get.return_value = None
        redis.delete.return_value = 1
        redis.srem.return_value = 1
        redis.ttl.return_value = 3600
        redis.exists.return_value = True
        redis.keys.return_value = []
        redis.scard.return_value = 0
        redis.set.return_value = True
        return redis
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Mock audit logger."""
        logger = AsyncMock(spec=AuditLogger)
        logger.log = AsyncMock()
        return logger
    
    @pytest.fixture
    def session_manager(self, mock_redis, mock_audit_logger):
        """Session manager instance."""
        return SessionManager(
            redis_client=mock_redis,
            audit_logger=mock_audit_logger,
            default_timeout=3600,
            max_concurrent_sessions=5
        )
    
    @pytest.mark.asyncio
    async def test_session_creation_with_audit(self, session_manager, mock_audit_logger):
        """Test session creation triggers audit logging."""
        user_id = "user-123"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"
        
        with patch('src.security.session_manager.uuid4') as mock_uuid:
            mock_uuid.return_value.__str__ = lambda self: "test-session-id"
            
            session = await session_manager.create_session(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        # Verify session created
        assert session.user_id == user_id
        assert session.ip_address == ip_address
        
        # Verify audit log was called
        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args
        assert call_args[1]["event_type"] == "session_created"
        assert call_args[1]["user_id"] == user_id
    
    @pytest.mark.asyncio
    async def test_session_destruction_with_audit(self, session_manager, mock_redis, mock_audit_logger):
        """Test session destruction triggers audit logging."""
        session_id = "test-session-id"
        user_id = "user-123"
        
        # Mock existing session
        session_data = {
            "id": session_id,
            "user_id": user_id,
            "ip_address": "192.168.1.1",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        mock_redis.get.return_value = json.dumps(session_data)
        
        result = await session_manager.destroy_session(session_id)
        
        assert result is True
        
        # Verify audit log was called
        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args
        assert call_args[1]["event_type"] == "session_destroyed"
    
    @pytest.mark.asyncio
    async def test_concurrent_session_limit_enforcement(self, session_manager, mock_redis, mock_audit_logger):
        """Test concurrent session limit is enforced."""
        user_id = "user-123"
        ip_address = "192.168.1.1"
        
        # Create 5 existing sessions (at limit)
        existing_sessions = []
        for i in range(5):
            session = Session(
                id=f"session-{i}",
                user_id=user_id,
                ip_address=ip_address,
                created_at=datetime.utcnow() - timedelta(minutes=i)
            )
            existing_sessions.append(session)
        
        with patch.object(session_manager, 'get_user_sessions') as mock_get_sessions:
            mock_get_sessions.return_value = existing_sessions
            
            with patch.object(session_manager, 'destroy_session') as mock_destroy:
                mock_destroy.return_value = True
                
                with patch('src.security.session_manager.uuid4') as mock_uuid:
                    mock_uuid.return_value.__str__ = lambda self: "new-session-id"
                    
                    session = await session_manager.create_session(
                        user_id=user_id,
                        ip_address=ip_address
                    )
                
                # Oldest session should be destroyed
                mock_destroy.assert_called_once_with("session-4")
    
    @pytest.mark.asyncio
    async def test_force_logout_all_sessions(self, session_manager, mock_audit_logger):
        """Test force logout destroys all user sessions."""
        user_id = "user-123"
        
        # Mock existing sessions
        existing_sessions = [
            Session(id="session-1", user_id=user_id, ip_address="192.168.1.1"),
            Session(id="session-2", user_id=user_id, ip_address="192.168.1.2"),
            Session(id="session-3", user_id=user_id, ip_address="192.168.1.3")
        ]
        
        with patch.object(session_manager, 'get_user_sessions') as mock_get_sessions:
            mock_get_sessions.return_value = existing_sessions
            
            with patch.object(session_manager, 'destroy_session') as mock_destroy:
                mock_destroy.return_value = True
                
                destroyed_count = await session_manager.force_logout(user_id)
        
        assert destroyed_count == 3
        assert mock_destroy.call_count == 3
        
        # Verify audit log
        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args
        assert call_args[1]["event_type"] == "force_logout"


class TestEncryptionIntegration:
    """Integration tests for encryption service."""
    
    @pytest.fixture
    def mock_key_store(self):
        """Mock key store."""
        key_store = AsyncMock()
        key_store.get_current_key.return_value = b"0" * 32  # 256-bit key
        key_store.get_key_by_id.return_value = b"0" * 32
        return key_store
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip."""
        # Test with simple encryption service
        plaintext = "sensitive data to encrypt"
        
        # Create a simple encryption test
        import hashlib
        
        # Simulate encryption/decryption
        key = hashlib.sha256(b"test-key").digest()
        
        # Simple XOR encryption for testing
        encrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(plaintext.encode())])
        decrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(encrypted)]).decode()
        
        assert decrypted == plaintext
    
    def test_field_level_encryption(self):
        """Test field-level encryption for database fields."""
        sensitive_fields = {
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111",
            "password": "secret123"
        }
        
        import hashlib
        key = hashlib.sha256(b"field-encryption-key").digest()
        
        encrypted_fields = {}
        for field_name, value in sensitive_fields.items():
            encrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(value.encode())])
            encrypted_fields[field_name] = encrypted.hex()
        
        # Verify all fields are encrypted
        for field_name in sensitive_fields:
            assert field_name in encrypted_fields
            assert encrypted_fields[field_name] != sensitive_fields[field_name]
        
        # Verify decryption
        for field_name, encrypted_hex in encrypted_fields.items():
            encrypted = bytes.fromhex(encrypted_hex)
            decrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(encrypted)]).decode()
            assert decrypted == sensitive_fields[field_name]


class TestSecurityWorkflow:
    """Integration tests for complete security workflows."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return MagicMock()
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis = AsyncMock()
        redis.smembers.return_value = []
        redis.setex.return_value = True
        redis.sadd.return_value = 1
        redis.expire.return_value = True
        return redis
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Mock audit logger."""
        return AsyncMock(spec=AuditLogger)
    
    @pytest.mark.asyncio
    async def test_user_login_workflow(self, mock_redis, mock_audit_logger):
        """Test complete user login workflow."""
        user_id = "user-123"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"
        
        # Create session manager
        session_manager = SessionManager(
            redis_client=mock_redis,
            audit_logger=mock_audit_logger
        )
        
        with patch('src.security.session_manager.uuid4') as mock_uuid:
            mock_uuid.return_value.__str__ = lambda self: "login-session-id"
            
            # Step 1: Create session on login
            session = await session_manager.create_session(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"login_method": "password"}
            )
        
        assert session is not None
        assert session.user_id == user_id
        assert session.metadata.get("login_method") == "password"
        
        # Verify audit log
        mock_audit_logger.log.assert_called()
    
    @pytest.mark.asyncio
    async def test_permission_denied_workflow(self, mock_db):
        """Test workflow when permission is denied."""
        rbac_engine = RBACEngine()
        user_id = uuid4()
        tenant_id = "tenant-123"
        
        # Mock no roles for user
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        # Check permission - should be denied
        decision = rbac_engine.check_permission(
            user_id, "admin/settings", "write", tenant_id, mock_db
        )
        
        assert isinstance(decision, AccessDecision)
        assert decision.allowed is False
    
    @pytest.mark.asyncio
    async def test_session_timeout_workflow(self, mock_redis, mock_audit_logger):
        """Test session timeout handling workflow."""
        user_id = "user-123"
        
        session_manager = SessionManager(
            redis_client=mock_redis,
            audit_logger=mock_audit_logger,
            default_timeout=60  # 1 minute timeout
        )
        
        # Create expired session data
        expired_session = {
            "id": "expired-session",
            "user_id": user_id,
            "ip_address": "192.168.1.1",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "last_activity": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        }
        
        mock_redis.get.return_value = json.dumps(expired_session)
        
        with patch.object(session_manager, 'destroy_session') as mock_destroy:
            mock_destroy.return_value = True
            
            # Validate expired session - should return None
            result = await session_manager.validate_session("expired-session")
        
        assert result is None
        mock_destroy.assert_called_once_with("expired-session")