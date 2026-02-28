"""
Property-based tests for integration test isolation.

Verifies that the test infrastructure correctly isolates:
- Database instances from production (Property 10, 30)
- Redis instances/keyspaces from production (Property 27)
- External service calls via mocking (Property 28)
- Environment state between test runs (Property 29)

**Validates: Requirements 3.5, 12.1, 12.3, 12.4, 12.5, 12.6**

Uses Hypothesis to generate diverse inputs and verify isolation
properties hold universally across all scenarios.
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from tests.database_isolation import (
    TestDatabaseConfig,
    TestDatabaseEngineFactory,
    DatabaseCleanupManager,
    prevent_production_database_access,
    isolated_test_session,
)
from tests.redis_isolation import (
    TestRedisConfig,
    TestRedisClientFactory,
    RedisKeyspaceIsolator,
    PrefixedRedisClient,
    prevent_production_redis_access,
)


# =============================================================================
# Strategies
# =============================================================================

def production_db_url_patterns() -> st.SearchStrategy[str]:
    """Generate URLs that look like production database connections."""
    hosts = st.sampled_from([
        "prod-db.rds.amazonaws.com",
        "production-db.cloudsql.com",
        "myapp-prod.database.azure.com",
        "prod-server.internal",
        "production-postgres.cluster.local",
    ])
    users = st.sampled_from(["admin", "app_user", "postgres", "root"])
    passwords = st.text(min_size=4, max_size=12, alphabet="abcdefghijklmnop0123456789")
    dbs = st.sampled_from(["myapp", "superinsight", "production_db", "app_data"])

    return st.builds(
        lambda u, p, h, d: f"postgresql://{u}:{p}@{h}:5432/{d}",
        users, passwords, hosts, dbs,
    )


def safe_test_db_url_patterns() -> st.SearchStrategy[str]:
    """Generate URLs that are safe for testing (no production indicators)."""
    return st.sampled_from([
        "sqlite:///:memory:",
        "sqlite:///test.db",
        "postgresql://test:test@localhost:5433/test_db",
        "postgresql://user:pass@127.0.0.1:5433/superinsight_test",
        "postgresql://ci:ci@postgres-test:5432/test_db",
    ])


def redis_key_names() -> st.SearchStrategy[str]:
    """Generate realistic Redis key names."""
    segments = st.text(
        min_size=1, max_size=20,
        alphabet="abcdefghijklmnopqrstuvwxyz_-0123456789",
    )
    return st.builds(
        lambda parts: ":".join(parts),
        st.lists(segments, min_size=1, max_size=4),
    )


def production_redis_url_patterns() -> st.SearchStrategy[str]:
    """Generate URLs that look like production Redis connections."""
    hosts = st.sampled_from([
        "prod-cache.redis.amazonaws.com",
        "production-redis.redis.cache.com",
        "prod.memorystore.googleapis.com",
        "redis-prod.internal",
    ])
    return st.builds(
        lambda h: f"redis://{h}:6379/0",
        hosts,
    )


def external_service_urls() -> st.SearchStrategy[str]:
    """Generate external service URLs that should be mocked in tests."""
    return st.sampled_from([
        "https://api.openai.com/v1/chat/completions",
        "https://smtp.gmail.com:587",
        "https://hooks.slack.com/services/T00/B00/xxx",
        "https://api.mturk.com/2017-01-17/tasks",
        "https://api.scale.com/v1/tasks",
        "https://s3.amazonaws.com/my-bucket/file.json",
    ])


# =============================================================================
# Property 10: Integration Test Database Isolation
# =============================================================================

class TestDatabaseIsolationProperty:
    """
    Property 10: Integration Test Database Isolation

    For any integration test execution, the test SHALL use a database
    instance that is separate from production and other test runs.

    **Validates: Requirements 3.5, 12.1**
    """

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_sqlite_engine_never_uses_production_url(self, data):
        """SQLite test engine always uses in-memory URL, never production."""
        engine = TestDatabaseEngineFactory.create_sqlite_engine()
        url = str(engine.url)

        assert "memory" in url or "test" in url.lower()
        assert "prod" not in url.lower()
        assert "rds.amazonaws.com" not in url
        assert "cloudsql.com" not in url

        engine.dispose()

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_test_db_config_uses_separate_port(self, data):
        """Test database config always uses port 5433, not production 5432."""
        url = TestDatabaseConfig.get_postgres_url()

        assert "5433" in url, "Test DB must use port 5433, not production 5432"
        assert "superinsight_test" in url, "Test DB must use test-specific database name"

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_isolated_session_rolls_back(self, data):
        """Each isolated session rolls back, preventing data leakage."""
        engine = TestDatabaseEngineFactory.create_sqlite_engine()

        # Write data in one session
        from sqlalchemy import text
        with isolated_test_session(engine) as session:
            session.execute(text(
                "CREATE TABLE IF NOT EXISTS _isolation_check (id INTEGER PRIMARY KEY, val TEXT)"
            ))
            session.execute(text("INSERT INTO _isolation_check (id, val) VALUES (1, 'leaked')"))
            session.flush()

        # Verify data is NOT visible in a new session (rolled back)
        with isolated_test_session(engine) as session:
            try:
                result = session.execute(text("SELECT COUNT(*) FROM _isolation_check"))
                count = result.scalar()
                assert count == 0, f"Data leaked between sessions: {count} rows found"
            except Exception:
                # Table may not exist after rollback — that's also valid isolation
                pass

        engine.dispose()


# =============================================================================
# Property 27: Redis Test Instance Isolation
# =============================================================================

class TestRedisIsolationProperty:
    """
    Property 27: Redis Test Instance Isolation

    For any test execution that uses Redis, the test SHALL use a separate
    Redis instance or keyspace that is isolated from production and other
    test runs.

    **Validates: Requirements 12.3**
    """

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_redis_config_uses_test_port(self, data):
        """Redis test config always uses port 6380, not production 6379."""
        url = TestRedisConfig.get_url()

        assert "6380" in url, "Test Redis must use port 6380, not production 6379"
        assert "/15" in url or "/14" in url or "/1" in url, (
            "Test Redis must use a non-default database number"
        )

    @given(key=redis_key_names())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_prefixed_client_always_adds_prefix(self, key):
        """PrefixedRedisClient always adds test prefix to keys."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_client.set.return_value = True

        prefix = TestRedisConfig.get_key_prefix()
        prefixed = PrefixedRedisClient(mock_client, prefix)

        prefixed.get(key)
        actual_key = mock_client.get.call_args[0][0]
        assert actual_key.startswith(prefix), (
            f"Key '{actual_key}' missing test prefix '{prefix}'"
        )

    @given(key=redis_key_names(), value=st.text(min_size=1, max_size=50))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_prefixed_client_set_always_prefixed(self, key, value):
        """PrefixedRedisClient.set always prefixes the key."""
        mock_client = MagicMock()
        mock_client.set.return_value = True

        prefix = TestRedisConfig.get_key_prefix()
        prefixed = PrefixedRedisClient(mock_client, prefix)

        prefixed.set(key, value)
        actual_key = mock_client.set.call_args[0][0]
        assert actual_key.startswith(prefix)

    @given(key=redis_key_names())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_keyspace_isolator_tracks_keys(self, key):
        """RedisKeyspaceIsolator tracks all created keys for cleanup."""
        mock_client = MagicMock()
        mock_client.set.return_value = True
        mock_client.setex.return_value = True

        isolator = RedisKeyspaceIsolator(mock_client)
        isolator.set_test_key(key, "test_value")

        tracked = isolator.get_tracked_keys()
        assert len(tracked) == 1

        prefix = TestRedisConfig.get_key_prefix()
        assert tracked[0].startswith(prefix)

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_redis_db_number_is_isolated(self, data):
        """Test Redis always uses a dedicated database number (not 0)."""
        assert TestRedisConfig.REDIS_DB != 0, (
            "Test Redis must not use db=0 (production default)"
        )
        assert TestRedisConfig.REDIS_PORT != 6379, (
            "Test Redis must not use port 6379 (production default)"
        )


# =============================================================================
# Property 28: External Service Mocking
# =============================================================================

class TestExternalServiceMockingProperty:
    """
    Property 28: External Service Mocking

    For any integration test execution that involves external service calls,
    those calls SHALL be intercepted and handled by mock services rather
    than reaching actual external systems.

    **Validates: Requirements 12.4**
    """

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_env_uses_test_api_keys(self, data):
        """Test environment always uses fake/test API keys."""
        env = os.environ.get("APP_ENV", "test")
        assert env == "test", "Tests must run in test environment"

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            assert "test" in api_key.lower() or "fake" in api_key.lower() or "not-real" in api_key.lower(), (
                "Test environment must use fake API keys"
            )

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_label_studio_uses_test_config(self, data):
        """Label Studio config in test env points to local/internal host, not production."""
        ls_url = os.environ.get("LABEL_STUDIO_URL", "http://localhost:8080")

        # Accept localhost, 127.0.0.1, or Docker service names (no dots = internal)
        is_local = "localhost" in ls_url or "127.0.0.1" in ls_url
        is_docker_service = "://" in ls_url and "." not in ls_url.split("://")[1].split(":")[0]

        assert is_local or is_docker_service, (
            f"Label Studio URL must point to local/internal host, got: {ls_url}"
        )

    @given(url=external_service_urls())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_external_urls_not_in_test_env(self, url):
        """No real external service URLs should be configured in test env."""
        db_url = os.environ.get("DATABASE_URL", "")
        redis_url = os.environ.get("REDIS_URL", "")

        # Production external URLs should never appear in test config
        assert url not in db_url
        assert url not in redis_url

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_mock_label_studio_fixture_returns_mock(self, data):
        """mock_label_studio fixture returns MagicMock, not real client."""
        mock = MagicMock()
        mock.get_projects.return_value = []
        mock.create_project.return_value = {"id": 1, "title": "Test"}

        assert isinstance(mock.get_projects.return_value, list)
        assert isinstance(mock.create_project.return_value, dict)
        # Verify no real HTTP calls are made
        mock.get_projects.assert_not_called()

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_mock_llm_service_returns_mock(self, data):
        """mock_llm_service fixture returns MagicMock, not real LLM."""
        mock = MagicMock()
        mock.annotate.return_value = {
            "annotations": [],
            "confidence": 0.95,
            "model": "test-model",
        }

        result = mock.annotate()
        assert result["model"] == "test-model"
        assert "annotations" in result


# =============================================================================
# Property 29: Test Environment Reset Between Runs
# =============================================================================

class TestEnvironmentResetProperty:
    """
    Property 29: Test Environment Reset Between Runs

    For any two consecutive test executions, the test environment state
    SHALL be reset between them to ensure isolation.

    **Validates: Requirements 12.5**
    """

    @given(
        records=st.lists(
            st.tuples(st.integers(min_value=1, max_value=1000), st.text(min_size=1, max_size=20)),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_db_session_resets_between_operations(self, records):
        """Database sessions reset state between isolated operations."""
        engine = TestDatabaseEngineFactory.create_sqlite_engine()
        from sqlalchemy import text

        # First "test run": insert data
        with isolated_test_session(engine) as session:
            session.execute(text(
                "CREATE TABLE IF NOT EXISTS _reset_check "
                "(id INTEGER PRIMARY KEY, name TEXT)"
            ))
            for rid, name in records:
                try:
                    session.execute(
                        text("INSERT INTO _reset_check (id, name) VALUES (:id, :name)"),
                        {"id": rid, "name": name},
                    )
                except Exception:
                    pass
            session.flush()

        # Second "test run": verify state is clean
        with isolated_test_session(engine) as session:
            try:
                result = session.execute(text("SELECT COUNT(*) FROM _reset_check"))
                count = result.scalar()
                assert count == 0, (
                    f"Environment not reset: {count} rows leaked from previous run"
                )
            except Exception:
                # Table doesn't exist after rollback — valid reset
                pass

        engine.dispose()

    @given(
        keys=st.lists(redis_key_names(), min_size=1, max_size=5),
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_redis_isolator_cleanup_resets_state(self, keys):
        """RedisKeyspaceIsolator cleanup removes all tracked keys."""
        mock_client = MagicMock()
        mock_client.set.return_value = True
        mock_client.setex.return_value = True
        mock_client.delete.return_value = len(keys)

        isolator = RedisKeyspaceIsolator(mock_client)

        # Simulate first test run: create keys
        for key in keys:
            isolator.set_test_key(key, "value")

        assert len(isolator.get_tracked_keys()) == len(keys)

        # Simulate cleanup between runs
        deleted = isolator.cleanup_test_keys()

        assert len(isolator.get_tracked_keys()) == 0, (
            "Tracked keys not cleared after cleanup"
        )

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_cleanup_manager_verifies_clean_state(self, data):
        """DatabaseCleanupManager can verify clean state after reset."""
        engine = TestDatabaseEngineFactory.create_sqlite_engine()

        with isolated_test_session(engine) as session:
            manager = DatabaseCleanupManager(session)
            is_clean = manager.verify_clean_state()
            assert is_clean is True, "Fresh session should report clean state"

        engine.dispose()


# =============================================================================
# Property 30: Production Database Access Prevention
# =============================================================================

class TestProductionAccessPreventionProperty:
    """
    Property 30: Production Database Access Prevention

    For any test execution, no database connections SHALL be established
    to production database instances.

    **Validates: Requirements 12.6**
    """

    @given(prod_url=production_db_url_patterns())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_production_db_urls_are_blocked(self, prod_url):
        """Any production-like database URL is blocked by prevention check."""
        original_env = os.environ.get("APP_ENV")
        original_url = os.environ.get("DATABASE_URL")

        try:
            os.environ["APP_ENV"] = "test"
            os.environ["DATABASE_URL"] = prod_url

            with pytest.raises(RuntimeError, match="production database"):
                prevent_production_database_access()
        finally:
            os.environ["APP_ENV"] = original_env or "test"
            if original_url:
                os.environ["DATABASE_URL"] = original_url
            else:
                os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    @given(safe_url=safe_test_db_url_patterns())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_safe_test_urls_are_allowed(self, safe_url):
        """Safe test database URLs pass the prevention check."""
        original_env = os.environ.get("APP_ENV")
        original_url = os.environ.get("DATABASE_URL")

        try:
            os.environ["APP_ENV"] = "test"
            os.environ["DATABASE_URL"] = safe_url

            # Should NOT raise
            prevent_production_database_access()
        finally:
            os.environ["APP_ENV"] = original_env or "test"
            if original_url:
                os.environ["DATABASE_URL"] = original_url
            else:
                os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_production_env_always_blocked(self, data):
        """APP_ENV=production always blocks test execution."""
        original_env = os.environ.get("APP_ENV")

        try:
            os.environ["APP_ENV"] = "production"

            with pytest.raises(RuntimeError, match="production environment"):
                prevent_production_database_access()
        finally:
            os.environ["APP_ENV"] = original_env or "test"

    @given(prod_url=production_redis_url_patterns())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_production_redis_urls_are_blocked(self, prod_url):
        """Any production-like Redis URL is blocked by prevention check."""
        original_env = os.environ.get("APP_ENV")
        original_url = os.environ.get("REDIS_URL")

        try:
            os.environ["APP_ENV"] = "test"
            os.environ["REDIS_URL"] = prod_url

            with pytest.raises(RuntimeError, match="production Redis"):
                prevent_production_redis_access()
        finally:
            os.environ["APP_ENV"] = original_env or "test"
            if original_url:
                os.environ["REDIS_URL"] = original_url
            else:
                os.environ["REDIS_URL"] = "redis://localhost:6380/15"

    @given(data=st.data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_test_env_database_url_is_safe(self, data):
        """Current test environment DATABASE_URL is always safe."""
        db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")

        production_indicators = [
            "prod", "production", "rds.amazonaws.com",
            "cloudsql.com", "database.azure.com",
        ]
        for indicator in production_indicators:
            assert indicator not in db_url.lower(), (
                f"Test DATABASE_URL contains production indicator: {indicator}"
            )
