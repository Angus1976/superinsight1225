"""
Redis Cache Schemas for Ontology Expert Collaboration

This module defines Redis key patterns and TTL policies for caching
collaboration sessions, expert presence, templates, and validation rules.

Key Patterns:
- ontology:session:{session_id} - Collaboration session data
- ontology:session:{session_id}:participants - Session participants set
- ontology:session:{session_id}:locks - Element locks hash
- ontology:presence:{session_id}:{user_id} - User presence with heartbeat
- ontology:template:{template_id} - Cached template data
- ontology:templates:industry:{industry} - Template IDs by industry
- ontology:validation:rules:{region}:{industry} - Validation rules cache
- ontology:expert:recommendations:{ontology_area} - Expert recommendations cache
- ontology:pubsub:session:{session_id} - Pub/sub channel for session broadcasts

TTL Policies:
- Sessions: 1 hour (3600 seconds)
- Presence: 5 minutes (300 seconds) - requires heartbeat
- Templates: 1 hour (3600 seconds)
- Validation Rules: 30 minutes (1800 seconds)
- Expert Recommendations: 15 minutes (900 seconds)
- Element Locks: 5 minutes (300 seconds) - configurable per lock
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import json


class CacheKeyPrefix(str, Enum):
    """Redis key prefixes for different cache types."""
    SESSION = "ontology:session"
    PRESENCE = "ontology:presence"
    TEMPLATE = "ontology:template"
    TEMPLATES_BY_INDUSTRY = "ontology:templates:industry"
    VALIDATION_RULES = "ontology:validation:rules"
    EXPERT_RECOMMENDATIONS = "ontology:expert:recommendations"
    PUBSUB_SESSION = "ontology:pubsub:session"
    ELEMENT_LOCK = "ontology:lock"


class CacheTTL(int, Enum):
    """TTL values in seconds for different cache types."""
    SESSION = 3600  # 1 hour
    PRESENCE = 300  # 5 minutes
    TEMPLATE = 3600  # 1 hour
    VALIDATION_RULES = 1800  # 30 minutes
    EXPERT_RECOMMENDATIONS = 900  # 15 minutes
    ELEMENT_LOCK = 300  # 5 minutes (default)


@dataclass
class RedisKeyBuilder:
    """Builder for Redis cache keys."""
    
    @staticmethod
    def session(session_id: str) -> str:
        """Get key for session data."""
        return f"{CacheKeyPrefix.SESSION}:{session_id}"
    
    @staticmethod
    def session_participants(session_id: str) -> str:
        """Get key for session participants set."""
        return f"{CacheKeyPrefix.SESSION}:{session_id}:participants"
    
    @staticmethod
    def session_locks(session_id: str) -> str:
        """Get key for session element locks hash."""
        return f"{CacheKeyPrefix.SESSION}:{session_id}:locks"
    
    @staticmethod
    def presence(session_id: str, user_id: str) -> str:
        """Get key for user presence."""
        return f"{CacheKeyPrefix.PRESENCE}:{session_id}:{user_id}"
    
    @staticmethod
    def template(template_id: str) -> str:
        """Get key for cached template."""
        return f"{CacheKeyPrefix.TEMPLATE}:{template_id}"
    
    @staticmethod
    def templates_by_industry(industry: str) -> str:
        """Get key for template IDs by industry."""
        return f"{CacheKeyPrefix.TEMPLATES_BY_INDUSTRY}:{industry}"
    
    @staticmethod
    def validation_rules(region: str, industry: str) -> str:
        """Get key for validation rules cache."""
        return f"{CacheKeyPrefix.VALIDATION_RULES}:{region}:{industry}"
    
    @staticmethod
    def expert_recommendations(ontology_area: str) -> str:
        """Get key for expert recommendations cache."""
        return f"{CacheKeyPrefix.EXPERT_RECOMMENDATIONS}:{ontology_area}"
    
    @staticmethod
    def pubsub_channel(session_id: str) -> str:
        """Get pub/sub channel for session broadcasts."""
        return f"{CacheKeyPrefix.PUBSUB_SESSION}:{session_id}"
    
    @staticmethod
    def element_lock(session_id: str, element_id: str) -> str:
        """Get key for element lock."""
        return f"{CacheKeyPrefix.ELEMENT_LOCK}:{session_id}:{element_id}"


@dataclass
class SessionCacheData:
    """Data structure for cached session."""
    session_id: str
    ontology_id: str
    created_by: str
    status: str
    created_at: str
    metadata: Optional[dict] = None
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "session_id": self.session_id,
            "ontology_id": self.ontology_id,
            "created_by": self.created_by,
            "status": self.status,
            "created_at": self.created_at,
            "metadata": self.metadata or {}
        })
    
    @classmethod
    def from_json(cls, data: str) -> "SessionCacheData":
        """Deserialize from JSON string."""
        parsed = json.loads(data)
        return cls(**parsed)


@dataclass
class PresenceCacheData:
    """Data structure for cached user presence."""
    user_id: str
    session_id: str
    user_name: str
    last_heartbeat: str
    cursor_position: Optional[dict] = None
    active_element: Optional[str] = None
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "user_id": self.user_id,
            "session_id": self.session_id,
            "user_name": self.user_name,
            "last_heartbeat": self.last_heartbeat,
            "cursor_position": self.cursor_position,
            "active_element": self.active_element
        })
    
    @classmethod
    def from_json(cls, data: str) -> "PresenceCacheData":
        """Deserialize from JSON string."""
        parsed = json.loads(data)
        return cls(**parsed)


@dataclass
class ElementLockCacheData:
    """Data structure for cached element lock."""
    element_id: str
    locked_by: str
    locked_by_name: str
    locked_at: str
    expires_at: str
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "element_id": self.element_id,
            "locked_by": self.locked_by,
            "locked_by_name": self.locked_by_name,
            "locked_at": self.locked_at,
            "expires_at": self.expires_at
        })
    
    @classmethod
    def from_json(cls, data: str) -> "ElementLockCacheData":
        """Deserialize from JSON string."""
        parsed = json.loads(data)
        return cls(**parsed)


@dataclass
class BroadcastMessage:
    """Data structure for pub/sub broadcast messages."""
    message_type: str  # change, lock, unlock, presence, cursor
    session_id: str
    sender_id: str
    payload: dict
    timestamp: str
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "message_type": self.message_type,
            "session_id": self.session_id,
            "sender_id": self.sender_id,
            "payload": self.payload,
            "timestamp": self.timestamp
        })
    
    @classmethod
    def from_json(cls, data: str) -> "BroadcastMessage":
        """Deserialize from JSON string."""
        parsed = json.loads(data)
        return cls(**parsed)


# Redis Lua scripts for atomic operations

LOCK_ELEMENT_SCRIPT = """
-- Atomic element lock acquisition
-- KEYS[1] = lock key
-- ARGV[1] = lock data JSON
-- ARGV[2] = TTL in seconds
-- Returns: 1 if lock acquired, 0 if already locked by another user

local existing = redis.call('GET', KEYS[1])
if existing then
    local lock_data = cjson.decode(existing)
    local new_data = cjson.decode(ARGV[1])
    if lock_data.locked_by == new_data.locked_by then
        -- Same user, extend lock
        redis.call('SETEX', KEYS[1], ARGV[2], ARGV[1])
        return 1
    else
        -- Different user, lock exists
        return 0
    end
else
    -- No existing lock, acquire
    redis.call('SETEX', KEYS[1], ARGV[2], ARGV[1])
    return 1
end
"""

UNLOCK_ELEMENT_SCRIPT = """
-- Atomic element unlock
-- KEYS[1] = lock key
-- ARGV[1] = user_id requesting unlock
-- Returns: 1 if unlocked, 0 if not locked or locked by another user

local existing = redis.call('GET', KEYS[1])
if existing then
    local lock_data = cjson.decode(existing)
    if lock_data.locked_by == ARGV[1] then
        redis.call('DEL', KEYS[1])
        return 1
    else
        return 0
    end
else
    return 1  -- Already unlocked
end
"""

HEARTBEAT_SCRIPT = """
-- Atomic presence heartbeat update
-- KEYS[1] = presence key
-- ARGV[1] = presence data JSON
-- ARGV[2] = TTL in seconds
-- Returns: 1 always

redis.call('SETEX', KEYS[1], ARGV[2], ARGV[1])
return 1
"""


def get_redis_scripts() -> dict:
    """Get all Lua scripts for Redis operations."""
    return {
        "lock_element": LOCK_ELEMENT_SCRIPT,
        "unlock_element": UNLOCK_ELEMENT_SCRIPT,
        "heartbeat": HEARTBEAT_SCRIPT
    }
