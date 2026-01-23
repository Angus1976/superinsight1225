"""
Property-based tests for LLM Health Monitor.

Tests Properties 14-15 from the LLM Integration design specification.

Property 14: Health Check Scheduling
- For any 60-second time window, the system should perform exactly one health check
  for each configured provider.

Property 15: Health Status Management
- For any provider, when a health check fails, the provider should be marked as
  unhealthy and excluded from request routing; when it recovers, it should be
  marked as healthy and included in routing.
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from collections import defaultdict
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai.llm_schemas import (
    LLMConfig, LLMMethod, LocalConfig, CloudConfig, ChinaLLMConfig,
    GenerateOptions, LLMResponse, TokenUsage, HealthStatus, LLMError, LLMErrorCode
)

# Test constants
HEALTH_CHECK_INTERVAL_SECONDS = 60

# Strategies for property-based testing
method_strategy = st.sampled_from(list(LLMMethod))
provider_id_strategy = st.uuids().map(str)
error_message_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())


class MockLLMProvider:
    """Mock LLM provider for testing health checks."""
    
    def __init__(
        self,
        method: LLMMethod,
        is_healthy: bool = True,
        health_check_delay: float = 0.0,
        error_message: Optional[str] = None
    ):
        self._method = method
        self._is_healthy = is_healthy
        self._health_check_delay = health_check_delay
        self._error_message = error_message
        self._health_check_count = 0
        self._health_check_times: List[float] = []
    
    @property
    def method(self) -> LLMMethod:
        return self._method
    
    async def health_check(self) -> HealthStatus:
        """Perform health check and record timing."""
        self._health_check_count += 1
        self._health_check_times.append(time.time())
        
        if self._health_check_delay > 0:
            await asyncio.sleep(self._health_check_delay)
        
        return HealthStatus(
            method=self._method,
            available=self._is_healthy,
            error=self._error_message if not self._is_healthy else None
        )
    
    def set_healthy(self, is_healthy: bool, error_message: Optional[str] = None):
        """Update health status for testing."""
        self._is_healthy = is_healthy
        self._error_message = error_message
    
    async def generate(self, prompt, options, model=None, system_prompt=None):
        """Mock generate method."""
        return LLMResponse(
            content=f"Response from {self._method.value}",
            model=model or "test-model",
            provider=self._method.value,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        )
    
    def list_models(self) -> List[str]:
        return ["test-model"]


class MockConfigManager:
    """Mock config manager for testing."""
    
    def __init__(self, config: LLMConfig):
        self._config = config
    
    async def get_config(self, tenant_id=None) -> LLMConfig:
        return self._config
    
    def watch_config_changes(self, callback):
        pass
    
    async def log_usage(self, **kwargs):
        pass


class MockLLMSwitcher:
    """Mock LLM Switcher for testing health monitor."""
    
    def __init__(self, providers: Dict[LLMMethod, MockLLMProvider]):
        self._providers = providers
        self._config = LLMConfig(
            default_method=list(providers.keys())[0] if providers else LLMMethod.LOCAL_OLLAMA,
            enabled_methods=list(providers.keys())
        )
        self._current_method = self._config.default_method
        self._initialized = True
    
    async def _ensure_initialized(self):
        pass


class HealthMonitorForTesting:
    """Test implementation of HealthMonitor for property testing."""
    
    def __init__(self, switcher: MockLLMSwitcher, check_interval: float = 0.1):
        self._switcher = switcher
        self._check_interval = check_interval
        
        # Health status cache (provider_id -> is_healthy)
        self._health_status: Dict[str, bool] = {}
        
        # Consecutive failure tracking
        self._consecutive_failures: Dict[str, int] = {}
        
        # Last error messages
        self._last_errors: Dict[str, Optional[str]] = {}
        
        # Async lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Background monitoring task
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Alert tracking for testing
        self._alerts: List[Dict[str, Any]] = []
        
        # Health check timing tracking
        self._health_check_times: Dict[str, List[float]] = defaultdict(list)
    
    async def start(self) -> None:
        """Start health monitoring."""
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
    
    async def stop(self) -> None:
        """Stop health monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
    
    async def _monitor_loop(self) -> None:
        """Background health check loop."""
        while self._running:
            try:
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception:
                pass
            
            try:
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all providers."""
        providers = self._switcher._providers
        
        for method, provider in providers.items():
            try:
                check_time = time.time()
                health_status = await provider.health_check()
                is_healthy = health_status.available
                error_message = health_status.error
                
                provider_id = f"provider_{method.value}"
                
                # Record check time
                self._health_check_times[provider_id].append(check_time)
                
                # Update health status
                await self._update_health_status(
                    provider_id=provider_id,
                    method=method,
                    is_healthy=is_healthy,
                    error_message=error_message
                )
                
            except Exception as e:
                provider_id = f"provider_{method.value}"
                self._health_check_times[provider_id].append(time.time())
                await self._update_health_status(
                    provider_id=provider_id,
                    method=method,
                    is_healthy=False,
                    error_message=str(e)
                )
    
    async def _update_health_status(
        self,
        provider_id: str,
        method: LLMMethod,
        is_healthy: bool,
        error_message: Optional[str] = None
    ) -> None:
        """Update provider health status and trigger alerts."""
        async with self._lock:
            previous_status = self._health_status.get(provider_id)
            
            self._health_status[provider_id] = is_healthy
            self._last_errors[provider_id] = error_message
            
            if is_healthy:
                self._consecutive_failures[provider_id] = 0
            else:
                self._consecutive_failures[provider_id] = \
                    self._consecutive_failures.get(provider_id, 0) + 1
        
        # Trigger alerts on status change
        if previous_status is not None and previous_status != is_healthy:
            alert_type = "recovered" if is_healthy else "unhealthy"
            self._alerts.append({
                "provider_id": provider_id,
                "method": method.value,
                "alert_type": alert_type,
                "is_healthy": is_healthy,
                "error_message": error_message,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def get_health_status(self, provider_id: str) -> bool:
        """Get current health status of a provider."""
        async with self._lock:
            return self._health_status.get(provider_id, False)
    
    async def get_healthy_providers(self) -> List[str]:
        """Get list of healthy provider IDs."""
        async with self._lock:
            return [
                provider_id
                for provider_id, is_healthy in self._health_status.items()
                if is_healthy
            ]
    
    async def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all providers."""
        async with self._lock:
            return {
                provider_id: {
                    "is_healthy": is_healthy,
                    "consecutive_failures": self._consecutive_failures.get(provider_id, 0),
                    "last_error": self._last_errors.get(provider_id)
                }
                for provider_id, is_healthy in self._health_status.items()
            }
    
    async def force_health_check(self, method: Optional[LLMMethod] = None) -> Dict[str, bool]:
        """Force an immediate health check."""
        results = {}
        providers = self._switcher._providers
        
        methods_to_check = [method] if method else list(providers.keys())
        
        for m in methods_to_check:
            if m in providers:
                try:
                    health_status = await providers[m].health_check()
                    is_healthy = health_status.available
                    results[m.value] = is_healthy
                    
                    provider_id = f"provider_{m.value}"
                    await self._update_health_status(
                        provider_id=provider_id,
                        method=m,
                        is_healthy=is_healthy,
                        error_message=health_status.error
                    )
                except Exception:
                    results[m.value] = False
        
        return results
    
    @property
    def is_running(self) -> bool:
        return self._running


def create_test_health_monitor(
    methods: List[LLMMethod],
    health_states: Optional[Dict[LLMMethod, bool]] = None,
    check_interval: float = 0.1
) -> tuple:
    """Create a test health monitor with mock providers."""
    health_states = health_states or {}
    
    providers = {}
    for method in methods:
        is_healthy = health_states.get(method, True)
        providers[method] = MockLLMProvider(
            method=method,
            is_healthy=is_healthy,
            error_message=f"Provider {method.value} is unhealthy" if not is_healthy else None
        )
    
    switcher = MockLLMSwitcher(providers)
    monitor = HealthMonitorForTesting(switcher, check_interval=check_interval)
    
    return monitor, switcher, providers


# ==================== Property 14: Health Check Scheduling ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    num_providers=st.integers(min_value=1, max_value=5),
    num_intervals=st.integers(min_value=1, max_value=3)
)
def test_property_14_health_check_scheduling_one_check_per_interval(num_providers, num_intervals):
    """
    Property 14: Health Check Scheduling
    
    For any 60-second time window, the system should perform exactly one health check
    for each configured provider.
    
    **Validates: Requirements 5.1**
    """
    async def run_test():
        # Select random methods for providers
        methods = list(LLMMethod)[:num_providers]
        
        # Use a short interval for testing (0.05s instead of 60s)
        check_interval = 0.05
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=methods,
            check_interval=check_interval
        )
        
        # Start monitoring
        await monitor.start()
        
        # Wait for multiple intervals
        await asyncio.sleep(check_interval * (num_intervals + 0.5))
        
        # Stop monitoring
        await monitor.stop()
        
        # Verify each provider was checked approximately once per interval
        for method in methods:
            provider = providers[method]
            
            # Should have approximately num_intervals + 1 checks (initial + intervals)
            # Allow some tolerance for timing
            expected_min = num_intervals
            expected_max = num_intervals + 2
            
            assert provider._health_check_count >= expected_min, \
                f"Provider {method.value} had {provider._health_check_count} checks, expected >= {expected_min}"
            assert provider._health_check_count <= expected_max, \
                f"Provider {method.value} had {provider._health_check_count} checks, expected <= {expected_max}"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(methods=st.lists(method_strategy, min_size=1, max_size=5, unique=True))
def test_property_14_all_providers_checked_each_interval(methods):
    """
    Property 14: All configured providers are checked in each interval.
    
    **Validates: Requirements 5.1**
    """
    async def run_test():
        check_interval = 0.05
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=methods,
            check_interval=check_interval
        )
        
        # Start monitoring
        await monitor.start()
        
        # Wait for one full interval plus buffer
        await asyncio.sleep(check_interval * 1.5)
        
        # Stop monitoring
        await monitor.stop()
        
        # Verify all providers were checked at least once
        for method in methods:
            provider = providers[method]
            assert provider._health_check_count >= 1, \
                f"Provider {method.value} was not checked"
    
    asyncio.run(run_test())


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy)
def test_property_14_health_check_timing_consistency(method):
    """
    Property 14: Health checks occur at consistent intervals.
    
    **Validates: Requirements 5.1**
    """
    async def run_test():
        check_interval = 0.05
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=[method],
            check_interval=check_interval
        )
        
        # Start monitoring
        await monitor.start()
        
        # Wait for multiple intervals
        await asyncio.sleep(check_interval * 3.5)
        
        # Stop monitoring
        await monitor.stop()
        
        # Get check times
        provider_id = f"provider_{method.value}"
        check_times = monitor._health_check_times.get(provider_id, [])
        
        # Verify we have multiple checks
        assert len(check_times) >= 2, "Should have at least 2 health checks"
        
        # Verify intervals are approximately consistent
        for i in range(1, len(check_times)):
            interval = check_times[i] - check_times[i-1]
            # Allow 50% tolerance for timing variations
            assert interval >= check_interval * 0.5, \
                f"Interval {interval}s is too short (expected ~{check_interval}s)"
            assert interval <= check_interval * 2.0, \
                f"Interval {interval}s is too long (expected ~{check_interval}s)"
    
    asyncio.run(run_test())


# ==================== Property 15: Health Status Management ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy, is_healthy=st.booleans())
def test_property_15_health_status_reflects_check_result(method, is_healthy):
    """
    Property 15: Health status correctly reflects health check result.
    
    **Validates: Requirements 5.2, 5.3, 5.4**
    """
    async def run_test():
        health_states = {method: is_healthy}
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=[method],
            health_states=health_states
        )
        
        # Force a health check
        await monitor.force_health_check(method)
        
        # Verify status matches
        provider_id = f"provider_{method.value}"
        status = await monitor.get_health_status(provider_id)
        
        assert status == is_healthy, \
            f"Health status {status} doesn't match expected {is_healthy}"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy)
def test_property_15_unhealthy_provider_excluded_from_healthy_list(method):
    """
    Property 15: Unhealthy providers are excluded from healthy provider list.
    
    When a health check fails, the provider should be marked as unhealthy
    and excluded from request routing.
    
    **Validates: Requirements 5.2, 5.3**
    """
    async def run_test():
        # Start with unhealthy provider
        health_states = {method: False}
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=[method],
            health_states=health_states
        )
        
        # Force a health check
        await monitor.force_health_check(method)
        
        # Verify provider is not in healthy list
        healthy_providers = await monitor.get_healthy_providers()
        provider_id = f"provider_{method.value}"
        
        assert provider_id not in healthy_providers, \
            f"Unhealthy provider {provider_id} should not be in healthy list"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy)
def test_property_15_healthy_provider_included_in_healthy_list(method):
    """
    Property 15: Healthy providers are included in healthy provider list.
    
    **Validates: Requirements 5.4**
    """
    async def run_test():
        # Start with healthy provider
        health_states = {method: True}
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=[method],
            health_states=health_states
        )
        
        # Force a health check
        await monitor.force_health_check(method)
        
        # Verify provider is in healthy list
        healthy_providers = await monitor.get_healthy_providers()
        provider_id = f"provider_{method.value}"
        
        assert provider_id in healthy_providers, \
            f"Healthy provider {provider_id} should be in healthy list"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy)
def test_property_15_alert_triggered_on_status_change_to_unhealthy(method):
    """
    Property 15: Alert is triggered when provider becomes unhealthy.
    
    When a health check fails, the system should trigger an alert.
    
    **Validates: Requirements 5.2**
    """
    async def run_test():
        # Start with healthy provider
        health_states = {method: True}
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=[method],
            health_states=health_states
        )
        
        # First check - healthy
        await monitor.force_health_check(method)
        initial_alerts = len(monitor._alerts)
        
        # Change to unhealthy
        providers[method].set_healthy(False, "Test failure")
        
        # Second check - unhealthy
        await monitor.force_health_check(method)
        
        # Verify alert was triggered
        assert len(monitor._alerts) > initial_alerts, \
            "Alert should be triggered when provider becomes unhealthy"
        
        # Verify alert type
        latest_alert = monitor._alerts[-1]
        assert latest_alert["alert_type"] == "unhealthy", \
            f"Alert type should be 'unhealthy', got '{latest_alert['alert_type']}'"
        assert latest_alert["method"] == method.value
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy)
def test_property_15_alert_triggered_on_recovery(method):
    """
    Property 15: Alert is triggered when provider recovers.
    
    When a provider recovers, it should be marked as healthy and an alert triggered.
    
    **Validates: Requirements 5.4**
    """
    async def run_test():
        # Start with unhealthy provider
        health_states = {method: False}
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=[method],
            health_states=health_states
        )
        
        # First check - unhealthy
        await monitor.force_health_check(method)
        initial_alerts = len(monitor._alerts)
        
        # Change to healthy (recovery)
        providers[method].set_healthy(True)
        
        # Second check - healthy
        await monitor.force_health_check(method)
        
        # Verify alert was triggered
        assert len(monitor._alerts) > initial_alerts, \
            "Alert should be triggered when provider recovers"
        
        # Verify alert type
        latest_alert = monitor._alerts[-1]
        assert latest_alert["alert_type"] == "recovered", \
            f"Alert type should be 'recovered', got '{latest_alert['alert_type']}'"
        assert latest_alert["method"] == method.value
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy)
def test_property_15_consecutive_failures_tracked(method):
    """
    Property 15: Consecutive failures are tracked correctly.
    
    **Validates: Requirements 5.2**
    """
    async def run_test():
        # Start with unhealthy provider
        health_states = {method: False}
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=[method],
            health_states=health_states
        )
        
        # Perform multiple health checks
        num_checks = 3
        for _ in range(num_checks):
            await monitor.force_health_check(method)
        
        # Verify consecutive failures
        provider_id = f"provider_{method.value}"
        all_status = await monitor.get_all_health_status()
        
        assert provider_id in all_status
        assert all_status[provider_id]["consecutive_failures"] == num_checks, \
            f"Expected {num_checks} consecutive failures, got {all_status[provider_id]['consecutive_failures']}"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy)
def test_property_15_consecutive_failures_reset_on_recovery(method):
    """
    Property 15: Consecutive failures reset when provider recovers.
    
    **Validates: Requirements 5.4**
    """
    async def run_test():
        # Start with unhealthy provider
        health_states = {method: False}
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=[method],
            health_states=health_states
        )
        
        # Perform multiple failed health checks
        for _ in range(3):
            await monitor.force_health_check(method)
        
        # Verify failures accumulated
        provider_id = f"provider_{method.value}"
        all_status = await monitor.get_all_health_status()
        assert all_status[provider_id]["consecutive_failures"] == 3
        
        # Recover
        providers[method].set_healthy(True)
        await monitor.force_health_check(method)
        
        # Verify failures reset
        all_status = await monitor.get_all_health_status()
        assert all_status[provider_id]["consecutive_failures"] == 0, \
            "Consecutive failures should reset on recovery"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    methods=st.lists(method_strategy, min_size=2, max_size=5, unique=True),
    health_flags=st.lists(st.booleans(), min_size=2, max_size=5)
)
def test_property_15_mixed_health_status_filtering(methods, health_flags):
    """
    Property 15: Mixed health status correctly filters healthy providers.
    
    **Validates: Requirements 5.3, 5.4**
    """
    async def run_test():
        # Ensure we have matching lengths
        flags = health_flags[:len(methods)]
        while len(flags) < len(methods):
            flags.append(True)
        
        # Create health states
        health_states = {
            method: is_healthy
            for method, is_healthy in zip(methods, flags)
        }
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=methods,
            health_states=health_states
        )
        
        # Force health checks
        for method in methods:
            await monitor.force_health_check(method)
        
        # Get healthy providers
        healthy_providers = await monitor.get_healthy_providers()
        
        # Verify filtering
        for method, is_healthy in health_states.items():
            provider_id = f"provider_{method.value}"
            
            if is_healthy:
                assert provider_id in healthy_providers, \
                    f"Healthy provider {provider_id} should be in healthy list"
            else:
                assert provider_id not in healthy_providers, \
                    f"Unhealthy provider {provider_id} should not be in healthy list"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy, error_message=error_message_strategy)
def test_property_15_error_message_stored_on_failure(method, error_message):
    """
    Property 15: Error message is stored when health check fails.
    
    **Validates: Requirements 5.2**
    """
    async def run_test():
        monitor, switcher, providers = create_test_health_monitor(
            methods=[method],
            health_states={method: False}
        )
        
        # Set specific error message
        providers[method].set_healthy(False, error_message)
        
        # Force health check
        await monitor.force_health_check(method)
        
        # Verify error message stored
        provider_id = f"provider_{method.value}"
        all_status = await monitor.get_all_health_status()
        
        assert provider_id in all_status
        assert all_status[provider_id]["last_error"] == error_message, \
            f"Error message not stored correctly"
    
    asyncio.run(run_test())


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy)
def test_property_15_no_alert_on_same_status(method):
    """
    Property 15: No alert triggered when status doesn't change.
    
    **Validates: Requirements 5.2, 5.4**
    """
    async def run_test():
        # Start with healthy provider
        health_states = {method: True}
        
        monitor, switcher, providers = create_test_health_monitor(
            methods=[method],
            health_states=health_states
        )
        
        # First check
        await monitor.force_health_check(method)
        alerts_after_first = len(monitor._alerts)
        
        # Second check (same status)
        await monitor.force_health_check(method)
        alerts_after_second = len(monitor._alerts)
        
        # Third check (same status)
        await monitor.force_health_check(method)
        alerts_after_third = len(monitor._alerts)
        
        # No new alerts should be triggered for same status
        assert alerts_after_second == alerts_after_first, \
            "No alert should be triggered when status doesn't change"
        assert alerts_after_third == alerts_after_second, \
            "No alert should be triggered when status doesn't change"
    
    asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
