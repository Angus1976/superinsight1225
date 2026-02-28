"""
Test Redis isolation utilities for SuperInsight testing.

This module provides:
- Separate Redis instance configuration for testing (port 6380)
- Redis connection manager for tests
- Keyspace isolation strategy using prefixes
- Automatic cleanup after tests
- Connection pooling management
- Prevention of production Redis access

Requirements: 12.3
"""

import os
import logging
from typing import Generator, Optional, List
from contextlib import contextmanager
from redis import Redis, ConnectionPool
from redis.client import Redis as RedisClient

logger = logging.getLogger(__name__)


# =============================================================================
# Test Redis Configuration
# =============================================================================

class TestRedisConfig:
    """Configuration for test Redis isolation."""
    
    # Test Redis connection settings
    REDIS_HOST = os.getenv("TEST_REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("TEST_REDIS_PORT", "6380"))
    REDIS_DB = int(os.getenv("TEST_REDIS_DB", "15"))  # Separate database for tests
    
    # Key prefix for test isolation
    KEY_PREFIX = "superinsight:test:"
    
    # Connection pool settings for tests
    MAX_CONNECTIONS = int(os.getenv("TEST_REDIS_MAX_CONNECTIONS", "10"))
    SOCKET_CONNECT_TIMEOUT = 1  # Short timeout for fast failure
    SOCKET_KEEPALIVE = True
    
    @classmethod
    def get_url(cls) -> str:
        """Get Redis URL for test instance."""
        return f"redis://{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"
    
    @classmethod
    def get_key_prefix(cls) -> str:
        """Get key prefix for test isolation."""
        return cls.KEY_PREFIX


# =============================================================================
# Test Redis Connection Pool
# =============================================================================

_test_redis_pool: Optional[ConnectionPool] = None


def get_test_redis_pool() -> ConnectionPool:
    """
    Get or create the test Redis connection pool.
    
    Returns:
        Connection pool for test Redis instance
    """
    global _test_redis_pool
    
    if _test_redis_pool is None:
        _test_redis_pool = ConnectionPool(
            host=TestRedisConfig.REDIS_HOST,
            port=TestRedisConfig.REDIS_PORT,
            db=TestRedisConfig.REDIS_DB,
            max_connections=TestRedisConfig.MAX_CONNECTIONS,
            socket_connect_timeout=TestRedisConfig.SOCKET_CONNECT_TIMEOUT,
            socket_keepalive=TestRedisConfig.SOCKET_KEEPALIVE,
            decode_responses=True,
        )
        logger.info(f"Created test Redis connection pool (host={TestRedisConfig.REDIS_HOST}, port={TestRedisConfig.REDIS_PORT}, db={TestRedisConfig.REDIS_DB})")
    
    return _test_redis_pool


def dispose_test_redis_pool():
    """Dispose of the test Redis connection pool."""
    global _test_redis_pool
    
    if _test_redis_pool is not None:
        _test_redis_pool.disconnect()
        _test_redis_pool = None
        logger.info("Disposed test Redis connection pool")


# =============================================================================
# Test Redis Client Factory
# =============================================================================

class TestRedisClientFactory:
    """Factory for creating test Redis clients with proper isolation."""
    
    @staticmethod
    def create_client() -> RedisClient:
        """
        Create a Redis client for testing.
        
        Uses connection pool for better performance and resource management.
        Uses separate database (db=15) for test isolation.
        
        Returns:
            Redis client connected to test instance
        """
        client = Redis(
            host=TestRedisConfig.REDIS_HOST,
            port=TestRedisConfig.REDIS_PORT,
            db=TestRedisConfig.REDIS_DB,
            socket_connect_timeout=TestRedisConfig.SOCKET_CONNECT_TIMEOUT,
            decode_responses=True,
        )
        
        logger.info(f"Created test Redis client (host={TestRedisConfig.REDIS_HOST}, port={TestRedisConfig.REDIS_PORT}, db={TestRedisConfig.REDIS_DB})")
        return client
    
    @staticmethod
    def create_client_from_pool() -> RedisClient:
        """
        Create a Redis client from the connection pool.
        
        More efficient for parallel test execution.
        
        Returns:
            Redis client from pool
        """
        pool = get_test_redis_pool()
        return Redis(connection_pool=pool)
    
    @staticmethod
    def create_isolated_client(key_prefix: str = None) -> RedisClient:
        """
        Create a Redis client with key prefix isolation.
        
        All keys set by this client will be prefixed for easy cleanup.
        
        Args:
            key_prefix: Prefix to use for all keys (default: from TestRedisConfig)
        
        Returns:
            Redis client with key prefix wrapper
        """
        client = TestRedisClientFactory.create_client()
        prefix = key_prefix or TestRedisConfig.get_key_prefix()
        
        # Wrap the client to automatically prefix keys
        return PrefixedRedisClient(client, prefix)


class PrefixedRedisClient:
    """
    Redis client wrapper that automatically prefixes all keys.
    
    Provides keyspace isolation by ensuring all keys have a test-specific prefix.
    """
    
    def __init__(self, client: RedisClient, prefix: str):
        self._client = client
        self._prefix = prefix
    
    def _prefix_key(self, key: str) -> str:
        """Add prefix to a key."""
        if key.startswith(self._prefix):
            return key
        return f"{self._prefix}{key}"
    
    def _prefix_keys(self, keys: List[str]) -> List[str]:
        """Add prefix to multiple keys."""
        return [self._prefix_key(k) for k in keys]
    
    def get(self, key: str, *args, **kwargs):
        """Get a value with key prefixing."""
        return self._client.get(self._prefix_key(key), *args, **kwargs)
    
    def set(self, key: str, value, *args, **kwargs):
        """Set a value with key prefixing."""
        return self._client.set(self._prefix_key(key), value, *args, **kwargs)
    
    def delete(self, *keys: str, **kwargs):
        """Delete keys with prefixing."""
        return self._client.delete(*self._prefix_keys(list(keys)), **kwargs)
    
    def keys(self, pattern: str = "*", **kwargs):
        """Get keys with prefixing."""
        prefixed_pattern = self._prefix_key(pattern) if not pattern.startswith(self._prefix) else pattern
        return self._client.keys(prefixed_pattern, **kwargs)
    
    def exists(self, *keys: str, **kwargs):
        """Check if keys exist with prefixing."""
        return self._client.exists(*self._prefix_keys(list(keys)), **kwargs)
    
    def expire(self, key: str, seconds: int, **kwargs):
        """Set expiration with key prefixing."""
        return self._client.expire(self._prefix_key(key), seconds, **kwargs)
    
    def incr(self, key: str, amount: int = 1, **kwargs):
        """Increment with key prefixing."""
        return self._client.incr(self._prefix_key(key), amount, **kwargs)
    
    def decr(self, key: str, amount: int = 1, **kwargs):
        """Decrement with key prefixing."""
        return self._client.decr(self._prefix_key(key), amount, **kwargs)
    
    def hget(self, name: str, key: str, **kwargs):
        """Get hash field with key prefixing."""
        return self._client.hget(self._prefix_key(name), key, **kwargs)
    
    def hset(self, name: str, key: str, value, **kwargs):
        """Set hash field with key prefixing."""
        return self._client.hset(self._prefix_key(name), key, value, **kwargs)
    
    def hgetall(self, name: str, **kwargs):
        """Get all hash fields with key prefixing."""
        return self._client.hgetall(self._prefix_key(name), **kwargs)
    
    def lpush(self, name: str, *values, **kwargs):
        """Push to list with key prefixing."""
        return self._client.lpush(self._prefix_key(name), *values, **kwargs)
    
    def lrange(self, name: str, start: int, end: int, **kwargs):
        """Get list range with key prefixing."""
        return self._client.lrange(self._prefix_key(name), start, end, **kwargs)
    
    def sadd(self, name: str, *values, **kwargs):
        """Add to set with key prefixing."""
        return self._client.sadd(self._prefix_key(name), *values, **kwargs)
    
    def smembers(self, name: str, **kwargs):
        """Get set members with key prefixing."""
        return self._client.smembers(self._prefix_key(name), **kwargs)
    
    def zadd(self, name: str, mapping: dict, **kwargs):
        """Add to sorted set with key prefixing."""
        return self._client.zadd(self._prefix_key(name), mapping, **kwargs)
    
    def zrange(self, name: str, start: int, end: int, **kwargs):
        """Get sorted set range with key prefixing."""
        return self._client.zrange(self._prefix_key(name), start, end, **kwargs)
    
    def ping(self, **kwargs):
        """Ping Redis server."""
        return self._client.ping(**kwargs)
    
    def flushdb(self, **kwargs):
        """Flush the test database."""
        return self._client.flushdb(**kwargs)
    
    def close(self):
        """Close the client connection."""
        return self._client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup test keys."""
        self._cleanup_test_keys()
        self.close()
        return False
    
    def _cleanup_test_keys(self):
        """Clean up all keys with the test prefix."""
        try:
            pattern = f"{self._prefix}*"
            keys = self._client.keys(pattern)
            if keys:
                self._client.delete(*keys)
                logger.info(f"Cleaned up {len(keys)} test keys with prefix '{self._prefix}'")
        except Exception as e:
            logger.error(f"Failed to cleanup test keys: {e}")


# =============================================================================
# Keyspace Isolation Strategy
# =============================================================================

class RedisKeyspaceIsolator:
    """
    Provides keyspace isolation for Redis tests.
    
    Strategy:
    1. Use separate Redis database (db=15) for tests
    2. Use key prefix for all test data
    3. Automatic cleanup after each test
    4. Session-level flushdb for complete cleanup
    """
    
    def __init__(self, client: RedisClient):
        self._client = client
        self._prefix = TestRedisConfig.get_key_prefix()
        self._created_keys: List[str] = []
    
    def set_test_key(self, key: str, value: str, ttl: int = None) -> None:
        """
        Set a test key with automatic prefix and tracking.
        
        Args:
            key: Key name (without prefix)
            value: Value to store
            ttl: Optional TTL in seconds
        """
        prefixed_key = self._prefix_key(key)
        self._created_keys.append(prefixed_key)
        
        if ttl:
            self._client.setex(prefixed_key, ttl, value)
        else:
            self._client.set(prefixed_key, value)
    
    def get_test_key(self, key: str) -> Optional[str]:
        """
        Get a test key with automatic prefix resolution.
        
        Args:
            key: Key name (without prefix)
        
        Returns:
            Value or None if key doesn't exist
        """
        return self._client.get(self._prefix_key(key))
    
    def delete_test_key(self, key: str) -> int:
        """
        Delete a test key with automatic prefix resolution.
        
        Args:
            key: Key name (without prefix)
        
        Returns:
            Number of keys deleted
        """
        prefixed_key = self._prefix_key(key)
        if prefixed_key in self._created_keys:
            self._created_keys.remove(prefixed_key)
        return self._client.delete(prefixed_key)
    
    def cleanup_test_keys(self) -> int:
        """
        Clean up all tracked test keys.
        
        Returns:
            Number of keys deleted
        """
        deleted_count = 0
        for key in self._created_keys:
            try:
                self._client.delete(key)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete test key {key}: {e}")
        
        self._created_keys.clear()
        logger.info(f"Cleaned up {deleted_count} test keys")
        return deleted_count
    
    def cleanup_all_test_keys(self) -> int:
        """
        Clean up ALL keys with test prefix (not just tracked ones).
        
        Returns:
            Number of keys deleted
        """
        pattern = f"{self._prefix}*"
        keys = self._client.keys(pattern)
        
        if keys:
            deleted_count = self._client.delete(*keys)
            logger.info(f"Cleaned up {deleted_count} test keys with prefix '{self._prefix}'")
            return deleted_count
        
        return 0
    
    def _prefix_key(self, key: str) -> str:
        """Add prefix to a key."""
        if key.startswith(self._prefix):
            return key
        return f"{self._prefix}{key}"
    
    def get_tracked_keys(self) -> List[str]:
        """Get list of tracked keys."""
        return self._created_keys.copy()


# =============================================================================
# Redis Test Cleanup Utilities
# =============================================================================

class RedisTestCleanupManager:
    """
    Manages cleanup of test data from Redis.
    
    Provides utilities for:
    - Flushing test database
    - Deleting keys by pattern
    - Verifying clean state
    """
    
    def __init__(self, client: RedisClient):
        self._client = client
        self._prefix = TestRedisConfig.get_key_prefix()
    
    def flush_test_database(self) -> bool:
        """
        Flush the entire test database.
        
        Warning: This is a destructive operation. Only use in test environments.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._client.flushdb()
            logger.info("Flushed test Redis database")
            return True
        except Exception as e:
            logger.error(f"Failed to flush test database: {e}")
            return False
    
    def delete_keys_by_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Key pattern (e.g., "test:*", "session:*")
        
        Returns:
            Number of keys deleted
        """
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to delete keys by pattern {pattern}: {e}")
            return 0
    
    def delete_test_prefix_keys(self) -> int:
        """
        Delete all keys with the test prefix.
        
        Returns:
            Number of keys deleted
        """
        return self.delete_keys_by_pattern(f"{self._prefix}*")
    
    def verify_clean_state(self) -> bool:
        """
        Verify that the test database is in a clean state.
        
        Returns:
            True if no test keys remain, False otherwise
        """
        try:
            pattern = f"{self._prefix}*"
            keys = self._client.keys(pattern)
            
            if keys:
                logger.warning(f"Found {len(keys)} remaining test keys")
                return False
            
            logger.info("Redis test database is in clean state")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify clean state: {e}")
            return False
    
    def get_test_key_count(self) -> int:
        """
        Get the count of test keys in the database.
        
        Returns:
            Number of test keys
        """
        try:
            pattern = f"{self._prefix}*"
            keys = self._client.keys(pattern)
            return len(keys)
        except Exception as e:
            logger.error(f"Failed to count test keys: {e}")
            return -1


# =============================================================================
# Production Redis Access Prevention
# =============================================================================

def prevent_production_redis_access():
    """
    Verify that tests are not accessing production Redis.
    
    Raises:
        RuntimeError: If production Redis access is detected
    """
    # Check environment
    app_env = os.getenv("APP_ENV", "development")
    if app_env == "production":
        raise RuntimeError(
            "Tests cannot run in production environment. "
            "Set APP_ENV=test to run tests."
        )
    
    # Check Redis URL
    redis_url = os.getenv("REDIS_URL", "")
    
    # List of patterns that indicate production Redis
    production_patterns = [
        "prod",
        "production",
        "redis.amazonaws.com",  # AWS ElastiCache
        "redis.cache.com",  # Azure Cache for Redis
        "memorystore.googleapis.com",  # GCP Memorystore
    ]
    
    for pattern in production_patterns:
        if pattern in redis_url.lower():
            raise RuntimeError(
                f"Tests cannot access production Redis. "
                f"REDIS_URL contains '{pattern}'. "
                f"Use a separate test Redis instance."
            )
    
    # Verify we're using test configuration
    if "6380" not in redis_url and "6381" not in redis_url:
        logger.warning(
            f"REDIS_URL does not use test port (6380). "
            f"Current: {redis_url}. "
            f"Tests should use redis://localhost:6380/15"
        )
    
    logger.info("Production Redis access prevention check passed")


# =============================================================================
# Context Manager for Isolated Redis Operations
# =============================================================================

@contextmanager
def isolated_redis_session(client: RedisClient = None) -> Generator[RedisClient, None, None]:
    """
    Context manager for isolated Redis test operations.
    
    Provides automatic cleanup of test keys after the context exits.
    
    Usage:
        with isolated_redis_session() as redis:
            redis.set("test:key", "value")
            # Test code here
            # All test keys will be cleaned up automatically
    
    Args:
        client: Redis client to use (creates new client if not provided)
    
    Yields:
        Redis client with automatic cleanup
    """
    if client is None:
        client = TestRedisClientFactory.create_client()
        should_close = True
    else:
        should_close = False
    
    try:
        yield client
    finally:
        # Cleanup test keys
        try:
            prefix = TestRedisConfig.get_key_prefix()
            pattern = f"{prefix}*"
            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)
                logger.info(f"Cleaned up {len(keys)} test keys")
        except Exception as e:
            logger.error(f"Failed to cleanup test keys: {e}")
        
        if should_close:
            client.close()


# =============================================================================
# Test Redis Setup and Teardown
# =============================================================================

def setup_test_redis():
    """
    Set up test Redis connection.
    
    Verifies connection and logs status.
    """
    try:
        client = TestRedisClientFactory.create_client()
        client.ping()
        logger.info("Test Redis connection established")
        client.close()
    except Exception as e:
        logger.error(f"Failed to connect to test Redis: {e}")
        raise


def teardown_test_redis():
    """
    Tear down test Redis connection pool.
    
    Disposes of the connection pool.
    """
    dispose_test_redis_pool()
    logger.info("Test Redis connection pool disposed")


def cleanup_test_redis(client: RedisClient):
    """
    Clean up test Redis data.
    
    Args:
        client: Redis client to use for cleanup
    """
    cleanup_manager = RedisTestCleanupManager(client)
    cleanup_manager.delete_test_prefix_keys()