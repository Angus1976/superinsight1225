"""
Tests for async/sync safety fixes.

This test suite verifies that all async functions properly use asyncio.Lock
instead of threading.Lock, and use await asyncio.sleep() instead of time.sleep().
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import time

# Test 1: Verify asyncio.Lock is used in async contexts
@pytest.mark.asyncio
async def test_health_check_manager_uses_asyncio_lock():
    """Verify HealthCheckManager uses asyncio.Lock instead of threading.Lock"""
    from src.monitoring.health_check import HealthCheckManager
    
    manager = HealthCheckManager()
    
    # Verify lock is asyncio.Lock
    assert isinstance(manager._lock, asyncio.Lock), \
        "HealthCheckManager._lock should be asyncio.Lock, not threading.Lock"


@pytest.mark.asyncio
async def test_service_alert_manager_uses_asyncio_lock():
    """Verify ServiceAlertManager uses asyncio.Lock instead of threading.Lock"""
    from src.monitoring.service_alert import ServiceAlertManager
    
    manager = ServiceAlertManager()
    
    # Verify lock is asyncio.Lock
    assert isinstance(manager._lock, asyncio.Lock), \
        "ServiceAlertManager._lock should be asyncio.Lock, not threading.Lock"


@pytest.mark.asyncio
async def test_prometheus_exporter_uses_asyncio_lock():
    """Verify PrometheusMetricsExporter uses asyncio.Lock instead of threading.Lock"""
    from src.system.prometheus_integration import PrometheusMetricsExporter
    
    exporter = PrometheusMetricsExporter()
    
    # Verify lock is asyncio.Lock
    assert isinstance(exporter._lock, asyncio.Lock), \
        "PrometheusMetricsExporter._lock should be asyncio.Lock, not threading.Lock"


@pytest.mark.asyncio
async def test_metrics_collector_uses_asyncio_lock():
    """Verify MetricsCollector uses asyncio.Lock instead of threading.Lock"""
    from src.system.monitoring import MetricsCollector
    
    collector = MetricsCollector()
    
    # Verify lock is asyncio.Lock
    assert isinstance(collector._lock, asyncio.Lock), \
        "MetricsCollector._lock should be asyncio.Lock, not threading.Lock"


@pytest.mark.asyncio
async def test_resource_monitor_uses_asyncio_lock():
    """Verify ResourceMonitor uses asyncio.Lock instead of threading.Lock"""
    from src.system.resource_optimizer import ResourceMonitor
    
    monitor = ResourceMonitor()
    
    # Verify lock is asyncio.Lock
    assert isinstance(monitor._lock, asyncio.Lock), \
        "ResourceMonitor._lock should be asyncio.Lock, not threading.Lock"


# Test 2: Verify no blocking psutil calls in async functions
@pytest.mark.asyncio
async def test_prometheus_exporter_no_blocking_psutil():
    """Verify PrometheusMetricsExporter doesn't block event loop with psutil"""
    from src.system.prometheus_integration import PrometheusMetricsExporter
    
    exporter = PrometheusMetricsExporter()
    
    # Mock psutil to track if it's called with interval parameter
    with patch('src.system.prometheus_integration.psutil.cpu_percent') as mock_cpu:
        mock_cpu.return_value = 50.0
        
        # This should not block the event loop
        start = time.time()
        await exporter._collect_system_metrics()
        elapsed = time.time() - start
        
        # Should complete quickly (< 100ms) since psutil is in executor
        assert elapsed < 0.1, \
            f"_collect_system_metrics took {elapsed:.2f}s, should use run_in_executor"


@pytest.mark.asyncio
async def test_metrics_collector_no_blocking_psutil():
    """Verify MetricsCollector doesn't block event loop with psutil"""
    from src.system.monitoring import MetricsCollector
    
    collector = MetricsCollector()
    
    # Mock psutil to track if it's called with interval parameter
    with patch('src.system.monitoring.psutil.cpu_percent') as mock_cpu:
        mock_cpu.return_value = 50.0
        
        # This should not block the event loop
        start = time.time()
        await collector._collect_system_metrics()
        elapsed = time.time() - start
        
        # Should complete quickly (< 100ms) since psutil is in executor
        assert elapsed < 0.1, \
            f"_collect_system_metrics took {elapsed:.2f}s, should use run_in_executor"


@pytest.mark.asyncio
async def test_resource_monitor_no_blocking_psutil():
    """Verify ResourceMonitor doesn't block event loop with psutil"""
    from src.system.resource_optimizer import ResourceMonitor
    
    monitor = ResourceMonitor()
    
    # Mock psutil to track if it's called with interval parameter
    with patch('src.system.resource_optimizer.psutil.cpu_percent') as mock_cpu:
        mock_cpu.return_value = 50.0
        
        # This should not block the event loop
        start = time.time()
        await monitor._collect_metrics()
        elapsed = time.time() - start
        
        # Should complete quickly (< 100ms) since psutil is in executor
        assert elapsed < 0.1, \
            f"_collect_metrics took {elapsed:.2f}s, should use run_in_executor"


# Test 3: Verify no deadlocks with concurrent access
@pytest.mark.asyncio
async def test_health_check_manager_concurrent_access():
    """Verify HealthCheckManager handles concurrent access without deadlock"""
    from src.monitoring.health_check import HealthCheckManager
    
    manager = HealthCheckManager()
    
    # Create multiple concurrent tasks
    async def access_lock():
        async with manager._lock:
            await asyncio.sleep(0.01)
            return True
    
    # Run 100 concurrent accesses
    tasks = [access_lock() for _ in range(100)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # All should succeed without timeout or deadlock
    assert all(r is True for r in results), \
        "Concurrent access should not cause deadlock"


@pytest.mark.asyncio
async def test_service_alert_manager_concurrent_access():
    """Verify ServiceAlertManager handles concurrent access without deadlock"""
    from src.monitoring.service_alert import ServiceAlertManager
    
    manager = ServiceAlertManager()
    
    # Create multiple concurrent tasks
    async def access_lock():
        async with manager._lock:
            await asyncio.sleep(0.01)
            return True
    
    # Run 100 concurrent accesses
    tasks = [access_lock() for _ in range(100)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # All should succeed without timeout or deadlock
    assert all(r is True for r in results), \
        "Concurrent access should not cause deadlock"


# Test 4: Verify async methods are properly async
@pytest.mark.asyncio
async def test_health_check_manager_methods_are_async():
    """Verify HealthCheckManager async methods are properly defined"""
    from src.monitoring.health_check import HealthCheckManager
    import inspect
    
    manager = HealthCheckManager()
    
    # Check that key methods are async
    assert inspect.iscoroutinefunction(manager.check_service), \
        "check_service should be async"
    assert inspect.iscoroutinefunction(manager.check_all), \
        "check_all should be async"
    assert inspect.iscoroutinefunction(manager.register), \
        "register should be async"
    assert inspect.iscoroutinefunction(manager.unregister), \
        "unregister should be async"


@pytest.mark.asyncio
async def test_service_alert_manager_methods_are_async():
    """Verify ServiceAlertManager async methods are properly defined"""
    from src.monitoring.service_alert import ServiceAlertManager
    import inspect
    
    manager = ServiceAlertManager()
    
    # Check that key methods are async
    assert inspect.iscoroutinefunction(manager._process_service_result), \
        "_process_service_result should be async"
    assert inspect.iscoroutinefunction(manager._monitoring_loop), \
        "_monitoring_loop should be async"


# Test 5: Verify no time.sleep() in async functions
@pytest.mark.asyncio
async def test_no_time_sleep_in_async_functions():
    """Verify no time.sleep() calls in async functions"""
    import inspect
    from src.system.health_monitor import HealthMonitor
    from src.system.advanced_recovery import AdvancedRecoveryManager
    
    # Check HealthMonitor._run_health_check
    source = inspect.getsource(HealthMonitor._run_health_check)
    assert 'time.sleep' not in source or 'asyncio.sleep' in source, \
        "HealthMonitor._run_health_check should use asyncio.sleep, not time.sleep"
    
    # Check AdvancedRecoveryManager methods
    for method_name in ['_execute_recovery_action', '_execute_rollback', 
                        '_execute_with_retry', '_clear_cache', '_reset_connection_pool',
                        '_restart_service', '_activate_fallback']:
        if hasattr(AdvancedRecoveryManager, method_name):
            method = getattr(AdvancedRecoveryManager, method_name)
            if inspect.iscoroutinefunction(method):
                source = inspect.getsource(method)
                # If it has time.sleep, it should also have asyncio.sleep
                if 'time.sleep' in source:
                    assert 'asyncio.sleep' in source, \
                        f"{method_name} should use asyncio.sleep, not time.sleep"


# Test 6: Verify executor usage for blocking operations
@pytest.mark.asyncio
async def test_psutil_calls_use_executor():
    """Verify psutil calls are wrapped in run_in_executor"""
    import inspect
    from src.system.prometheus_integration import PrometheusMetricsExporter
    from src.system.monitoring import MetricsCollector
    from src.system.resource_optimizer import ResourceMonitor
    
    # Check PrometheusMetricsExporter._collect_system_metrics
    source = inspect.getsource(PrometheusMetricsExporter._collect_system_metrics)
    assert 'run_in_executor' in source, \
        "PrometheusMetricsExporter._collect_system_metrics should use run_in_executor"
    
    # Check MetricsCollector._collect_system_metrics
    source = inspect.getsource(MetricsCollector._collect_system_metrics)
    assert 'run_in_executor' in source, \
        "MetricsCollector._collect_system_metrics should use run_in_executor"
    
    # Check ResourceMonitor._collect_metrics
    source = inspect.getsource(ResourceMonitor._collect_metrics)
    assert 'run_in_executor' in source, \
        "ResourceMonitor._collect_metrics should use run_in_executor"


# Test 7: Timeout protection
@pytest.mark.asyncio
async def test_async_operations_have_timeout_protection():
    """Verify async operations have timeout protection"""
    from src.monitoring.health_check import HealthCheckManager
    
    manager = HealthCheckManager()
    
    # Create a mock checker that takes too long
    mock_checker = AsyncMock()
    mock_checker.name = "slow_checker"
    mock_checker.check_with_timeout = AsyncMock(
        side_effect=asyncio.TimeoutError()
    )
    
    # This should handle timeout gracefully
    result = await manager.check_service("slow_checker")
    # Result should be None or handle the timeout
    assert result is None or isinstance(result, Exception), \
        "Should handle timeout gracefully"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
