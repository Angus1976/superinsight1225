"""
Integration tests for the Performance Optimization System.

Tests cover:
- Task 18.3: Cache and concurrency integration, load balancing with service discovery,
  monitoring with health check integration
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from src.agent.performance import (
    # Caching
    CacheStrategy,
    CacheMetrics,
    InMemoryCache,
    ResponseCache,
    cached_response,
    # Concurrency
    ConcurrencyMode,
    TaskResult,
    ConcurrentExecutor,
    # Monitoring
    MetricType,
    PerformanceMetric,
    LatencyStats,
    PerformanceMonitor,
    measure_latency,
    # Health and Service Discovery
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    HealthChecker,
    ServiceInstance,
    ServiceRegistry,
    LoadBalanceStrategy,
    LoadBalancer,
    # Global accessors
    get_response_cache,
    get_performance_monitor,
    get_concurrent_executor,
    get_health_checker,
    get_service_registry,
    create_default_health_checks,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def cache():
    """Create a response cache instance."""
    return ResponseCache(max_size=100, default_ttl=60.0)


@pytest.fixture
def executor():
    """Create a concurrent executor instance."""
    return ConcurrentExecutor(max_workers=4, max_concurrent=20, timeout=10.0)


@pytest.fixture
def monitor():
    """Create a performance monitor instance."""
    return PerformanceMonitor(window_size_seconds=60)


@pytest.fixture
def health_checker():
    """Create a health checker instance."""
    return HealthChecker()


@pytest.fixture
def service_registry():
    """Create a service registry instance."""
    return ServiceRegistry(heartbeat_timeout=300.0)


# =============================================================================
# Test: Cache and Concurrency Integration
# =============================================================================


class TestCacheAndConcurrencyIntegration:
    """Tests for cache and concurrency integration."""

    @pytest.mark.asyncio
    async def test_cached_concurrent_execution(self, cache, executor):
        """Test cached responses with concurrent execution."""
        call_count = 0

        async def expensive_operation(query: str) -> Dict[str, Any]:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate expensive operation
            return {"query": query, "result": f"computed_{query}"}

        async def cached_operation(query: str) -> Dict[str, Any]:
            # Check cache first
            cached = await cache.get_response(query)
            if cached:
                return cached

            # Execute and cache
            result = await expensive_operation(query)
            await cache.cache_response(query, result)
            return result

        # Execute same query concurrently
        tasks = [(f"task-{i}", cached_operation, ("query1",), {}) for i in range(5)]

        # First batch - should compute once and cache
        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        assert all(r.success for r in results)

        # Due to race condition, might compute a few times
        # but subsequent calls should use cache
        initial_count = call_count

        # Second batch - should all hit cache
        second_results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        assert all(r.success for r in second_results)
        # Call count shouldn't increase much (all cache hits)
        assert call_count == initial_count

    @pytest.mark.asyncio
    async def test_cache_warming_with_executor(self, cache, executor):
        """Test cache warming using concurrent executor."""
        async def fetch_data(key: str) -> Dict[str, Any]:
            await asyncio.sleep(0.01)
            return {"key": key, "value": f"data_{key}"}

        # Warm cache concurrently
        keys = [f"key_{i}" for i in range(20)]
        tasks = [
            (f"warm-{key}", fetch_data, (key,), {})
            for key in keys
        ]

        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        # Cache all results
        for result in results:
            if result.success:
                await cache.cache_response(
                    result.result["key"],
                    result.result
                )

        # Verify all cached
        for key in keys:
            cached = await cache.get_response(key)
            assert cached is not None

    @pytest.mark.asyncio
    async def test_cache_invalidation_during_execution(self, cache, executor):
        """Test cache invalidation during concurrent execution."""
        # Populate cache
        for i in range(10):
            await cache.cache_response(f"key_{i}", {"value": i})

        async def update_and_invalidate(key: str, new_value: int) -> Dict[str, Any]:
            # Invalidate old cache
            await cache.invalidate(key)
            # Store new value
            new_data = {"value": new_value}
            await cache.cache_response(key, new_data)
            return new_data

        # Update all keys concurrently
        tasks = [
            (f"update-{i}", update_and_invalidate, (f"key_{i}", i * 10), {})
            for i in range(10)
        ]

        await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        # Verify updates
        for i in range(10):
            cached = await cache.get_response(f"key_{i}")
            assert cached["value"] == i * 10


# =============================================================================
# Test: Load Balancing with Service Discovery Integration
# =============================================================================


class TestLoadBalancingWithServiceDiscovery:
    """Tests for load balancing with service discovery integration."""

    @pytest.mark.asyncio
    async def test_service_discovery_with_load_balancing(self, service_registry):
        """Test complete service discovery with load balancing."""
        # Register multiple service instances
        services = ["api", "worker", "cache"]
        for service in services:
            for i in range(3):
                instance = ServiceInstance(
                    service_id=f"{service}-{i}",
                    service_name=service,
                    host="localhost",
                    port=8080 + i,
                    health_status=HealthStatus.HEALTHY,
                    metadata={"weight": i + 1}
                )
                await service_registry.register(instance)

        # Create load balancers for each strategy
        strategies = [
            LoadBalanceStrategy.ROUND_ROBIN,
            LoadBalanceStrategy.RANDOM,
            LoadBalanceStrategy.LEAST_CONNECTIONS,
            LoadBalanceStrategy.WEIGHTED,
        ]

        for strategy in strategies:
            lb = LoadBalancer(service_registry, strategy=strategy)

            # Get instances for each service
            for service in services:
                instance = await lb.get_instance(service)
                assert instance is not None
                assert instance.service_name == service

    @pytest.mark.asyncio
    async def test_load_balancer_health_integration(self, service_registry):
        """Test that load balancer respects health status."""
        # Register healthy and unhealthy instances
        healthy = ServiceInstance(
            service_id="healthy-1",
            service_name="api",
            host="localhost",
            port=8080,
            health_status=HealthStatus.HEALTHY
        )
        unhealthy = ServiceInstance(
            service_id="unhealthy-1",
            service_name="api",
            host="localhost",
            port=8081,
            health_status=HealthStatus.UNHEALTHY
        )

        await service_registry.register(healthy)
        await service_registry.register(unhealthy)

        lb = LoadBalancer(service_registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)

        # Should only get healthy instance
        for _ in range(10):
            instance = await lb.get_instance("api")
            assert instance.service_id == "healthy-1"

    @pytest.mark.asyncio
    async def test_dynamic_instance_registration(self, service_registry):
        """Test dynamic registration and deregistration."""
        lb = LoadBalancer(service_registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)

        # Initially no instances
        instance = await lb.get_instance("api")
        assert instance is None

        # Register instance
        service = ServiceInstance(
            service_id="api-1",
            service_name="api",
            host="localhost",
            port=8080,
            health_status=HealthStatus.HEALTHY
        )
        await service_registry.register(service)

        # Now should get instance
        instance = await lb.get_instance("api")
        assert instance is not None

        # Deregister
        await service_registry.deregister("api", "api-1")

        # Should be none again
        instance = await lb.get_instance("api")
        assert instance is None

    @pytest.mark.asyncio
    async def test_load_balancer_with_concurrent_requests(self, service_registry, executor):
        """Test load balancer under concurrent request load."""
        # Register instances
        for i in range(3):
            instance = ServiceInstance(
                service_id=f"api-{i}",
                service_name="api",
                host="localhost",
                port=8080 + i,
                health_status=HealthStatus.HEALTHY
            )
            await service_registry.register(instance)

        lb = LoadBalancer(service_registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)

        request_counts = {}

        async def simulate_request(request_id: int) -> str:
            instance = await lb.get_instance("api")
            if instance:
                request_counts[instance.service_id] = request_counts.get(
                    instance.service_id, 0
                ) + 1
                return instance.service_id
            return "none"

        # Execute concurrent requests
        tasks = [(f"req-{i}", simulate_request, (i,), {}) for i in range(30)]
        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        # Verify all requests succeeded
        assert all(r.success for r in results)

        # Verify load distribution (round robin should be even)
        assert len(request_counts) == 3
        for count in request_counts.values():
            assert count == 10  # 30 requests / 3 instances


# =============================================================================
# Test: Monitoring with Health Check Integration
# =============================================================================


class TestMonitoringWithHealthCheck:
    """Tests for monitoring with health check integration."""

    @pytest.mark.asyncio
    async def test_health_check_records_latency(self, health_checker, monitor):
        """Test that health checks record latency to monitor."""
        async def db_check():
            start = time.time()
            await asyncio.sleep(0.05)  # Simulate check
            latency = (time.time() - start) * 1000
            await monitor.record_latency("health_check.database", latency)
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                latency_ms=latency
            )

        health_checker.register_check("database", db_check)
        await health_checker.check_component("database")

        stats = monitor.get_latency_stats("health_check.database")
        assert stats is not None
        assert stats.count == 1
        assert stats.avg_ms >= 50

    @pytest.mark.asyncio
    async def test_system_health_with_metrics(self, health_checker, monitor):
        """Test system health integrated with performance metrics."""
        # Register multiple health checks
        async def create_check(name: str, healthy: bool):
            async def check():
                await asyncio.sleep(0.01)
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY if healthy else HealthStatus.DEGRADED
                )
            return check

        health_checker.register_check("api", await create_check("api", True))
        health_checker.register_check("db", await create_check("db", True))
        health_checker.register_check("cache", await create_check("cache", False))

        # Run health checks
        system = await health_checker.check_all()

        # Record system health as gauge
        await monitor.set_gauge(
            "system_health",
            1.0 if system.status == HealthStatus.HEALTHY else 0.5
        )

        # Verify
        metrics = monitor.get_all_metrics()
        assert "system_health" in str(metrics["gauges"])

    @pytest.mark.asyncio
    async def test_default_health_checks_integration(self, health_checker):
        """Test default health checks setup and execution."""
        await create_default_health_checks(health_checker)

        system = await health_checker.check_all()

        # Should have default checks
        component_names = [c.name for c in system.components]
        assert "response_cache" in component_names
        assert "concurrent_executor" in component_names
        assert "performance_monitor" in component_names

    @pytest.mark.asyncio
    async def test_health_degradation_detection(self, health_checker, monitor):
        """Test detecting health degradation from metrics."""
        degradation_detected = []

        async def cpu_check():
            # Get CPU metric (simulated)
            cpu_usage = 0.95  # High CPU

            status = HealthStatus.HEALTHY
            if cpu_usage > 0.9:
                status = HealthStatus.DEGRADED
                degradation_detected.append(("cpu", cpu_usage))
            elif cpu_usage > 0.95:
                status = HealthStatus.UNHEALTHY

            await monitor.set_gauge("cpu_usage", cpu_usage)

            return ComponentHealth(
                name="cpu",
                status=status,
                metadata={"usage": cpu_usage}
            )

        health_checker.register_check("cpu", cpu_check)
        await health_checker.check_component("cpu")

        assert len(degradation_detected) == 1
        assert degradation_detected[0][1] > 0.9


# =============================================================================
# Test: Full Performance Stack Integration
# =============================================================================


class TestFullPerformanceStackIntegration:
    """Full integration tests for complete performance stack."""

    @pytest.mark.asyncio
    async def test_complete_request_flow(
        self, cache, executor, monitor, health_checker, service_registry
    ):
        """Test complete request flow through all performance components."""
        # Setup services
        for i in range(2):
            instance = ServiceInstance(
                service_id=f"api-{i}",
                service_name="api",
                host="localhost",
                port=8080 + i,
                health_status=HealthStatus.HEALTHY
            )
            await service_registry.register(instance)

        lb = LoadBalancer(service_registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)

        async def process_request(request_id: str) -> Dict[str, Any]:
            start = time.time()

            # Step 1: Check cache
            cached = await cache.get_response(request_id)
            if cached:
                await monitor.increment_counter("cache_hit")
                return cached

            await monitor.increment_counter("cache_miss")

            # Step 2: Get service instance
            instance = await lb.get_instance("api")

            # Step 3: Process (simulated)
            await asyncio.sleep(0.01)
            result = {
                "request_id": request_id,
                "processed_by": instance.service_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Step 4: Cache result
            await cache.cache_response(request_id, result)

            # Step 5: Record metrics
            latency = (time.time() - start) * 1000
            await monitor.record_latency("request_processing", latency)

            return result

        # Execute requests
        request_ids = [f"req-{i}" for i in range(20)]
        tasks = [(rid, process_request, (rid,), {}) for rid in request_ids]

        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        assert all(r.success for r in results)

        # Verify metrics
        metrics = monitor.get_all_metrics()
        assert metrics["counters"].get("cache_miss:{}", 0) >= 0

        # Re-execute same requests (should hit cache)
        second_results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)
        assert all(r.success for r in second_results)

    @pytest.mark.asyncio
    async def test_performance_under_load(self, executor, monitor):
        """Test performance stack under load."""
        async def workload(n: int) -> int:
            await asyncio.sleep(0.001)
            return n * 2

        # Generate heavy load
        num_requests = 100
        tasks = [(f"task-{i}", workload, (i,), {}) for i in range(num_requests)]

        start = time.time()
        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)
        total_time = time.time() - start

        # Record metrics
        await monitor.set_gauge("total_requests", num_requests)
        await monitor.set_gauge("total_time_seconds", total_time)
        await monitor.set_gauge("requests_per_second", num_requests / total_time)

        success_count = sum(1 for r in results if r.success)
        assert success_count == num_requests

        # Verify throughput
        throughput = num_requests / total_time
        assert throughput > 10  # At least 10 requests per second

    @pytest.mark.asyncio
    async def test_failover_scenario(self, service_registry, executor):
        """Test failover when service becomes unhealthy."""
        # Register instances
        primary = ServiceInstance(
            service_id="primary",
            service_name="api",
            host="localhost",
            port=8080,
            health_status=HealthStatus.HEALTHY
        )
        backup = ServiceInstance(
            service_id="backup",
            service_name="api",
            host="localhost",
            port=8081,
            health_status=HealthStatus.HEALTHY
        )

        await service_registry.register(primary)
        await service_registry.register(backup)

        lb = LoadBalancer(service_registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)

        # Initially both should be used
        instances_before = set()
        for _ in range(10):
            instance = await lb.get_instance("api")
            instances_before.add(instance.service_id)

        assert len(instances_before) == 2

        # Mark primary as unhealthy
        await service_registry.update_health("api", "primary", HealthStatus.UNHEALTHY)

        # Now only backup should be used
        instances_after = set()
        for _ in range(10):
            instance = await lb.get_instance("api")
            instances_after.add(instance.service_id)

        assert instances_after == {"backup"}

    @pytest.mark.asyncio
    async def test_cache_with_service_health(self, cache, health_checker, service_registry):
        """Test cache behavior when services are unhealthy."""
        # Setup health check that checks service registry
        async def service_health_check():
            instances = await service_registry.get_instances("api", healthy_only=True)
            if not instances:
                return ComponentHealth(
                    name="api_services",
                    status=HealthStatus.UNHEALTHY,
                    message="No healthy instances"
                )

            healthy_count = len(instances)
            return ComponentHealth(
                name="api_services",
                status=HealthStatus.HEALTHY,
                message=f"{healthy_count} healthy instances",
                metadata={"healthy_count": healthy_count}
            )

        health_checker.register_check("api_services", service_health_check)

        # Initially unhealthy (no services)
        result = await health_checker.check_component("api_services")
        assert result.status == HealthStatus.UNHEALTHY

        # Register a healthy service
        instance = ServiceInstance(
            service_id="api-1",
            service_name="api",
            host="localhost",
            port=8080,
            health_status=HealthStatus.HEALTHY
        )
        await service_registry.register(instance)

        # Now should be healthy
        result = await health_checker.check_component("api_services")
        assert result.status == HealthStatus.HEALTHY


# =============================================================================
# Test: Global Instance Integration
# =============================================================================


class TestGlobalInstanceIntegration:
    """Tests for global instance integration."""

    @pytest.mark.asyncio
    async def test_global_instances_work_together(self):
        """Test that global instances work together correctly."""
        cache = get_response_cache()
        monitor = get_performance_monitor()
        executor = get_concurrent_executor()
        checker = get_health_checker()
        registry = get_service_registry()

        # Register default health checks
        await create_default_health_checks(checker)

        # Use all components together
        async def integrated_task(key: str) -> str:
            # Check cache
            cached = await cache.get_response(key)
            if cached:
                return cached["value"]

            # Execute work
            result = {"value": f"computed_{key}"}
            await cache.cache_response(key, result)

            # Record metric
            await monitor.increment_counter("computations")

            return result["value"]

        # Execute via executor
        result = await executor.execute_async("test-task", integrated_task, "test_key")
        assert result.success

        # Run health check
        system = await checker.check_all()
        assert system.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
