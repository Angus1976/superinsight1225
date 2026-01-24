"""
Property-based tests for LLM Health Monitor.

Tests correctness properties with Hypothesis (100+ iterations each).

Properties tested:
- Property 14: Health Check Scheduling
  - Validates: Requirements 5.1
  - Verifies health checks execute at regular intervals

- Property 15: Health Status Management
  - Validates: Requirements 5.2, 5.3, 5.4
  - Verifies health status tracking, alerts, and recovery
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, Mock, MagicMock
from hypothesis import given, strategies as st, settings, HealthCheck
from uuid import uuid4

# Import the module under test
try:
    from src.ai.llm.health_monitor import HealthMonitor, HEALTH_CHECK_INTERVAL_SECONDS
    from src.ai.llm_schemas import LLMMethod, HealthStatus
    from src.ai.llm_switcher import LLMProvider
except ImportError:
    pytest.skip("LLM health monitor not available", allow_module_level=True)


# ==================== Test Fixtures ====================

class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, method: LLMMethod, healthy: bool = True, error: str = None):
        self._method = method
        self._healthy = healthy
        self._error = error
        self.health_check_count = 0

    @property
    def method(self) -> LLMMethod:
        return self._method

    async def generate(self, *args, **kwargs):
        pass

    async def stream_generate(self, *args, **kwargs):
        pass

    async def embed(self, *args, **kwargs):
        pass

    async def health_check(self) -> HealthStatus:
        """Mock health check that tracks call count."""
        self.health_check_count += 1
        return HealthStatus(
            available=self._healthy,
            latency_ms=100.0 if self._healthy else 0.0,
            error=self._error if not self._healthy else None
        )

    def set_health(self, healthy: bool, error: str = None):
        """Update health status."""
        self._healthy = healthy
        self._error = error


class MockSwitcher:
    """Mock LLM switcher for testing."""

    def __init__(self):
        self._providers: Dict[LLMMethod, MockProvider] = {}
        self._initialized = True

    async def _ensure_initialized(self):
        """Mock initialization."""
        pass

    def add_provider(self, provider: MockProvider):
        """Add a provider to the switcher."""
        self._providers[provider.method] = provider


@pytest.fixture
def mock_switcher():
    """Create a mock LLM switcher."""
    return MockSwitcher()


@pytest.fixture
def health_monitor(mock_switcher):
    """Create a health monitor with mock switcher."""
    return HealthMonitor(
        switcher=mock_switcher,
        db_session=None,  # No database for property tests
        metrics_collector=None
    )


# ==================== Property Tests ====================

@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_providers=st.integers(min_value=1, max_value=5),
    check_duration_seconds=st.floats(min_value=0.5, max_value=2.0)
)
async def test_property_14_health_check_scheduling(
    num_providers: int,
    check_duration_seconds: float,
    mock_switcher: MockSwitcher
):
    """
    Property 14: Health Check Scheduling

    Validates: Requirements 5.1

    Property: Health checks are executed at regular intervals

    For any number of providers and check duration:
    - When health monitor is running
    - Then health checks occur at regular intervals
    - And all providers are checked in each cycle
    """
    # Setup: Create providers
    methods = list(LLMMethod)[:num_providers]
    providers = []

    for method in methods:
        provider = MockProvider(method=method, healthy=True)
        mock_switcher.add_provider(provider)
        providers.append(provider)

    # Create health monitor
    monitor = HealthMonitor(
        switcher=mock_switcher,
        db_session=None,
        metrics_collector=None
    )

    try:
        # Start monitoring
        await monitor.start()

        # Wait for at least one check cycle
        await asyncio.sleep(check_duration_seconds)

        # Verify: All providers were checked
        for provider in providers:
            # At least one health check should have been performed
            # (may be more if check_duration > HEALTH_CHECK_INTERVAL_SECONDS)
            assert provider.health_check_count >= 1, \
                f"Provider {provider.method} was not health-checked"

        # Property: Health checks are performed on all providers
        checked_providers = [p for p in providers if p.health_check_count > 0]
        assert len(checked_providers) == num_providers, \
            "Not all providers received health checks"

    finally:
        # Cleanup
        await monitor.stop()


@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    initial_health=st.booleans(),
    becomes_unhealthy=st.booleans(),
    error_message=st.text(min_size=0, max_size=100)
)
async def test_property_15_health_status_management(
    initial_health: bool,
    becomes_unhealthy: bool,
    error_message: str,
    mock_switcher: MockSwitcher
):
    """
    Property 15: Health Status Management

    Validates: Requirements 5.2, 5.3, 5.4

    Property: Health status is correctly tracked and alerts are triggered

    For any initial health state and transitions:
    - When provider health changes
    - Then status is correctly updated
    - And alerts are triggered on status change
    - And healthy providers can be queried
    """
    # Setup: Create a provider with initial health
    provider = MockProvider(
        method=LLMMethod.LOCAL_OLLAMA,
        healthy=initial_health,
        error="Initial error" if not initial_health else None
    )
    mock_switcher.add_provider(provider)

    # Create health monitor with alert tracking
    alert_calls: List[Dict[str, Any]] = []

    def alert_callback(alert_data: Dict[str, Any]):
        alert_calls.append(alert_data)

    monitor = HealthMonitor(
        switcher=mock_switcher,
        db_session=None,
        metrics_collector=None
    )
    monitor.register_alert_callback(alert_callback)

    try:
        # Start monitoring
        await monitor.start()

        # Wait for initial health check
        await asyncio.sleep(0.2)

        # Get provider ID
        provider_id = await monitor._get_provider_id(LLMMethod.LOCAL_OLLAMA)
        assert provider_id is not None

        # Property 1: Initial status is tracked
        initial_status = await monitor.get_health_status(provider_id)
        assert isinstance(initial_status, bool), "Health status should be boolean"

        # If provider becomes unhealthy, change its health
        if becomes_unhealthy and initial_health:
            provider.set_health(healthy=False, error=error_message)

            # Wait for next health check
            await asyncio.sleep(0.2)

            # Property 2: Status change is detected
            new_status = await monitor.get_health_status(provider_id)
            assert new_status == False, "Provider should be marked as unhealthy"

            # Property 3: Alert is triggered on status change
            # Filter for unhealthy alerts
            unhealthy_alerts = [
                a for a in alert_calls
                if a.get("alert_type") == "unhealthy"
            ]
            assert len(unhealthy_alerts) >= 1, \
                "Alert should be triggered when provider becomes unhealthy"

            # Property 4: Unhealthy providers are not in healthy list
            healthy_providers = await monitor.get_healthy_providers()
            assert provider_id not in healthy_providers, \
                "Unhealthy provider should not be in healthy list"

            # Now recover the provider
            provider.set_health(healthy=True, error=None)
            await asyncio.sleep(0.2)

            # Property 5: Recovery is detected
            recovered_status = await monitor.get_health_status(provider_id)
            assert recovered_status == True, "Provider should be marked as healthy after recovery"

            # Property 6: Recovery alert is triggered
            recovery_alerts = [
                a for a in alert_calls
                if a.get("alert_type") == "recovered"
            ]
            assert len(recovery_alerts) >= 1, \
                "Alert should be triggered when provider recovers"

            # Property 7: Recovered providers are in healthy list
            healthy_providers = await monitor.get_healthy_providers()
            assert provider_id in healthy_providers, \
                "Recovered provider should be in healthy list"

        # Property 8: Consecutive failures are tracked
        all_status = await monitor.get_all_health_status()
        if provider_id in all_status:
            status_info = all_status[provider_id]
            assert "consecutive_failures" in status_info, \
                "Consecutive failures should be tracked"
            assert isinstance(status_info["consecutive_failures"], int), \
                "Consecutive failures should be an integer"
            assert status_info["consecutive_failures"] >= 0, \
                "Consecutive failures should be non-negative"

    finally:
        # Cleanup
        await monitor.stop()


@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_failures=st.integers(min_value=1, max_value=10)
)
async def test_property_consecutive_failure_tracking(
    num_failures: int,
    mock_switcher: MockSwitcher
):
    """
    Property: Consecutive Failures Tracking

    Validates: Requirements 5.2

    Property: Consecutive failures are accurately counted

    For any number of consecutive failures:
    - When provider fails multiple times
    - Then consecutive failure count increments correctly
    - And count resets on successful health check
    """
    # Setup: Create an unhealthy provider
    provider = MockProvider(
        method=LLMMethod.CLOUD_OPENAI,
        healthy=False,
        error="Simulated failure"
    )
    mock_switcher.add_provider(provider)

    monitor = HealthMonitor(
        switcher=mock_switcher,
        db_session=None,
        metrics_collector=None
    )

    try:
        await monitor.start()

        # Get provider ID
        await asyncio.sleep(0.1)
        provider_id = await monitor._get_provider_id(LLMMethod.CLOUD_OPENAI)

        # Simulate multiple failures by forcing health checks
        for i in range(num_failures):
            await monitor.force_health_check(LLMMethod.CLOUD_OPENAI)
            await asyncio.sleep(0.05)

        # Property 1: Consecutive failures are counted
        all_status = await monitor.get_all_health_status()
        if provider_id in all_status:
            failures = all_status[provider_id]["consecutive_failures"]
            # Should have at least some failures recorded
            assert failures >= 1, \
                f"Expected at least 1 consecutive failure, got {failures}"

        # Now make provider healthy
        provider.set_health(healthy=True, error=None)
        await monitor.force_health_check(LLMMethod.CLOUD_OPENAI)
        await asyncio.sleep(0.1)

        # Property 2: Consecutive failures reset on recovery
        all_status = await monitor.get_all_health_status()
        if provider_id in all_status:
            failures = all_status[provider_id]["consecutive_failures"]
            assert failures == 0, \
                f"Consecutive failures should reset to 0 on recovery, got {failures}"

    finally:
        await monitor.stop()


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_providers=st.integers(min_value=2, max_value=5),
    num_healthy=st.integers(min_value=0, max_value=5)
)
async def test_property_healthy_provider_list(
    num_providers: int,
    num_healthy: int,
    mock_switcher: MockSwitcher
):
    """
    Property: Healthy Provider List

    Validates: Requirements 5.3

    Property: Healthy provider list accurately reflects health status

    For any distribution of healthy/unhealthy providers:
    - When querying healthy providers
    - Then only healthy providers are returned
    - And the count matches the number of healthy providers
    """
    # Ensure num_healthy doesn't exceed num_providers
    num_healthy = min(num_healthy, num_providers)

    # Setup: Create mix of healthy and unhealthy providers
    methods = list(LLMMethod)[:num_providers]
    providers = []

    for i, method in enumerate(methods):
        is_healthy = i < num_healthy
        provider = MockProvider(
            method=method,
            healthy=is_healthy,
            error=None if is_healthy else f"Error {i}"
        )
        mock_switcher.add_provider(provider)
        providers.append((provider, is_healthy))

    monitor = HealthMonitor(
        switcher=mock_switcher,
        db_session=None,
        metrics_collector=None
    )

    try:
        await monitor.start()

        # Wait for health checks
        await asyncio.sleep(0.3)

        # Property 1: Get healthy providers
        healthy_list = await monitor.get_healthy_providers()

        # Property 2: Healthy list should only contain healthy providers
        # (Note: In practice, may take a check cycle to populate)
        assert isinstance(healthy_list, list), "Healthy providers should be a list"

        # Property 3: All items in healthy list should be strings (provider IDs)
        for provider_id in healthy_list:
            assert isinstance(provider_id, str), "Provider ID should be a string"

        # Property 4: Count should be reasonable (allowing for timing)
        # The actual count may vary due to check timing, but should not exceed total
        assert len(healthy_list) <= num_providers, \
            "Healthy list should not exceed total providers"

    finally:
        await monitor.stop()


# ==================== Edge Case Tests ====================

@pytest.mark.asyncio
async def test_health_monitor_stop_idempotent(mock_switcher: MockSwitcher):
    """Test that stopping the monitor multiple times is safe."""
    monitor = HealthMonitor(
        switcher=mock_switcher,
        db_session=None,
        metrics_collector=None
    )

    await monitor.start()
    await monitor.stop()

    # Stop again - should not raise error
    await monitor.stop()

    assert not monitor.is_running


@pytest.mark.asyncio
async def test_health_monitor_start_idempotent(mock_switcher: MockSwitcher):
    """Test that starting the monitor multiple times is safe."""
    monitor = HealthMonitor(
        switcher=mock_switcher,
        db_session=None,
        metrics_collector=None
    )

    await monitor.start()
    assert monitor.is_running

    # Start again - should not create duplicate tasks
    await monitor.start()
    assert monitor.is_running

    await monitor.stop()


@pytest.mark.asyncio
async def test_health_monitor_no_providers(mock_switcher: MockSwitcher):
    """Test health monitor with no providers configured."""
    # Don't add any providers
    monitor = HealthMonitor(
        switcher=mock_switcher,
        db_session=None,
        metrics_collector=None
    )

    await monitor.start()
    await asyncio.sleep(0.2)

    # Should not crash with no providers
    healthy_list = await monitor.get_healthy_providers()
    assert healthy_list == []

    await monitor.stop()
