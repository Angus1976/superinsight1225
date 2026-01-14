"""
Session Manager for SuperInsight Platform.

Manages user sessions with Redis backend, concurrent session limits, and timeout configuration.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4
from dataclasses import dataclass, field

import redis.asyncio as redis

from src.security.audit_logger import AuditLogger


@dataclass
class Session:
    """User session data structure."""
    id: str
    user_id: str
    ip_address: str
    user_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            ip_address=data["ip_address"],
            user_agent=data.get("user_agent"),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            metadata=data.get("metadata", {})
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    @property
    def time_until_expiry(self) -> Optional[timedelta]:
        """Get time until session expires."""
        if self.expires_at:
            return self.expires_at - datetime.utcnow()
        return None


class SessionManager:
    """
    Session manager with Redis backend.
    
    Provides session creation, validation, destruction, and management
    with support for concurrent session limits and configurable timeouts.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        audit_logger: AuditLogger,
        default_timeout: int = 3600,  # 1 hour
        max_concurrent_sessions: int = 5
    ):
        self.redis = redis_client
        self.audit_logger = audit_logger
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.default_timeout = default_timeout
        self.max_concurrent_sessions = max_concurrent_sessions
        self.cleanup_interval = 300  # 5 minutes
        
        # Redis key prefixes
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"
        self.session_config_key = "session_config"
    
    async def create_session(
        self,
        user_id: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Create a new user session.
        
        Args:
            user_id: User identifier
            ip_address: Client IP address
            user_agent: Client user agent (optional)
            timeout: Session timeout in seconds (optional, uses default)
            metadata: Additional session metadata (optional)
            
        Returns:
            Created Session object
        """
        session_timeout = timeout or self.default_timeout
        
        # Check concurrent session limit
        current_sessions = await self.get_user_sessions(user_id)
        
        if len(current_sessions) >= self.max_concurrent_sessions:
            # Remove oldest session
            oldest_session = min(current_sessions, key=lambda s: s.created_at)
            await self.destroy_session(oldest_session.id)
            self.logger.info(f"Removed oldest session {oldest_session.id} due to concurrent limit")
        
        # Create new session
        session_id = str(uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=session_timeout)
        
        session = Session(
            id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            last_activity=now,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        # Store session in Redis
        session_key = f"{self.session_prefix}{session_id}"
        await self.redis.setex(
            session_key,
            session_timeout,
            json.dumps(session.to_dict(), default=str)
        )
        
        # Add to user's session list
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        await self.redis.sadd(user_sessions_key, session_id)
        await self.redis.expire(user_sessions_key, session_timeout + 300)  # Extra buffer
        
        # Log session creation
        await self.audit_logger.log(
            event_type="session_created",
            user_id=user_id,
            ip_address=ip_address,
            details={
                "session_id": session_id,
                "user_agent": user_agent,
                "timeout": session_timeout
            }
        )
        
        self.logger.info(f"Created session {session_id} for user {user_id}")
        
        return session
    
    async def validate_session(self, session_id: str) -> Optional[Session]:
        """
        Validate and refresh a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object if valid, None if invalid or expired
        """
        session_key = f"{self.session_prefix}{session_id}"
        
        # Get session data from Redis
        session_data = await self.redis.get(session_key)
        if not session_data:
            return None
        
        try:
            session_dict = json.loads(session_data)
            session = Session.from_dict(session_dict)
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Invalid session data for {session_id}: {e}")
            await self.destroy_session(session_id)
            return None
        
        # Check if session is expired
        if session.is_expired:
            await self.destroy_session(session_id)
            return None
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        
        # Refresh session in Redis
        ttl = await self.redis.ttl(session_key)
        if ttl > 0:
            await self.redis.setex(
                session_key,
                ttl,
                json.dumps(session.to_dict(), default=str)
            )
        
        return session
    
    async def destroy_session(self, session_id: str) -> bool:
        """
        Destroy a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was destroyed, False if not found
        """
        session_key = f"{self.session_prefix}{session_id}"
        
        # Get session data before deletion for logging
        session_data = await self.redis.get(session_key)
        if not session_data:
            return False
        
        try:
            session_dict = json.loads(session_data)
            user_id = session_dict["user_id"]
        except (json.JSONDecodeError, KeyError):
            user_id = "unknown"
        
        # Remove from Redis
        await self.redis.delete(session_key)
        
        # Remove from user's session list
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        await self.redis.srem(user_sessions_key, session_id)
        
        # Log session destruction
        await self.audit_logger.log(
            event_type="session_destroyed",
            user_id=user_id,
            details={"session_id": session_id}
        )
        
        self.logger.info(f"Destroyed session {session_id}")
        
        return True
    
    async def force_logout(self, user_id: str) -> int:
        """
        Force logout all sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of sessions destroyed
        """
        sessions = await self.get_user_sessions(user_id)
        
        destroyed_count = 0
        for session in sessions:
            if await self.destroy_session(session.id):
                destroyed_count += 1
        
        # Log force logout
        await self.audit_logger.log(
            event_type="force_logout",
            user_id=user_id,
            details={"sessions_destroyed": destroyed_count}
        )
        
        self.logger.info(f"Force logout for user {user_id}: {destroyed_count} sessions destroyed")
        
        return destroyed_count
    
    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of active Session objects
        """
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        session_ids = await self.redis.smembers(user_sessions_key)
        
        sessions = []
        for session_id in session_ids:
            session_key = f"{self.session_prefix}{session_id.decode()}"
            session_data = await self.redis.get(session_key)
            
            if session_data:
                try:
                    session_dict = json.loads(session_data)
                    session = Session.from_dict(session_dict)
                    
                    # Check if session is expired
                    if not session.is_expired:
                        sessions.append(session)
                    else:
                        # Clean up expired session
                        await self.destroy_session(session.id)
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.error(f"Invalid session data: {e}")
                    # Clean up invalid session
                    await self.redis.srem(user_sessions_key, session_id)
        
        return sessions
    
    async def get_active_sessions(self, limit: int = 100) -> List[Session]:
        """
        Get all active sessions (admin function).
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of active Session objects
        """
        # Get all session keys
        session_keys = await self.redis.keys(f"{self.session_prefix}*")
        
        sessions = []
        for session_key in session_keys[:limit]:
            session_data = await self.redis.get(session_key)
            
            if session_data:
                try:
                    session_dict = json.loads(session_data)
                    session = Session.from_dict(session_dict)
                    
                    if not session.is_expired:
                        sessions.append(session)
                except (json.JSONDecodeError, KeyError):
                    continue
        
        return sessions
    
    async def configure_timeout(self, timeout_seconds: int) -> None:
        """
        Configure default session timeout.
        
        Args:
            timeout_seconds: Timeout in seconds
        """
        self.default_timeout = timeout_seconds
        
        # Store configuration in Redis
        config = {
            "default_timeout": timeout_seconds,
            "max_concurrent_sessions": self.max_concurrent_sessions,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await self.redis.set(
            self.session_config_key,
            json.dumps(config)
        )
        
        self.logger.info(f"Updated session timeout to {timeout_seconds} seconds")
    
    async def configure_max_concurrent(self, max_sessions: int) -> None:
        """
        Configure maximum concurrent sessions per user.
        
        Args:
            max_sessions: Maximum concurrent sessions
        """
        self.max_concurrent_sessions = max_sessions
        
        # Store configuration in Redis
        config = {
            "default_timeout": self.default_timeout,
            "max_concurrent_sessions": max_sessions,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await self.redis.set(
            self.session_config_key,
            json.dumps(config)
        )
        
        self.logger.info(f"Updated max concurrent sessions to {max_sessions}")
    
    async def extend_session(self, session_id: str, additional_seconds: int) -> bool:
        """
        Extend session timeout.
        
        Args:
            session_id: Session identifier
            additional_seconds: Additional seconds to add to timeout
            
        Returns:
            True if extended successfully, False if session not found
        """
        session_key = f"{self.session_prefix}{session_id}"
        
        # Check if session exists
        if not await self.redis.exists(session_key):
            return False
        
        # Extend TTL
        current_ttl = await self.redis.ttl(session_key)
        if current_ttl > 0:
            new_ttl = current_ttl + additional_seconds
            await self.redis.expire(session_key, new_ttl)
            
            self.logger.info(f"Extended session {session_id} by {additional_seconds} seconds")
            return True
        
        return False
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (maintenance function).
        
        Returns:
            Number of sessions cleaned up
        """
        # Get all session keys
        session_keys = await self.redis.keys(f"{self.session_prefix}*")
        
        cleaned_count = 0
        for session_key in session_keys:
            session_data = await self.redis.get(session_key)
            
            if session_data:
                try:
                    session_dict = json.loads(session_data)
                    session = Session.from_dict(session_dict)
                    
                    if session.is_expired:
                        await self.destroy_session(session.id)
                        cleaned_count += 1
                except (json.JSONDecodeError, KeyError):
                    # Clean up invalid session data
                    await self.redis.delete(session_key)
                    cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} expired sessions")
        
        return cleaned_count
    
    async def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Returns:
            Dictionary with session statistics
        """
        # Count total active sessions
        session_keys = await self.redis.keys(f"{self.session_prefix}*")
        total_sessions = len(session_keys)
        
        # Count sessions by user (top 10)
        user_session_counts = {}
        user_keys = await self.redis.keys(f"{self.user_sessions_prefix}*")
        
        for user_key in user_keys:
            user_id = user_key.decode().replace(self.user_sessions_prefix, "")
            session_count = await self.redis.scard(user_key)
            user_session_counts[user_id] = session_count
        
        # Sort by session count
        top_users = sorted(
            user_session_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "total_active_sessions": total_sessions,
            "total_users_with_sessions": len(user_session_counts),
            "top_users_by_sessions": dict(top_users),
            "configuration": {
                "default_timeout": self.default_timeout,
                "max_concurrent_sessions": self.max_concurrent_sessions
            }
        }