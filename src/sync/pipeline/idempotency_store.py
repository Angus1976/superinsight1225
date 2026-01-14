"""
Idempotency Store for Data Sync Pipeline.

Manages idempotency keys to prevent duplicate data processing.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class IdempotencyStore:
    """
    Store for managing idempotency keys.
    
    Supports both in-memory and Redis-backed storage.
    """
    
    def __init__(self, redis_client=None, ttl_hours: int = 24):
        """
        Initialize the idempotency store.
        
        Args:
            redis_client: Optional Redis client for distributed storage.
                         If None, uses in-memory storage.
            ttl_hours: Time-to-live for idempotency keys in hours (default 24)
        """
        self.redis_client = redis_client
        self.ttl_hours = ttl_hours
        self._memory_store: Dict[str, datetime] = {}
    
    async def exists(self, key: str) -> bool:
        """
        Check if an idempotency key exists.
        
        Args:
            key: Idempotency key to check
            
        Returns:
            True if key exists and is not expired
        """
        if self.redis_client:
            return await self._exists_in_redis(key)
        
        if key in self._memory_store:
            # Check if expired
            stored_at = self._memory_store[key]
            if datetime.utcnow() - stored_at < timedelta(hours=self.ttl_hours):
                return True
            else:
                # Clean up expired key
                del self._memory_store[key]
        
        return False
    
    async def save(self, key: str) -> None:
        """
        Save an idempotency key.
        
        Args:
            key: Idempotency key to save
        """
        if self.redis_client:
            await self._save_to_redis(key)
        else:
            self._memory_store[key] = datetime.utcnow()
        
        logger.debug(f"Saved idempotency key: {key}")
    
    async def delete(self, key: str) -> bool:
        """
        Delete an idempotency key.
        
        Args:
            key: Idempotency key to delete
            
        Returns:
            True if deleted, False if not found
        """
        if self.redis_client:
            return await self._delete_from_redis(key)
        
        if key in self._memory_store:
            del self._memory_store[key]
            return True
        return False
    
    async def cleanup_expired(self) -> int:
        """
        Clean up expired idempotency keys.
        
        Returns:
            Number of keys cleaned up
        """
        if self.redis_client:
            # Redis handles TTL automatically
            return 0
        
        now = datetime.utcnow()
        expired_keys = [
            key for key, stored_at in self._memory_store.items()
            if now - stored_at >= timedelta(hours=self.ttl_hours)
        ]
        
        for key in expired_keys:
            del self._memory_store[key]
        
        return len(expired_keys)
    
    async def _exists_in_redis(self, key: str) -> bool:
        """Check if key exists in Redis."""
        result = await self.redis_client.exists(f"idempotency:{key}")
        return result > 0
    
    async def _save_to_redis(self, key: str) -> None:
        """Save key to Redis with TTL."""
        await self.redis_client.setex(
            f"idempotency:{key}",
            timedelta(hours=self.ttl_hours),
            "1"
        )
    
    async def _delete_from_redis(self, key: str) -> bool:
        """Delete key from Redis."""
        result = await self.redis_client.delete(f"idempotency:{key}")
        return result > 0
    
    def clear_memory(self) -> None:
        """Clear all in-memory keys."""
        self._memory_store.clear()
    
    @property
    def count(self) -> int:
        """Get the number of stored keys (memory store only)."""
        return len(self._memory_store)
