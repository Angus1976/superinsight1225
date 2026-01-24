"""Property-based tests for Text-to-SQL Service.

This module tests the following properties:
- Property 34: Comprehensive Metrics Tracking
- Property 51: Tenant Data Isolation
- Property 52: Tenant Usage Tracking
- Property 53: Tenant Quota Enforcement

Requirements:
- All requests should be tracked with comprehensive metrics
- Tenant data should be completely isolated
- Tenant usage should be accurately tracked
- Quotas should be enforced when limits exceeded
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import List
from datetime import datetime
from uuid import UUID, uuid4

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.text_to_sql.text_to_sql_service import (
    TextToSQLService,
    SQLGenerationRequest,
    QuotaExceededError,
    reset_text_to_sql_service,
)


# ============================================================================
# Property 34: Comprehensive Metrics Tracking
# ============================================================================

class TestComprehensiveMetricsTracking:
    """Property 34: All requests tracked with comprehensive metrics.

    Validates: Requirements 8.1, 8.2, 8.3
    """

    @pytest.mark.asyncio
    @given(
        num_requests=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    async def test_all_requests_tracked(self, num_requests: int):
        """Test that all requests are tracked in metrics."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_id = uuid4()

        # Make multiple requests
        for i in range(num_requests):
            request = SQLGenerationRequest(
                query=f"Get all users from table_{i}",
                database_type="postgresql",
                tenant_id=tenant_id,
                use_cache=False,  # Disable cache for consistent testing
            )

            try:
                await service.generate_sql(request)
            except Exception:
                pass  # May fail on validation, but should still be tracked

        # Get metrics
        metrics = await service.get_tenant_metrics(tenant_id)

        # All requests should be tracked
        assert metrics.total_requests == num_requests
        assert metrics.successful_requests + metrics.failed_requests == num_requests

    @pytest.mark.asyncio
    @given(
        num_template=st.integers(min_value=1, max_value=20),
        num_llm=st.integers(min_value=1, max_value=20),
        num_hybrid=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=100, deadline=None)
    async def test_method_usage_tracking(
        self,
        num_template: int,
        num_llm: int,
        num_hybrid: int,
    ):
        """Test that method usage is tracked separately."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_id = uuid4()

        # Make requests with different methods
        for i in range(num_template):
            request = SQLGenerationRequest(
                query="Simple query",
                database_type="postgresql",
                tenant_id=tenant_id,
                method_preference="template",
                use_cache=False,
            )
            await service.generate_sql(request)

        for i in range(num_llm):
            request = SQLGenerationRequest(
                query="Complex query",
                database_type="postgresql",
                tenant_id=tenant_id,
                method_preference="llm",
                use_cache=False,
            )
            await service.generate_sql(request)

        for i in range(num_hybrid):
            request = SQLGenerationRequest(
                query="Medium query",
                database_type="postgresql",
                tenant_id=tenant_id,
                method_preference="hybrid",
                use_cache=False,
            )
            await service.generate_sql(request)

        # Get metrics
        metrics = await service.get_tenant_metrics(tenant_id)

        # Method usage should be tracked
        assert metrics.template_requests == num_template
        assert metrics.llm_requests_count == num_llm
        assert metrics.hybrid_requests == num_hybrid

    @pytest.mark.asyncio
    @given(
        use_cache=st.booleans()
    )
    @settings(max_examples=100, deadline=None)
    async def test_cache_hit_rate_tracking(self, use_cache: bool):
        """Test that cache hit/miss rates are tracked."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_id = uuid4()

        # Make same request twice
        request = SQLGenerationRequest(
            query="Get all users",
            database_type="postgresql",
            tenant_id=tenant_id,
            use_cache=use_cache,
        )

        # First request (cache miss)
        result1 = await service.generate_sql(request)

        # Second request (cache hit if caching enabled)
        result2 = await service.generate_sql(request)

        # Get metrics
        metrics = await service.get_tenant_metrics(tenant_id)

        if use_cache:
            # Should have 1 hit, 1 miss
            assert metrics.cache_hits == 1
            assert metrics.cache_misses == 1
            assert metrics.cache_hit_rate == 0.5
        else:
            # No caching, all misses
            assert metrics.cache_hits == 0
            assert metrics.cache_misses == 2
            assert metrics.cache_hit_rate == 0.0

    @pytest.mark.asyncio
    async def test_execution_time_percentiles(self):
        """Test that execution time percentiles are calculated."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_id = uuid4()

        # Make multiple requests
        for i in range(20):
            request = SQLGenerationRequest(
                query=f"Query {i}",
                database_type="postgresql",
                tenant_id=tenant_id,
                use_cache=False,
            )
            await service.generate_sql(request)

        # Get metrics
        metrics = await service.get_tenant_metrics(tenant_id)

        # Percentiles should be calculated
        assert metrics.avg_execution_time_ms > 0
        assert metrics.p50_execution_time_ms > 0
        assert metrics.p95_execution_time_ms > 0
        assert metrics.p99_execution_time_ms > 0

        # P99 >= P95 >= P50
        assert metrics.p99_execution_time_ms >= metrics.p95_execution_time_ms
        assert metrics.p95_execution_time_ms >= metrics.p50_execution_time_ms


# ============================================================================
# Property 51: Tenant Data Isolation
# ============================================================================

class TestTenantDataIsolation:
    """Property 51: Tenant data is completely isolated.

    Validates: Requirements 12.1, 12.2
    """

    @pytest.mark.asyncio
    @given(
        num_tenants=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    async def test_metrics_isolated_per_tenant(self, num_tenants: int):
        """Test that metrics are isolated per tenant."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_ids = [uuid4() for _ in range(num_tenants)]

        # Each tenant makes different number of requests
        requests_per_tenant = {}
        for i, tenant_id in enumerate(tenant_ids):
            num_requests = i + 1  # 1, 2, 3, ...
            requests_per_tenant[tenant_id] = num_requests

            for j in range(num_requests):
                request = SQLGenerationRequest(
                    query=f"Query {j}",
                    database_type="postgresql",
                    tenant_id=tenant_id,
                    use_cache=False,
                )
                await service.generate_sql(request)

        # Verify each tenant has correct metrics
        for tenant_id, expected_requests in requests_per_tenant.items():
            metrics = await service.get_tenant_metrics(tenant_id)
            assert metrics.total_requests == expected_requests
            assert metrics.tenant_id == tenant_id

    @pytest.mark.asyncio
    @given(
        num_tenants=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    async def test_quotas_isolated_per_tenant(self, num_tenants: int):
        """Test that quotas are isolated per tenant."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_ids = [uuid4() for _ in range(num_tenants)]

        # Each tenant has independent quota
        for tenant_id in tenant_ids:
            quota = await service.get_tenant_quota(tenant_id)
            assert quota.tenant_id == tenant_id
            assert quota.monthly_llm_requests == 0
            assert quota.monthly_llm_tokens == 0

        # Make LLM request for first tenant
        request = SQLGenerationRequest(
            query="Complex query",
            database_type="postgresql",
            tenant_id=tenant_ids[0],
            method_preference="llm",
            use_cache=False,
        )
        await service.generate_sql(request)

        # Only first tenant should have usage
        quota1 = await service.get_tenant_quota(tenant_ids[0])
        assert quota1.monthly_llm_requests == 1

        # Other tenants should have zero usage
        for tenant_id in tenant_ids[1:]:
            quota = await service.get_tenant_quota(tenant_id)
            assert quota.monthly_llm_requests == 0


# ============================================================================
# Property 52: Tenant Usage Tracking
# ============================================================================

class TestTenantUsageTracking:
    """Property 52: Tenant usage is accurately tracked.

    Validates: Requirements 12.3, 12.6
    """

    @pytest.mark.asyncio
    @given(
        num_llm_requests=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=100, deadline=None)
    async def test_llm_request_counting(self, num_llm_requests: int):
        """Test that LLM requests are counted accurately."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_id = uuid4()

        # Make LLM requests
        for i in range(num_llm_requests):
            request = SQLGenerationRequest(
                query=f"Query {i}",
                database_type="postgresql",
                tenant_id=tenant_id,
                method_preference="llm",
                use_cache=False,
            )
            await service.generate_sql(request)

        # Check quota usage
        quota = await service.get_tenant_quota(tenant_id)
        assert quota.monthly_llm_requests == num_llm_requests

    @pytest.mark.asyncio
    @given(
        query_length=st.integers(min_value=10, max_value=500)
    )
    @settings(max_examples=100, deadline=None)
    async def test_token_usage_tracking(self, query_length: int):
        """Test that token usage is tracked."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_id = uuid4()

        # Make LLM request with specific length
        query = "a" * query_length
        request = SQLGenerationRequest(
            query=query,
            database_type="postgresql",
            tenant_id=tenant_id,
            method_preference="llm",
            use_cache=False,
        )
        await service.generate_sql(request)

        # Check token usage
        quota = await service.get_tenant_quota(tenant_id)
        assert quota.monthly_llm_tokens > 0

        # Token count should be roughly proportional to query length
        # (rough estimate: ~4 chars per token)
        expected_min_tokens = query_length // 5
        assert quota.monthly_llm_tokens >= expected_min_tokens

    @pytest.mark.asyncio
    async def test_template_requests_dont_count_quota(self):
        """Test that template requests don't count against quota."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_id = uuid4()

        # Make template requests
        for i in range(10):
            request = SQLGenerationRequest(
                query="Simple query",
                database_type="postgresql",
                tenant_id=tenant_id,
                method_preference="template",
                use_cache=False,
            )
            await service.generate_sql(request)

        # Quota should be zero
        quota = await service.get_tenant_quota(tenant_id)
        assert quota.monthly_llm_requests == 0
        assert quota.monthly_llm_tokens == 0


# ============================================================================
# Property 53: Tenant Quota Enforcement
# ============================================================================

class TestTenantQuotaEnforcement:
    """Property 53: Quotas are enforced when limits exceeded.

    Validates: Requirements 12.4
    """

    @pytest.mark.asyncio
    async def test_quota_enforcement_on_limit(self):
        """Test that quota is enforced when limit reached."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_id = uuid4()

        # Set low limit for testing
        quota = await service.get_tenant_quota(tenant_id)
        quota.llm_requests_limit = 5

        # Make requests up to limit
        for i in range(5):
            request = SQLGenerationRequest(
                query=f"Query {i}",
                database_type="postgresql",
                tenant_id=tenant_id,
                method_preference="llm",
                use_cache=False,
            )
            await service.generate_sql(request)

        # Next LLM request should fail
        request = SQLGenerationRequest(
            query="One more",
            database_type="postgresql",
            tenant_id=tenant_id,
            method_preference="llm",
            use_cache=False,
        )

        with pytest.raises(QuotaExceededError):
            await service.generate_sql(request)

    @pytest.mark.asyncio
    async def test_automatic_fallback_to_template(self):
        """Test that quota exceeded causes automatic template fallback."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_id = uuid4()

        # Set quota as exceeded
        quota = await service.get_tenant_quota(tenant_id)
        quota.llm_requests_limit = 1
        quota.monthly_llm_requests = 2
        quota.quota_exceeded = True

        # Request with auto method selection
        request = SQLGenerationRequest(
            query="Complex query with joins and aggregations",  # Would normally use LLM
            database_type="postgresql",
            tenant_id=tenant_id,
            method_preference=None,  # Auto-select
            use_cache=False,
        )

        result = await service.generate_sql(request)

        # Should have fallen back to template
        assert result.method_used == "template"

    @pytest.mark.asyncio
    async def test_quota_reset_monthly(self):
        """Test that quota resets at month boundary."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_id = uuid4()

        # Set quota with past reset date
        quota = await service.get_tenant_quota(tenant_id)
        quota.monthly_llm_requests = 100
        quota.monthly_llm_tokens = 10000
        quota.quota_exceeded = True

        # Force reset date to past
        from datetime import timedelta
        quota.quota_reset_date = datetime.now() - timedelta(days=1)

        # Access quota again (should trigger reset)
        quota_after = await service.get_tenant_quota(tenant_id)

        # Should be reset
        assert quota_after.monthly_llm_requests == 0
        assert quota_after.monthly_llm_tokens == 0
        assert not quota_after.quota_exceeded

    @pytest.mark.asyncio
    @given(
        requests_limit=st.integers(min_value=5, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    async def test_quota_limit_configurable(self, requests_limit: int):
        """Test that quota limits are configurable per tenant."""
        await reset_text_to_sql_service()
        service = TextToSQLService()

        tenant_id = uuid4()

        # Set custom limit
        quota = await service.get_tenant_quota(tenant_id)
        quota.llm_requests_limit = requests_limit

        # Make requests up to limit
        for i in range(requests_limit):
            request = SQLGenerationRequest(
                query=f"Query {i}",
                database_type="postgresql",
                tenant_id=tenant_id,
                method_preference="llm",
                use_cache=False,
            )
            await service.generate_sql(request)

        # Check quota is at limit
        quota_after = await service.get_tenant_quota(tenant_id)
        assert quota_after.monthly_llm_requests == requests_limit
        assert quota_after.quota_exceeded


# ============================================================================
# Helper functions for running async tests
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
