"""
Property-based tests for Query Cache module.

Tests Properties 42-45 from text-to-sql-methods specification:
- Property 42: Query-SQL Caching with TTL
- Property 43: Cache Performance
- Property 44: Schema Change Cache Invalidation
- Property 45: LRU Cache Eviction
"""

import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, strategies as st, settings, assume

# Import the module under test
import sys
sys.path.insert(0, str(__file__).replace("\\", "/").rsplit("/tests/", 1)[0] + "/src")

from text_to_sql.query_cache import (
    QueryCache,
    CacheEntry,
    CacheStats,
    CacheConfig,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

@st.composite
def query_strategy(draw) -> str:
    """Generate realistic SQL-like queries."""
    tables = draw(st.sampled_from([
        "users", "orders", "products", "customers", "transactions",
        "inventory", "employees", "departments", "sales", "reports"
    ]))
    columns = draw(st.sampled_from([
        "*", "id", "name", "email", "created_at", "amount", "status",
        "COUNT(*)", "SUM(amount)", "AVG(price)"
    ]))
    condition = draw(st.sampled_from([
        "", " WHERE id = 1", " WHERE status = 'active'",
        " WHERE created_at > '2024-01-01'", " LIMIT 100"
    ]))
    return f"SELECT {columns} FROM {tables}{condition}"


@st.composite
def sql_result_strategy(draw) -> str:
    """Generate SQL result strings."""
    tables = draw(st.sampled_from(["users", "orders", "products"]))
    columns = draw(st.lists(
        st.sampled_from(["id", "name", "email", "amount", "status"]),
        min_size=1, max_size=5, unique=True
    ))
    return f"SELECT {', '.join(columns)} FROM {tables}"


@st.composite
def database_type_strategy(draw) -> str:
    """Generate database type strings."""
    return draw(st.sampled_from([
        "postgresql", "mysql", "oracle", "sqlserver", "sqlite"
    ]))


@st.composite
def schema_hash_strategy(draw) -> str:
    """Generate schema hash strings."""
    content = draw(st.text(min_size=10, max_size=50))
    return hashlib.md5(content.encode()).hexdigest()


@st.composite
def ttl_strategy(draw) -> int:
    """Generate TTL values in seconds."""
    return draw(st.integers(min_value=1, max_value=86400))  # 1 second to 24 hours


@st.composite
def cache_entry_strategy(draw) -> Dict[str, Any]:
    """Generate cache entry data."""
    return {
        "query": draw(query_strategy()),
        "sql": draw(sql_result_strategy()),
        "database_type": draw(database_type_strategy()),
        "schema_hash": draw(schema_hash_strategy()),
        "method_used": draw(st.sampled_from(["llm", "template", "semantic", "hybrid"])),
        "confidence": draw(st.floats(min_value=0.0, max_value=1.0)),
        "ttl_seconds": draw(st.integers(min_value=60, max_value=3600)),
    }


# =============================================================================
# Property 42: Query-SQL Caching with TTL
# =============================================================================

class TestQuerySQLCachingWithTTL:
    """
    Property 42: Query-SQL Caching with TTL

    Validates that:
    1. Cache entries are stored with correct TTL
    2. Entries expire after TTL
    3. Cache hits return correct data before expiration
    4. Cache misses occur after expiration
    """

    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance for each test."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        return QueryCache(config)

    @given(
        query=query_strategy(),
        sql=sql_result_strategy(),
        database_type=database_type_strategy(),
        schema_hash=schema_hash_strategy(),
        ttl=ttl_strategy(),
    )
    @settings(max_examples=50, deadline=None)
    def test_cache_stores_with_ttl(
        self, query: str, sql: str, database_type: str,
        schema_hash: str, ttl: int
    ):
        """Property: Cache entries are stored with specified TTL."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        async def run_test():
            # Store entry with TTL
            key = await cache.set(
                query=query,
                sql=sql,
                database_type=database_type,
                schema_hash=schema_hash,
                method_used="test",
                confidence=0.9,
                ttl_seconds=ttl,
            )

            # Retrieve and verify
            entry = await cache.get(query, database_type, schema_hash)

            assert entry is not None
            assert entry.sql == sql
            assert entry.ttl_seconds == ttl

        asyncio.run(run_test())

    @given(
        query=query_strategy(),
        sql=sql_result_strategy(),
        database_type=database_type_strategy(),
        schema_hash=schema_hash_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_cache_hit_returns_correct_data(
        self, query: str, sql: str, database_type: str, schema_hash: str
    ):
        """Property: Cache hits return the exact data that was stored."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        async def run_test():
            method = "llm_model"
            confidence = 0.85

            # Store
            await cache.set(
                query=query,
                sql=sql,
                database_type=database_type,
                schema_hash=schema_hash,
                method_used=method,
                confidence=confidence,
            )

            # Retrieve
            entry = await cache.get(query, database_type, schema_hash)

            # Verify exact match
            assert entry is not None
            assert entry.sql == sql
            assert entry.method_used == method
            assert entry.confidence == confidence

        asyncio.run(run_test())

    @pytest.mark.asyncio
    async def test_cache_expiration_after_ttl(self):
        """Property: Cache entries expire after TTL."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=1,  # 1 second default TTL
            enable_redis=False,
        )
        cache = QueryCache(config)

        query = "SELECT * FROM users"
        sql = "SELECT id, name FROM users"
        db_type = "postgresql"
        schema_hash = "abc123"

        # Store with short TTL
        await cache.set(
            query=query,
            sql=sql,
            database_type=db_type,
            schema_hash=schema_hash,
            method_used="test",
            confidence=0.9,
            ttl_seconds=1,  # 1 second TTL
        )

        # Verify entry exists
        entry = await cache.get(query, db_type, schema_hash)
        assert entry is not None

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Run cleanup
        await cache.cleanup_expired()

        # Verify entry is gone
        entry = await cache.get(query, db_type, schema_hash)
        assert entry is None

    @given(
        entries=st.lists(cache_entry_strategy(), min_size=1, max_size=10)
    )
    @settings(max_examples=20, deadline=None)
    def test_multiple_entries_independent_ttl(self, entries: List[Dict[str, Any]]):
        """Property: Multiple entries have independent TTLs."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        async def run_test():
            keys = []
            for entry in entries:
                key = await cache.set(**entry)
                keys.append(key)

            # All entries should be retrievable
            for entry in entries:
                result = await cache.get(
                    entry["query"],
                    entry["database_type"],
                    entry["schema_hash"]
                )
                assert result is not None
                assert result.sql == entry["sql"]

        asyncio.run(run_test())


# =============================================================================
# Property 43: Cache Performance
# =============================================================================

class TestCachePerformance:
    """
    Property 43: Cache Performance

    Validates that:
    1. Cache operations complete within time bounds
    2. Cache hit rate improves with repeated queries
    3. Cache statistics are accurate
    """

    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance."""
        config = CacheConfig(
            max_size=10000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        return QueryCache(config)

    @given(
        query=query_strategy(),
        sql=sql_result_strategy(),
        database_type=database_type_strategy(),
        schema_hash=schema_hash_strategy(),
    )
    @settings(max_examples=50, deadline=None)
    def test_cache_set_performance(
        self, query: str, sql: str, database_type: str, schema_hash: str
    ):
        """Property: Cache set operations complete quickly."""
        config = CacheConfig(
            max_size=10000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        async def run_test():
            start = time.time()
            await cache.set(
                query=query,
                sql=sql,
                database_type=database_type,
                schema_hash=schema_hash,
                method_used="test",
                confidence=0.9,
            )
            elapsed = time.time() - start

            # Set should complete in < 10ms for in-memory cache
            assert elapsed < 0.01, f"Cache set took {elapsed:.4f}s"

        asyncio.run(run_test())

    @given(
        query=query_strategy(),
        sql=sql_result_strategy(),
        database_type=database_type_strategy(),
        schema_hash=schema_hash_strategy(),
    )
    @settings(max_examples=50, deadline=None)
    def test_cache_get_performance(
        self, query: str, sql: str, database_type: str, schema_hash: str
    ):
        """Property: Cache get operations complete quickly."""
        config = CacheConfig(
            max_size=10000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        async def run_test():
            # Store first
            await cache.set(
                query=query,
                sql=sql,
                database_type=database_type,
                schema_hash=schema_hash,
                method_used="test",
                confidence=0.9,
            )

            # Time the get
            start = time.time()
            entry = await cache.get(query, database_type, schema_hash)
            elapsed = time.time() - start

            assert entry is not None
            # Get should complete in < 5ms for in-memory cache
            assert elapsed < 0.005, f"Cache get took {elapsed:.4f}s"

        asyncio.run(run_test())

    @pytest.mark.asyncio
    async def test_hit_rate_improves_with_repeated_queries(self):
        """Property: Cache hit rate improves when same queries are repeated."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        queries = [
            ("SELECT * FROM users", "SELECT id, name FROM users"),
            ("SELECT * FROM orders", "SELECT id, amount FROM orders"),
            ("SELECT * FROM products", "SELECT id, price FROM products"),
        ]

        # First pass - all misses, then stores
        for query, sql in queries:
            entry = await cache.get(query, "postgresql", "schema1")
            assert entry is None  # Miss
            await cache.set(
                query=query,
                sql=sql,
                database_type="postgresql",
                schema_hash="schema1",
                method_used="test",
                confidence=0.9,
            )

        # Second pass - all hits
        hits = 0
        for query, _ in queries:
            entry = await cache.get(query, "postgresql", "schema1")
            if entry is not None:
                hits += 1

        # All should be hits now
        assert hits == len(queries)

        # Check statistics
        stats = await cache.get_stats()
        assert stats.hit_rate > 0

    @pytest.mark.asyncio
    async def test_cache_statistics_accuracy(self):
        """Property: Cache statistics accurately reflect operations."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        # Perform known operations
        await cache.set(
            query="q1", sql="s1", database_type="postgresql",
            schema_hash="h1", method_used="test", confidence=0.9
        )
        await cache.set(
            query="q2", sql="s2", database_type="postgresql",
            schema_hash="h1", method_used="test", confidence=0.9
        )

        # 2 hits
        await cache.get("q1", "postgresql", "h1")
        await cache.get("q2", "postgresql", "h1")

        # 2 misses
        await cache.get("q3", "postgresql", "h1")
        await cache.get("q4", "postgresql", "h1")

        stats = await cache.get_stats()

        assert stats.total_entries == 2
        assert stats.hits == 2
        assert stats.misses == 2
        assert stats.hit_rate == 0.5  # 2 hits / 4 total requests


# =============================================================================
# Property 44: Schema Change Cache Invalidation
# =============================================================================

class TestSchemaChangeCacheInvalidation:
    """
    Property 44: Schema Change Cache Invalidation

    Validates that:
    1. Schema changes invalidate relevant cache entries
    2. Entries for unchanged schemas remain valid
    3. Database-type specific invalidation works correctly
    """

    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        return QueryCache(config)

    @given(
        old_schema=schema_hash_strategy(),
        new_schema=schema_hash_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_schema_change_invalidates_entries(
        self, old_schema: str, new_schema: str
    ):
        """Property: Schema changes invalidate cache entries with old schema."""
        assume(old_schema != new_schema)  # Ensure schemas are different

        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        async def run_test():
            # Store entries with old schema
            await cache.set(
                query="SELECT * FROM users",
                sql="SELECT id FROM users",
                database_type="postgresql",
                schema_hash=old_schema,
                method_used="test",
                confidence=0.9,
            )

            # Verify entry exists
            entry = await cache.get("SELECT * FROM users", "postgresql", old_schema)
            assert entry is not None

            # Invalidate by schema change
            invalidated = await cache.invalidate_by_schema(
                database_type="postgresql",
                new_schema_hash=new_schema
            )

            # Entry should be invalidated
            entry = await cache.get("SELECT * FROM users", "postgresql", old_schema)
            assert entry is None

        asyncio.run(run_test())

    @pytest.mark.asyncio
    async def test_unaffected_schemas_remain_valid(self):
        """Property: Entries with unchanged schemas remain valid."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        # Store entries for different database types
        await cache.set(
            query="q1", sql="s1", database_type="postgresql",
            schema_hash="pg_schema", method_used="test", confidence=0.9
        )
        await cache.set(
            query="q2", sql="s2", database_type="mysql",
            schema_hash="mysql_schema", method_used="test", confidence=0.9
        )

        # Invalidate only postgresql
        await cache.invalidate_by_schema("postgresql", "new_pg_schema")

        # MySQL entry should still exist
        entry = await cache.get("q2", "mysql", "mysql_schema")
        assert entry is not None
        assert entry.sql == "s2"

        # PostgreSQL entry should be gone
        entry = await cache.get("q1", "postgresql", "pg_schema")
        assert entry is None

    @given(
        database_type=database_type_strategy(),
    )
    @settings(max_examples=20, deadline=None)
    def test_database_specific_invalidation(self, database_type: str):
        """Property: Invalidation is database-type specific."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        async def run_test():
            all_db_types = ["postgresql", "mysql", "oracle", "sqlserver"]

            # Store entry for each database type
            for db_type in all_db_types:
                await cache.set(
                    query=f"SELECT * FROM {db_type}_table",
                    sql=f"SELECT id FROM {db_type}_table",
                    database_type=db_type,
                    schema_hash=f"schema_{db_type}",
                    method_used="test",
                    confidence=0.9,
                )

            # Invalidate only the target database type
            await cache.invalidate_by_schema(database_type, "new_schema")

            # Check that only target db type entries are invalidated
            for db_type in all_db_types:
                entry = await cache.get(
                    f"SELECT * FROM {db_type}_table",
                    db_type,
                    f"schema_{db_type}"
                )
                if db_type == database_type:
                    assert entry is None, f"{db_type} entry should be invalidated"
                else:
                    assert entry is not None, f"{db_type} entry should remain"

        asyncio.run(run_test())


# =============================================================================
# Property 45: LRU Cache Eviction
# =============================================================================

class TestLRUCacheEviction:
    """
    Property 45: LRU Cache Eviction

    Validates that:
    1. Least recently used entries are evicted first
    2. Cache respects max size limits
    3. Recently accessed entries are preserved
    """

    @pytest.mark.asyncio
    async def test_cache_respects_max_size(self):
        """Property: Cache does not exceed max size."""
        max_size = 5
        config = CacheConfig(
            max_size=max_size,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        # Add more entries than max size
        for i in range(max_size * 2):
            await cache.set(
                query=f"query_{i}",
                sql=f"sql_{i}",
                database_type="postgresql",
                schema_hash="schema",
                method_used="test",
                confidence=0.9,
            )

        stats = await cache.get_stats()
        assert stats.total_entries <= max_size

    @pytest.mark.asyncio
    async def test_lru_evicts_oldest_entries(self):
        """Property: LRU eviction removes least recently used entries."""
        max_size = 3
        config = CacheConfig(
            max_size=max_size,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        # Add 3 entries (filling cache)
        for i in range(3):
            await cache.set(
                query=f"query_{i}",
                sql=f"sql_{i}",
                database_type="postgresql",
                schema_hash="schema",
                method_used="test",
                confidence=0.9,
            )

        # Access query_0 and query_2 (making query_1 LRU)
        await cache.get("query_0", "postgresql", "schema")
        await cache.get("query_2", "postgresql", "schema")

        # Add new entry, triggering eviction
        await cache.set(
            query="query_new",
            sql="sql_new",
            database_type="postgresql",
            schema_hash="schema",
            method_used="test",
            confidence=0.9,
        )

        # query_1 should be evicted (LRU)
        entry = await cache.get("query_1", "postgresql", "schema")
        assert entry is None

        # Recently accessed entries should remain
        assert await cache.get("query_0", "postgresql", "schema") is not None
        assert await cache.get("query_2", "postgresql", "schema") is not None
        assert await cache.get("query_new", "postgresql", "schema") is not None

    @pytest.mark.asyncio
    async def test_recently_accessed_preserved_during_eviction(self):
        """Property: Recently accessed entries are preserved during eviction."""
        max_size = 5
        config = CacheConfig(
            max_size=max_size,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        # Fill cache
        for i in range(max_size):
            await cache.set(
                query=f"query_{i}",
                sql=f"sql_{i}",
                database_type="postgresql",
                schema_hash="schema",
                method_used="test",
                confidence=0.9,
            )

        # Access the first two entries multiple times (making them hot)
        for _ in range(5):
            await cache.get("query_0", "postgresql", "schema")
            await cache.get("query_1", "postgresql", "schema")

        # Add many new entries to trigger evictions
        for i in range(max_size, max_size * 2):
            await cache.set(
                query=f"query_{i}",
                sql=f"sql_{i}",
                database_type="postgresql",
                schema_hash="schema",
                method_used="test",
                confidence=0.9,
            )

        # Hot entries should still be accessible
        entry_0 = await cache.get("query_0", "postgresql", "schema")
        entry_1 = await cache.get("query_1", "postgresql", "schema")

        assert entry_0 is not None, "Hot entry 0 should be preserved"
        assert entry_1 is not None, "Hot entry 1 should be preserved"

    @given(
        num_entries=st.integers(min_value=10, max_value=50),
        max_size=st.integers(min_value=5, max_value=20),
    )
    @settings(max_examples=20, deadline=None)
    def test_cache_never_exceeds_limit(self, num_entries: int, max_size: int):
        """Property: Cache size never exceeds configured maximum."""
        config = CacheConfig(
            max_size=max_size,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        async def run_test():
            for i in range(num_entries):
                await cache.set(
                    query=f"query_{i}",
                    sql=f"sql_{i}",
                    database_type="postgresql",
                    schema_hash=f"schema_{i % 3}",
                    method_used="test",
                    confidence=0.9,
                )

                # Check size after each insertion
                stats = await cache.get_stats()
                assert stats.total_entries <= max_size, \
                    f"Cache size {stats.total_entries} exceeds max {max_size}"

        asyncio.run(run_test())


# =============================================================================
# Additional Edge Case Tests
# =============================================================================

class TestCacheEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_cache_stats(self):
        """Property: Empty cache has correct initial stats."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        stats = await cache.get_stats()
        assert stats.total_entries == 0
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.hit_rate == 0.0

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Property: Cache clear removes all entries."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        # Add entries
        for i in range(10):
            await cache.set(
                query=f"query_{i}",
                sql=f"sql_{i}",
                database_type="postgresql",
                schema_hash="schema",
                method_used="test",
                confidence=0.9,
            )

        # Clear
        cleared = await cache.clear()
        assert cleared == 10

        # Verify empty
        stats = await cache.get_stats()
        assert stats.total_entries == 0

    @pytest.mark.asyncio
    async def test_cache_warm_up(self):
        """Property: Cache warm-up populates cache correctly."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        warm_up_entries = [
            {
                "query": f"query_{i}",
                "sql": f"sql_{i}",
                "database_type": "postgresql",
                "schema_hash": "schema",
                "method_used": "test",
                "confidence": 0.9,
            }
            for i in range(5)
        ]

        loaded = await cache.warm_up(warm_up_entries)
        assert loaded == 5

        # Verify entries are accessible
        for i in range(5):
            entry = await cache.get(f"query_{i}", "postgresql", "schema")
            assert entry is not None
            assert entry.sql == f"sql_{i}"

    @pytest.mark.asyncio
    async def test_delete_entry(self):
        """Property: Individual entries can be deleted."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        # Add entry
        key = await cache.set(
            query="query_1",
            sql="sql_1",
            database_type="postgresql",
            schema_hash="schema",
            method_used="test",
            confidence=0.9,
        )

        # Verify exists
        entry = await cache.get("query_1", "postgresql", "schema")
        assert entry is not None

        # Delete
        deleted = await cache.delete(key)
        assert deleted is True

        # Verify gone
        entry = await cache.get("query_1", "postgresql", "schema")
        assert entry is None

    @given(
        query=query_strategy(),
        database_type=database_type_strategy(),
        schema_hash=schema_hash_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_consistent_key_generation(
        self, query: str, database_type: str, schema_hash: str
    ):
        """Property: Same inputs always generate same cache key."""
        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        key1 = cache.generate_key(query, database_type, schema_hash)
        key2 = cache.generate_key(query, database_type, schema_hash)

        assert key1 == key2, "Same inputs should generate same key"

    @given(
        query1=query_strategy(),
        query2=query_strategy(),
        database_type=database_type_strategy(),
        schema_hash=schema_hash_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_different_queries_different_keys(
        self, query1: str, query2: str, database_type: str, schema_hash: str
    ):
        """Property: Different queries generate different keys."""
        assume(query1 != query2)  # Ensure queries are different

        config = CacheConfig(
            max_size=1000,
            default_ttl_seconds=3600,
            enable_redis=False,
        )
        cache = QueryCache(config)

        key1 = cache.generate_key(query1, database_type, schema_hash)
        key2 = cache.generate_key(query2, database_type, schema_hash)

        assert key1 != key2, "Different queries should generate different keys"


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
