"""
Unit tests for SessionManager.

Tests session creation, validation, destruction, concurrent limits,
timeout configuration, and all session management functionality.
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.security.session_manager import SessionManager, Session
from src.security.audit_logger import AuditLogger


class TestSession:
    """Test Session data class."""
    
    def test_session_creation(self):
        """Test Session object creation."""
        session_id = str(uuid4())
        user_id = "user123"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"
        
        session = Session(
            id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        assert session.id == session_id
        assert session.user_id == user_id
        assert session.ip_address == ip_address
        assert session.user_agent == user_agent
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity, datetime)
        assert session.expires_at is None
        assert session.metadata == {}
    
    def test_session_to_dict(self):
        """Test Session serialization to dictionary."""
        session_id = str(uuid4())
        user_id = "user123"
        ip_address = "192.168.1.1"
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=1)
        
        session = Session(
            id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            created_at=now,
            last_activity=now,
            expires_at=expires_at,
            metadata={"key": "value"}
        )
        
        session_dict = session.to_dict()
        
        assert session_dict["id"] == session_id
        assert session_dict["user_id"] == user_id
        assert session_dict["ip_address"] == ip_address
        assert session_dict["created_at"] == now.isoformat()
        assert session_dict["last_activity"] == now.isoformat()
        assert session_dict["expires_at"] == expires_at.isoformat()
        assert session_dict["metadata"] == {"key": "value"}
    
    def test_session_from_dict(self):
        """Test Session deserialization from dictionary."""
        session_id = str(uuid4())
        user_id = "user123"
        ip_address = "192.168.1.1"
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=1)
        
        session_dict = {
            "id": session_id,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": "Mozilla/5.0",
            "created_at": now.isoformat(),
            "last_activity": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "metadata": {"key": "value"}
        }
        
        session = Session.from_dict(session_dict)
        
        assert session.id == session_id
        assert session.user_id == user_id
        assert session.ip_address == ip_address
        assert session.user_agent == "Mozilla/5.0"
        assert session.created_at == now
        assert session.last_activity == now
        assert session.expires_at == expires_at
        assert session.metadata == {"key": "value"}
    
    def test_session_from_dict_minimal(self):
        """Test Session deserialization with minimal data."""
        session_id = str(uuid4())
        user_id = "user123"
        ip_address = "192.168.1.1"
        now = datetime.utcnow()
        
        session_dict = {
            "id": session_id,
            "user_id": user_id,
            "ip_address": ip_address,
            "created_at": now.isoformat(),
            "last_activity": now.isoformat()
        }
        
        session = Session.from_dict(session_dict)
        
        assert session.id == session_id
        assert session.user_id == user_id
        assert session.ip_address == ip_address
        assert session.user_agent is None
        assert session.expires_at is None
        assert session.metadata == {}
    
    def test_session_is_expired_true(self):
        """Test session expiry check when expired."""
        session = Session(
            id=str(uuid4()),
            user_id="user123",
            ip_address="192.168.1.1",
            expires_at=datetime.utcnow() - timedelta(minutes=1)
        )
        
        assert session.is_expired is True
    
    def test_session_is_expired_false(self):
        """Test session expiry check when not expired."""
        session = Session(
            id=str(uuid4()),
            user_id="user123",
            ip_address="192.168.1.1",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert session.is_expired is False
    
    def test_session_is_expired_no_expiry(self):
        """Test session expiry check when no expiry set."""
        session = Session(
            id=str(uuid4()),
            user_id="user123",
            ip_address="192.168.1.1"
        )
        
        assert session.is_expired is False
    
    def test_session_time_until_expiry(self):
        """Test time until expiry calculation."""
        expires_at = datetime.utcnow() + timedelta(hours=1)
        session = Session(
            id=str(uuid4()),
            user_id="user123",
            ip_address="192.168.1.1",
            expires_at=expires_at
        )
        
        time_until = session.time_until_expiry
        assert time_until is not None
        assert time_until.total_seconds() > 3500  # Close to 1 hour
        assert time_until.total_seconds() < 3600
    
    def test_session_time_until_expiry_no_expiry(self):
        """Test time until expiry when no expiry set."""
        session = Session(
            id=str(uuid4()),
            user_id="user123",
            ip_address="192.168.1.1"
        )
        
        assert session.time_until_expiry is None


class TestSessionManager:
    """Test SessionManager class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis_mock = AsyncMock()
        return redis_mock
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Mock AuditLogger."""
        audit_mock = AsyncMock(spec=AuditLogger)
        return audit_mock
    
    @pytest.fixture
    def session_manager(self, mock_redis, mock_audit_logger):
        """Create SessionManager instance with mocks."""
        return SessionManager(
            redis_client=mock_redis,
            audit_logger=mock_audit_logger,
            default_timeout=3600,
            max_concurrent_sessions=5
        )
    
    @pytest.mark.asyncio
    async def test_create_session_basic(self, session_manager, mock_redis, mock_audit_logger):
        """Test basic session creation."""
        user_id = "user123"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"
        
        # Mock Redis operations
        mock_redis.smembers.return_value = []  # No existing sessions
        mock_redis.setex.return_value = True
        mock_redis.sadd.return_value = 1
        mock_redis.expire.return_value = True
        
        with patch('src.security.session_manager.uuid4') as mock_uuid:
            mock_uuid.return_value.__str__ = lambda self: "test-session-id"
            
            session = await session_manager.create_session(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        # Verify session properties
        assert session.id == "test-session-id"
        assert session.user_id == user_id
        assert session.ip_address == ip_address
        assert session.user_agent == user_agent
        assert session.expires_at is not None
        
        # Verify Redis calls
        mock_redis.setex.assert_called_once()
        mock_redis.sadd.assert_called_once()
        mock_redis.expire.assert_called_once()
        
        # Verify audit log
        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args
        assert call_args[1]["event_type"] == "session_created"
        assert call_args[1]["user_id"] == user_id
        assert call_args[1]["ip_address"] == ip_address
    
    @pytest.mark.asyncio
    async def test_create_session_with_custom_timeout(self, session_manager, mock_redis, mock_audit_logger):
        """Test session creation with custom timeout."""
        user_id = "user123"
        ip_address = "192.168.1.1"
        custom_timeout = 7200  # 2 hours
        
        mock_redis.smembers.return_value = []
        mock_redis.setex.return_value = True
        mock_redis.sadd.return_value = 1
        mock_redis.expire.return_value = True
        
        with patch('src.security.session_manager.uuid4') as mock_uuid:
            mock_uuid.return_value.__str__ = lambda self: "test-session-id"
            
            session = await session_manager.create_session(
                user_id=user_id,
                ip_address=ip_address,
                timeout=custom_timeout
            )
        
        # Verify timeout is applied
        expected_expiry = session.created_at + timedelta(seconds=custom_timeout)
        assert abs((session.expires_at - expected_expiry).total_seconds()) < 1
        
        # Verify Redis setex called with custom timeout
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[1] == custom_timeout  # timeout parameter
    
    @pytest.mark.asyncio
    async def test_create_session_with_metadata(self, session_manager, mock_redis, mock_audit_logger):
        """Test session creation with metadata."""
        user_id = "user123"
        ip_address = "192.168.1.1"
        metadata = {"role": "admin", "department": "IT"}
        
        mock_redis.smembers.return_value = []
        mock_redis.setex.return_value = True
        mock_redis.sadd.return_value = 1
        mock_redis.expire.return_value = True
        
        with patch('src.security.session_manager.uuid4') as mock_uuid:
            mock_uuid.return_value.__str__ = lambda self: "test-session-id"
            
            session = await session_manager.create_session(
                user_id=user_id,
                ip_address=ip_address,
                metadata=metadata
            )
        
        assert session.metadata == metadata
    
    @pytest.mark.asyncio
    async def test_create_session_concurrent_limit_exceeded(self, session_manager, mock_redis, mock_audit_logger):
        """Test session creation when concurrent limit is exceeded."""
        user_id = "user123"
        ip_address = "192.168.1.1"
        
        # Mock existing sessions (at limit)
        existing_sessions = []
        for i in range(5):  # max_concurrent_sessions = 5
            session_data = {
                "id": f"session-{i}",
                "user_id": user_id,
                "ip_address": "192.168.1.1",
                "created_at": (datetime.utcnow() - timedelta(minutes=i)).isoformat(),
                "last_activity": datetime.utcnow().isoformat()
            }
            existing_sessions.append(session_data)
        
        # Mock get_user_sessions to return existing sessions
        with patch.object(session_manager, 'get_user_sessions') as mock_get_sessions:
            mock_get_sessions.return_value = [Session.from_dict(s) for s in existing_sessions]
            
            # Mock destroy_session
            with patch.object(session_manager, 'destroy_session') as mock_destroy:
                mock_destroy.return_value = True
                
                mock_redis.setex.return_value = True
                mock_redis.sadd.return_value = 1
                mock_redis.expire.return_value = True
                
                with patch('src.security.session_manager.uuid4') as mock_uuid:
                    mock_uuid.return_value.__str__ = lambda self: "new-session-id"
                    
                    session = await session_manager.create_session(
                        user_id=user_id,
                        ip_address=ip_address
                    )
                
                # Verify oldest session was destroyed
                mock_destroy.assert_called_once_with("session-4")  # Oldest session
                
                # Verify new session was created
                assert session.id == "new-session-id"
    
    @pytest.mark.asyncio
    async def test_validate_session_valid(self, session_manager, mock_redis):
        """Test validating a valid session."""
        session_id = "test-session-id"
        session_data = {
            "id": session_id,
            "user_id": "user123",
            "ip_address": "192.168.1.1",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        
        mock_redis.get.return_value = json.dumps(session_data)
        mock_redis.ttl.return_value = 3600
        mock_redis.setex.return_value = True
        
        session = await session_manager.validate_session(session_id)
        
        assert session is not None
        assert session.id == session_id
        assert session.user_id == "user123"
        
        # Verify last_activity was updated
        assert session.last_activity > datetime.fromisoformat(session_data["last_activity"])
        
        # Verify Redis operations
        mock_redis.get.assert_called_once_with(f"session:{session_id}")
        mock_redis.ttl.assert_called_once()
        mock_redis.setex.assert_called_once()  # Session refreshed
    
    @pytest.mark.asyncio
    async def test_validate_session_not_found(self, session_manager, mock_redis):
        """Test validating a non-existent session."""
        session_id = "non-existent-session"
        
        mock_redis.get.return_value = None
        
        session = await session_manager.validate_session(session_id)
        
        assert session is None
        mock_redis.get.assert_called_once_with(f"session:{session_id}")
    
    @pytest.mark.asyncio
    async def test_validate_session_expired(self, session_manager, mock_redis):
        """Test validating an expired session."""
        session_id = "expired-session"
        session_data = {
            "id": session_id,
            "user_id": "user123",
            "ip_address": "192.168.1.1",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "last_activity": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()  # Expired
        }
        
        mock_redis.get.return_value = json.dumps(session_data)
        mock_redis.delete.return_value = 1
        mock_redis.srem.return_value = 1
        
        with patch.object(session_manager, 'destroy_session') as mock_destroy:
            mock_destroy.return_value = True
            
            session = await session_manager.validate_session(session_id)
        
        assert session is None
        mock_destroy.assert_called_once_with(session_id)
    
    @pytest.mark.asyncio
    async def test_validate_session_invalid_data(self, session_manager, mock_redis):
        """Test validating a session with invalid JSON data."""
        session_id = "invalid-session"
        
        mock_redis.get.return_value = "invalid-json-data"
        
        with patch.object(session_manager, 'destroy_session') as mock_destroy:
            mock_destroy.return_value = True
            
            session = await session_manager.validate_session(session_id)
        
        assert session is None
        mock_destroy.assert_called_once_with(session_id)
    
    @pytest.mark.asyncio
    async def test_destroy_session_success(self, session_manager, mock_redis, mock_audit_logger):
        """Test successful session destruction."""
        session_id = "test-session-id"
        user_id = "user123"
        session_data = {
            "id": session_id,
            "user_id": user_id,
            "ip_address": "192.168.1.1"
        }
        
        mock_redis.get.return_value = json.dumps(session_data)
        mock_redis.delete.return_value = 1
        mock_redis.srem.return_value = 1
        
        result = await session_manager.destroy_session(session_id)
        
        assert result is True
        
        # Verify Redis operations
        mock_redis.delete.assert_called_once_with(f"session:{session_id}")
        mock_redis.srem.assert_called_once_with(f"user_sessions:{user_id}", session_id)
        
        # Verify audit log
        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args
        assert call_args[1]["event_type"] == "session_destroyed"
        assert call_args[1]["user_id"] == user_id
    
    @pytest.mark.asyncio
    async def test_destroy_session_not_found(self, session_manager, mock_redis):
        """Test destroying a non-existent session."""
        session_id = "non-existent-session"
        
        mock_redis.get.return_value = None
        
        result = await session_manager.destroy_session(session_id)
        
        assert result is False
        mock_redis.get.assert_called_once_with(f"session:{session_id}")
    
    @pytest.mark.asyncio
    async def test_force_logout(self, session_manager, mock_audit_logger):
        """Test force logout functionality."""
        user_id = "user123"
        
        # Mock user sessions
        sessions = [
            Session(id="session-1", user_id=user_id, ip_address="192.168.1.1"),
            Session(id="session-2", user_id=user_id, ip_address="192.168.1.2"),
            Session(id="session-3", user_id=user_id, ip_address="192.168.1.3")
        ]
        
        with patch.object(session_manager, 'get_user_sessions') as mock_get_sessions:
            mock_get_sessions.return_value = sessions
            
            with patch.object(session_manager, 'destroy_session') as mock_destroy:
                mock_destroy.return_value = True
                
                destroyed_count = await session_manager.force_logout(user_id)
        
        assert destroyed_count == 3
        assert mock_destroy.call_count == 3
        
        # Verify audit log
        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args
        assert call_args[1]["event_type"] == "force_logout"
        assert call_args[1]["user_id"] == user_id
        assert call_args[1]["details"]["sessions_destroyed"] == 3
    
    @pytest.mark.asyncio
    async def test_get_user_sessions(self, session_manager, mock_redis):
        """Test getting user sessions."""
        user_id = "user123"
        session_ids = [b"session-1", b"session-2", b"session-3"]
        
        # Mock Redis operations
        mock_redis.smembers.return_value = session_ids
        
        # Mock session data
        session_data_1 = {
            "id": "session-1",
            "user_id": user_id,
            "ip_address": "192.168.1.1",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        session_data_2 = {
            "id": "session-2",
            "user_id": user_id,
            "ip_address": "192.168.1.2",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        # session-3 will be expired
        session_data_3 = {
            "id": "session-3",
            "user_id": user_id,
            "ip_address": "192.168.1.3",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "last_activity": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()  # Expired
        }
        
        mock_redis.get.side_effect = [
            json.dumps(session_data_1),
            json.dumps(session_data_2),
            json.dumps(session_data_3)
        ]
        
        with patch.object(session_manager, 'destroy_session') as mock_destroy:
            mock_destroy.return_value = True
            
            sessions = await session_manager.get_user_sessions(user_id)
        
        # Should return 2 valid sessions, expired one should be destroyed
        assert len(sessions) == 2
        assert sessions[0].id == "session-1"
        assert sessions[1].id == "session-2"
        
        # Verify expired session was destroyed
        mock_destroy.assert_called_once_with("session-3")
    
    @pytest.mark.asyncio
    async def test_get_user_sessions_invalid_data(self, session_manager, mock_redis):
        """Test getting user sessions with invalid session data."""
        user_id = "user123"
        session_ids = [b"session-1", b"session-2"]
        
        mock_redis.smembers.return_value = session_ids
        mock_redis.get.side_effect = [
            json.dumps({"id": "session-1", "user_id": user_id, "ip_address": "192.168.1.1", 
                       "created_at": datetime.utcnow().isoformat(), 
                       "last_activity": datetime.utcnow().isoformat()}),
            "invalid-json"  # Invalid JSON
        ]
        mock_redis.srem.return_value = 1
        
        sessions = await session_manager.get_user_sessions(user_id)
        
        # Should return 1 valid session, invalid one should be cleaned up
        assert len(sessions) == 1
        assert sessions[0].id == "session-1"
        
        # Verify cleanup of invalid session
        mock_redis.srem.assert_called_once_with(f"user_sessions:{user_id}", b"session-2")
    
    @pytest.mark.asyncio
    async def test_get_active_sessions(self, session_manager, mock_redis):
        """Test getting all active sessions."""
        session_keys = [b"session:session-1", b"session:session-2", b"session:session-3"]
        
        mock_redis.keys.return_value = session_keys
        
        # Mock session data
        session_data_1 = {
            "id": "session-1",
            "user_id": "user1",
            "ip_address": "192.168.1.1",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        session_data_2 = {
            "id": "session-2",
            "user_id": "user2",
            "ip_address": "192.168.1.2",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        # session-3 will be expired
        session_data_3 = {
            "id": "session-3",
            "user_id": "user3",
            "ip_address": "192.168.1.3",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "last_activity": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()  # Expired
        }
        
        mock_redis.get.side_effect = [
            json.dumps(session_data_1),
            json.dumps(session_data_2),
            json.dumps(session_data_3)
        ]
        
        sessions = await session_manager.get_active_sessions(limit=10)
        
        # Should return 2 valid sessions (expired one filtered out)
        assert len(sessions) == 2
        assert sessions[0].id == "session-1"
        assert sessions[1].id == "session-2"
    
    @pytest.mark.asyncio
    async def test_configure_timeout(self, session_manager, mock_redis):
        """Test configuring session timeout."""
        new_timeout = 7200  # 2 hours
        
        mock_redis.set.return_value = True
        
        await session_manager.configure_timeout(new_timeout)
        
        assert session_manager.default_timeout == new_timeout
        
        # Verify Redis configuration storage
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args[0]
        assert call_args[0] == "session_config"
        
        config_data = json.loads(call_args[1])
        assert config_data["default_timeout"] == new_timeout
        assert config_data["max_concurrent_sessions"] == 5
    
    @pytest.mark.asyncio
    async def test_configure_max_concurrent(self, session_manager, mock_redis):
        """Test configuring maximum concurrent sessions."""
        new_max = 10
        
        mock_redis.set.return_value = True
        
        await session_manager.configure_max_concurrent(new_max)
        
        assert session_manager.max_concurrent_sessions == new_max
        
        # Verify Redis configuration storage
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args[0]
        config_data = json.loads(call_args[1])
        assert config_data["max_concurrent_sessions"] == new_max
    
    @pytest.mark.asyncio
    async def test_extend_session_success(self, session_manager, mock_redis):
        """Test extending session timeout."""
        session_id = "test-session-id"
        additional_seconds = 1800  # 30 minutes
        current_ttl = 3600  # 1 hour
        
        mock_redis.exists.return_value = True
        mock_redis.ttl.return_value = current_ttl
        mock_redis.expire.return_value = True
        
        result = await session_manager.extend_session(session_id, additional_seconds)
        
        assert result is True
        
        # Verify Redis operations
        mock_redis.exists.assert_called_once_with(f"session:{session_id}")
        mock_redis.ttl.assert_called_once_with(f"session:{session_id}")
        mock_redis.expire.assert_called_once_with(f"session:{session_id}", current_ttl + additional_seconds)
    
    @pytest.mark.asyncio
    async def test_extend_session_not_found(self, session_manager, mock_redis):
        """Test extending non-existent session."""
        session_id = "non-existent-session"
        additional_seconds = 1800
        
        mock_redis.exists.return_value = False
        
        result = await session_manager.extend_session(session_id, additional_seconds)
        
        assert result is False
        mock_redis.exists.assert_called_once_with(f"session:{session_id}")
    
    @pytest.mark.asyncio
    async def test_extend_session_no_ttl(self, session_manager, mock_redis):
        """Test extending session with no TTL."""
        session_id = "test-session-id"
        additional_seconds = 1800
        
        mock_redis.exists.return_value = True
        mock_redis.ttl.return_value = -1  # No TTL
        
        result = await session_manager.extend_session(session_id, additional_seconds)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_manager, mock_redis):
        """Test cleaning up expired sessions."""
        session_keys = [b"session:session-1", b"session:session-2", b"session:session-3"]
        
        mock_redis.keys.return_value = session_keys
        
        # Mock session data - mix of valid, expired, and invalid
        session_data_1 = {
            "id": "session-1",
            "user_id": "user1",
            "ip_address": "192.168.1.1",
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()  # Valid
        }
        session_data_2 = {
            "id": "session-2",
            "user_id": "user2",
            "ip_address": "192.168.1.2",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "last_activity": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()  # Expired
        }
        
        mock_redis.get.side_effect = [
            json.dumps(session_data_1),
            json.dumps(session_data_2),
            "invalid-json"  # Invalid data
        ]
        mock_redis.delete.return_value = 1
        
        with patch.object(session_manager, 'destroy_session') as mock_destroy:
            mock_destroy.return_value = True
            
            cleaned_count = await session_manager.cleanup_expired_sessions()
        
        # Should clean up 1 expired session + 1 invalid session
        assert cleaned_count == 2
        mock_destroy.assert_called_once_with("session-2")  # Expired session
        mock_redis.delete.assert_called_once_with(b"session:session-3")  # Invalid session
    
    @pytest.mark.asyncio
    async def test_get_session_statistics(self, session_manager, mock_redis):
        """Test getting session statistics."""
        # Mock session keys
        session_keys = [b"session:session-1", b"session:session-2", b"session:session-3"]
        mock_redis.keys.side_effect = [
            session_keys,  # For total sessions
            [b"user_sessions:user1", b"user_sessions:user2", b"user_sessions:user3"]  # For user sessions
        ]
        
        # Mock user session counts
        mock_redis.scard.side_effect = [3, 2, 1]  # user1: 3, user2: 2, user3: 1
        
        stats = await session_manager.get_session_statistics()
        
        assert stats["total_active_sessions"] == 3
        assert stats["total_users_with_sessions"] == 3
        assert stats["top_users_by_sessions"] == {"user1": 3, "user2": 2, "user3": 1}
        assert stats["configuration"]["default_timeout"] == 3600
        assert stats["configuration"]["max_concurrent_sessions"] == 5
    
    def test_session_manager_initialization(self, mock_redis, mock_audit_logger):
        """Test SessionManager initialization."""
        custom_timeout = 7200
        custom_max_sessions = 10
        
        manager = SessionManager(
            redis_client=mock_redis,
            audit_logger=mock_audit_logger,
            default_timeout=custom_timeout,
            max_concurrent_sessions=custom_max_sessions
        )
        
        assert manager.redis == mock_redis
        assert manager.audit_logger == mock_audit_logger
        assert manager.default_timeout == custom_timeout
        assert manager.max_concurrent_sessions == custom_max_sessions
        assert manager.cleanup_interval == 300
        assert manager.session_prefix == "session:"
        assert manager.user_sessions_prefix == "user_sessions:"
        assert manager.session_config_key == "session_config"