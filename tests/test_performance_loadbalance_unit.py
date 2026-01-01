"""
Unit tests for the Performance Load Balancing and Service Discovery System.

Tests cover:
- Task 17.3: Service registration, load balancing strategies, heartbeat detection, service discovery
- Task 17.4: Property-based tests for load balancing fairness
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import random

from hypothesis import given, strategies as st, settings, assume

from src.agent.performance import (
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    HealthChecker,
    ServiceInstance,
    ServiceRegistry,
    LoadBalanceStrategy,
    LoadBalancer,
    get_health_checker,
    get_service_registry,
    create_default_health_checks,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def health_checker():
    """Create a health checker instance."""
    return HealthChecker()


@pytest.fixture
def service_registry():
    """Create a service registry instance."""
    return ServiceRegistry(heartbeat_timeout=30.0)


@pytest.fixture
def sample_service_instance():
    """Create a sample service instance."""
    return ServiceInstance(
        service_id="instance-1",
        service_name="api-service",
        host="localhost",
        port=8080,
        health_status=HealthStatus.HEALTHY,
        metadata={"weight": 1, "version": "1.0"}
    )


@pytest.fixture
def load_balancer(service_registry):
    """Create a load balancer instance."""
    return LoadBalancer(service_registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)


# =============================================================================
# Test: ComponentHealth
# =============================================================================


class TestComponentHealth:
    """Tests for ComponentHealth dataclass."""

    def test_component_health_creation(self):
        """Test creating component health."""
        health = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Connection OK",
            latency_ms=5.2
        )
        assert health.name == "database"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "Connection OK"
        assert health.latency_ms == 5.2

    def test_component_health_degraded(self):
        """Test degraded health status."""
        health = ComponentHealth(
            name="cache",
            status=HealthStatus.DEGRADED,
            message="High latency detected"
        )
        assert health.status == HealthStatus.DEGRADED

    def test_component_health_metadata(self):
        """Test health metadata."""
        health = ComponentHealth(
            name="api",
            status=HealthStatus.HEALTHY,
            metadata={"connections": 100, "requests_per_sec": 500}
        )
        assert health.metadata["connections"] == 100


# =============================================================================
# Test: SystemHealth
# =============================================================================


class TestSystemHealth:
    """Tests for SystemHealth dataclass."""

    def test_system_health_all_healthy(self):
        """Test system health when all components are healthy."""
        components = [
            ComponentHealth(name="db", status=HealthStatus.HEALTHY),
            ComponentHealth(name="cache", status=HealthStatus.HEALTHY),
            ComponentHealth(name="api", status=HealthStatus.HEALTHY),
        ]

        system = SystemHealth.aggregate(components)

        assert system.status == HealthStatus.HEALTHY
        assert len(system.components) == 3

    def test_system_health_some_degraded(self):
        """Test system health when some components are degraded."""
        components = [
            ComponentHealth(name="db", status=HealthStatus.HEALTHY),
            ComponentHealth(name="cache", status=HealthStatus.DEGRADED),
            ComponentHealth(name="api", status=HealthStatus.HEALTHY),
        ]

        system = SystemHealth.aggregate(components)

        assert system.status == HealthStatus.DEGRADED

    def test_system_health_some_unhealthy(self):
        """Test system health when some components are unhealthy."""
        components = [
            ComponentHealth(name="db", status=HealthStatus.HEALTHY),
            ComponentHealth(name="cache", status=HealthStatus.UNHEALTHY),
            ComponentHealth(name="api", status=HealthStatus.HEALTHY),
        ]

        system = SystemHealth.aggregate(components)

        assert system.status == HealthStatus.UNHEALTHY

    def test_system_health_empty_components(self):
        """Test system health with no components."""
        system = SystemHealth.aggregate([])
        assert system.status == HealthStatus.UNKNOWN

    def test_system_health_version(self):
        """Test system health version."""
        components = [ComponentHealth(name="db", status=HealthStatus.HEALTHY)]
        system = SystemHealth.aggregate(components, version="2.0.0")
        assert system.version == "2.0.0"


# =============================================================================
# Test: HealthChecker
# =============================================================================


class TestHealthChecker:
    """Tests for HealthChecker class."""

    @pytest.mark.asyncio
    async def test_register_check(self, health_checker):
        """Test registering a health check."""
        async def db_check():
            return ComponentHealth(name="db", status=HealthStatus.HEALTHY)

        health_checker.register_check("database", db_check)

        result = await health_checker.check_component("database")
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_nonexistent(self, health_checker):
        """Test checking non-existent component."""
        result = await health_checker.check_component("nonexistent")
        assert result.status == HealthStatus.UNKNOWN
        assert "No health check registered" in result.message

    @pytest.mark.asyncio
    async def test_check_timeout(self, health_checker):
        """Test health check timeout."""
        async def slow_check():
            await asyncio.sleep(10.0)
            return ComponentHealth(name="slow", status=HealthStatus.HEALTHY)

        health_checker.register_check("slow", slow_check)

        result = await health_checker.check_component("slow")
        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_exception(self, health_checker):
        """Test health check with exception."""
        async def failing_check():
            raise ConnectionError("Connection refused")

        health_checker.register_check("failing", failing_check)

        result = await health_checker.check_component("failing")
        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection refused" in result.message

    @pytest.mark.asyncio
    async def test_check_all(self, health_checker):
        """Test checking all components."""
        async def check_a():
            return ComponentHealth(name="a", status=HealthStatus.HEALTHY)

        async def check_b():
            return ComponentHealth(name="b", status=HealthStatus.HEALTHY)

        health_checker.register_check("component_a", check_a)
        health_checker.register_check("component_b", check_b)

        system = await health_checker.check_all()

        assert system.status == HealthStatus.HEALTHY
        assert len(system.components) == 2

    @pytest.mark.asyncio
    async def test_get_last_results(self, health_checker):
        """Test getting last results."""
        async def check():
            return ComponentHealth(name="test", status=HealthStatus.HEALTHY)

        health_checker.register_check("test", check)
        await health_checker.check_component("test")

        results = health_checker.get_last_results()
        assert "test" in results
        assert results["test"].status == HealthStatus.HEALTHY


# =============================================================================
# Test: ServiceInstance
# =============================================================================


class TestServiceInstance:
    """Tests for ServiceInstance dataclass."""

    def test_service_instance_creation(self, sample_service_instance):
        """Test creating a service instance."""
        assert sample_service_instance.service_id == "instance-1"
        assert sample_service_instance.service_name == "api-service"
        assert sample_service_instance.host == "localhost"
        assert sample_service_instance.port == 8080

    def test_address_property(self, sample_service_instance):
        """Test address property."""
        assert sample_service_instance.address == "localhost:8080"

    def test_is_healthy_property(self, sample_service_instance):
        """Test is_healthy property."""
        assert sample_service_instance.is_healthy is True

        sample_service_instance.health_status = HealthStatus.UNHEALTHY
        assert sample_service_instance.is_healthy is False

    def test_metadata(self, sample_service_instance):
        """Test service metadata."""
        assert sample_service_instance.metadata["weight"] == 1
        assert sample_service_instance.metadata["version"] == "1.0"


# =============================================================================
# Test: ServiceRegistry
# =============================================================================


class TestServiceRegistry:
    """Tests for ServiceRegistry class."""

    @pytest.mark.asyncio
    async def test_register_service(self, service_registry, sample_service_instance):
        """Test registering a service."""
        await service_registry.register(sample_service_instance)

        instances = await service_registry.get_instances("api-service", healthy_only=False)
        assert len(instances) == 1
        assert instances[0].service_id == "instance-1"

    @pytest.mark.asyncio
    async def test_register_multiple_instances(self, service_registry):
        """Test registering multiple instances."""
        for i in range(3):
            instance = ServiceInstance(
                service_id=f"instance-{i}",
                service_name="api-service",
                host="localhost",
                port=8080 + i,
                health_status=HealthStatus.HEALTHY
            )
            await service_registry.register(instance)

        instances = await service_registry.get_instances("api-service")
        assert len(instances) == 3

    @pytest.mark.asyncio
    async def test_deregister_service(self, service_registry, sample_service_instance):
        """Test deregistering a service."""
        await service_registry.register(sample_service_instance)

        result = await service_registry.deregister("api-service", "instance-1")
        assert result is True

        instances = await service_registry.get_instances("api-service", healthy_only=False)
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_deregister_nonexistent(self, service_registry):
        """Test deregistering non-existent service."""
        result = await service_registry.deregister("nonexistent", "instance-1")
        assert result is False

    @pytest.mark.asyncio
    async def test_heartbeat(self, service_registry, sample_service_instance):
        """Test heartbeat update."""
        await service_registry.register(sample_service_instance)

        old_heartbeat = sample_service_instance.last_heartbeat

        await asyncio.sleep(0.01)
        result = await service_registry.heartbeat("api-service", "instance-1")

        assert result is True
        instances = await service_registry.get_instances("api-service", healthy_only=False)
        assert instances[0].last_heartbeat > old_heartbeat

    @pytest.mark.asyncio
    async def test_heartbeat_nonexistent(self, service_registry):
        """Test heartbeat for non-existent service."""
        result = await service_registry.heartbeat("nonexistent", "instance-1")
        assert result is False

    @pytest.mark.asyncio
    async def test_update_health(self, service_registry, sample_service_instance):
        """Test health status update."""
        await service_registry.register(sample_service_instance)

        result = await service_registry.update_health(
            "api-service", "instance-1", HealthStatus.DEGRADED
        )

        assert result is True
        instances = await service_registry.get_instances("api-service", healthy_only=False)
        assert instances[0].health_status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_healthy_only_filter(self, service_registry):
        """Test healthy-only filtering."""
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

        healthy_instances = await service_registry.get_instances("api", healthy_only=True)
        all_instances = await service_registry.get_instances("api", healthy_only=False)

        assert len(healthy_instances) == 1
        assert len(all_instances) == 2

    @pytest.mark.asyncio
    async def test_stale_instance_filtering(self):
        """Test stale instance filtering based on heartbeat."""
        registry = ServiceRegistry(heartbeat_timeout=0.1)

        instance = ServiceInstance(
            service_id="stale-1",
            service_name="api",
            host="localhost",
            port=8080,
            health_status=HealthStatus.HEALTHY
        )
        await registry.register(instance)

        # Should be available immediately
        instances = await registry.get_instances("api", healthy_only=False)
        assert len(instances) == 1

        # Wait for heartbeat timeout
        await asyncio.sleep(0.15)

        # Should be filtered out as stale
        instances = await registry.get_instances("api", healthy_only=False)
        assert len(instances) == 0

    @pytest.mark.asyncio
    async def test_get_all_services(self, service_registry):
        """Test getting all services."""
        for svc in ["api", "db", "cache"]:
            instance = ServiceInstance(
                service_id=f"{svc}-1",
                service_name=svc,
                host="localhost",
                port=8080,
                health_status=HealthStatus.HEALTHY
            )
            await service_registry.register(instance)

        all_services = await service_registry.get_all_services()

        assert len(all_services) == 3
        assert "api" in all_services
        assert "db" in all_services
        assert "cache" in all_services


# =============================================================================
# Test: LoadBalancer - Round Robin
# =============================================================================


class TestLoadBalancerRoundRobin:
    """Tests for LoadBalancer with Round Robin strategy."""

    @pytest.mark.asyncio
    async def test_round_robin_distribution(self, service_registry):
        """Test round robin distributes evenly."""
        for i in range(3):
            instance = ServiceInstance(
                service_id=f"instance-{i}",
                service_name="api",
                host="localhost",
                port=8080 + i,
                health_status=HealthStatus.HEALTHY
            )
            await service_registry.register(instance)

        lb = LoadBalancer(service_registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)

        # Should cycle through instances
        selected = []
        for _ in range(6):
            instance = await lb.get_instance("api")
            selected.append(instance.service_id)

        # Should see each instance twice
        assert selected.count("instance-0") == 2
        assert selected.count("instance-1") == 2
        assert selected.count("instance-2") == 2

    @pytest.mark.asyncio
    async def test_round_robin_empty_service(self, service_registry):
        """Test round robin with no instances."""
        lb = LoadBalancer(service_registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)

        instance = await lb.get_instance("nonexistent")
        assert instance is None


# =============================================================================
# Test: LoadBalancer - Random
# =============================================================================


class TestLoadBalancerRandom:
    """Tests for LoadBalancer with Random strategy."""

    @pytest.mark.asyncio
    async def test_random_selection(self, service_registry):
        """Test random selection."""
        for i in range(3):
            instance = ServiceInstance(
                service_id=f"instance-{i}",
                service_name="api",
                host="localhost",
                port=8080 + i,
                health_status=HealthStatus.HEALTHY
            )
            await service_registry.register(instance)

        lb = LoadBalancer(service_registry, strategy=LoadBalanceStrategy.RANDOM)

        # Should return a valid instance
        instance = await lb.get_instance("api")
        assert instance is not None
        assert instance.service_name == "api"


# =============================================================================
# Test: LoadBalancer - Least Connections
# =============================================================================


class TestLoadBalancerLeastConnections:
    """Tests for LoadBalancer with Least Connections strategy."""

    @pytest.mark.asyncio
    async def test_least_connections(self, service_registry):
        """Test least connections selection."""
        for i in range(3):
            instance = ServiceInstance(
                service_id=f"instance-{i}",
                service_name="api",
                host="localhost",
                port=8080 + i,
                health_status=HealthStatus.HEALTHY
            )
            await service_registry.register(instance)

        lb = LoadBalancer(service_registry, strategy=LoadBalanceStrategy.LEAST_CONNECTIONS)

        # Simulate connections on instance-0 and instance-1
        await lb.acquire("instance-0")
        await lb.acquire("instance-0")
        await lb.acquire("instance-1")

        # Should select instance-2 (0 connections)
        instance = await lb.get_instance("api")
        assert instance.service_id == "instance-2"

    @pytest.mark.asyncio
    async def test_acquire_release(self, service_registry, load_balancer):
        """Test connection acquire and release."""
        instance = ServiceInstance(
            service_id="instance-1",
            service_name="api",
            host="localhost",
            port=8080,
            health_status=HealthStatus.HEALTHY
        )
        await service_registry.register(instance)

        lb = LoadBalancer(service_registry, strategy=LoadBalanceStrategy.LEAST_CONNECTIONS)

        await lb.acquire("instance-1")
        assert lb._connections.get("instance-1") == 1

        await lb.release("instance-1")
        assert lb._connections.get("instance-1") == 0

        # Release below zero should stay at 0
        await lb.release("instance-1")
        assert lb._connections.get("instance-1") == 0


# =============================================================================
# Test: LoadBalancer - Weighted
# =============================================================================


class TestLoadBalancerWeighted:
    """Tests for LoadBalancer with Weighted strategy."""

    @pytest.mark.asyncio
    async def test_weighted_selection(self, service_registry):
        """Test weighted selection respects weights."""
        # Create instances with different weights
        heavy = ServiceInstance(
            service_id="heavy",
            service_name="api",
            host="localhost",
            port=8080,
            health_status=HealthStatus.HEALTHY,
            metadata={"weight": 10}
        )
        light = ServiceInstance(
            service_id="light",
            service_name="api",
            host="localhost",
            port=8081,
            health_status=HealthStatus.HEALTHY,
            metadata={"weight": 1}
        )

        await service_registry.register(heavy)
        await service_registry.register(light)

        lb = LoadBalancer(service_registry, strategy=LoadBalanceStrategy.WEIGHTED)

        # Sample many times
        selections = {"heavy": 0, "light": 0}
        for _ in range(100):
            instance = await lb.get_instance("api")
            selections[instance.service_id] += 1

        # Heavy should be selected more often
        assert selections["heavy"] > selections["light"]


# =============================================================================
# Property-Based Tests: Load Balancing Fairness
# =============================================================================


class TestPropertyLoadBalancingFairness:
    """Property-based tests for load balancing fairness."""

    @given(
        num_instances=st.integers(min_value=2, max_value=5),
        num_requests=st.integers(min_value=10, max_value=50)
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_property_round_robin_fairness(self, num_instances, num_requests):
        """Property: Round robin should distribute requests evenly."""
        registry = ServiceRegistry(heartbeat_timeout=300.0)

        for i in range(num_instances):
            instance = ServiceInstance(
                service_id=f"instance-{i}",
                service_name="api",
                host="localhost",
                port=8080 + i,
                health_status=HealthStatus.HEALTHY
            )
            await registry.register(instance)

        lb = LoadBalancer(registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)

        counts = {}
        for _ in range(num_requests):
            instance = await lb.get_instance("api")
            counts[instance.service_id] = counts.get(instance.service_id, 0) + 1

        # Each instance should get approximately equal requests
        expected = num_requests // num_instances
        for count in counts.values():
            assert abs(count - expected) <= 1  # Allow off by 1

    @given(
        num_instances=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_property_least_conn_selects_minimum(self, num_instances):
        """Property: Least connections should always select instance with fewest connections."""
        registry = ServiceRegistry(heartbeat_timeout=300.0)

        for i in range(num_instances):
            instance = ServiceInstance(
                service_id=f"instance-{i}",
                service_name="api",
                host="localhost",
                port=8080 + i,
                health_status=HealthStatus.HEALTHY
            )
            await registry.register(instance)

        lb = LoadBalancer(registry, strategy=LoadBalanceStrategy.LEAST_CONNECTIONS)

        # Assign different connection counts
        connection_counts = {}
        for i in range(num_instances):
            conn_count = random.randint(0, 10)
            connection_counts[f"instance-{i}"] = conn_count
            for _ in range(conn_count):
                await lb.acquire(f"instance-{i}")

        # Get instance
        selected = await lb.get_instance("api")

        # Should be one of the instances with minimum connections
        min_conn = min(connection_counts.values())
        min_instances = [k for k, v in connection_counts.items() if v == min_conn]
        assert selected.service_id in min_instances

    @given(
        weights=st.lists(st.integers(min_value=1, max_value=10), min_size=2, max_size=5)
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_property_weighted_respects_ratios(self, weights):
        """Property: Weighted selection should approximately respect weight ratios."""
        registry = ServiceRegistry(heartbeat_timeout=300.0)

        for i, weight in enumerate(weights):
            instance = ServiceInstance(
                service_id=f"instance-{i}",
                service_name="api",
                host="localhost",
                port=8080 + i,
                health_status=HealthStatus.HEALTHY,
                metadata={"weight": weight}
            )
            await registry.register(instance)

        lb = LoadBalancer(registry, strategy=LoadBalanceStrategy.WEIGHTED)

        # Sample many times
        counts = {f"instance-{i}": 0 for i in range(len(weights))}
        total_samples = 1000

        for _ in range(total_samples):
            instance = await lb.get_instance("api")
            counts[instance.service_id] += 1

        # Check that higher weights get more selections
        total_weight = sum(weights)
        for i, weight in enumerate(weights):
            expected_ratio = weight / total_weight
            actual_ratio = counts[f"instance-{i}"] / total_samples
            # Allow 20% tolerance due to randomness
            assert abs(actual_ratio - expected_ratio) < 0.2


# =============================================================================
# Integration Tests
# =============================================================================


class TestLoadBalancingIntegration:
    """Integration tests for load balancing system."""

    @pytest.mark.asyncio
    async def test_full_service_lifecycle(self):
        """Test complete service lifecycle."""
        registry = ServiceRegistry(heartbeat_timeout=300.0)
        checker = HealthChecker()

        # Register services
        for i in range(3):
            instance = ServiceInstance(
                service_id=f"api-{i}",
                service_name="api",
                host="localhost",
                port=8080 + i,
                health_status=HealthStatus.HEALTHY
            )
            await registry.register(instance)

        # Create load balancer
        lb = LoadBalancer(registry, strategy=LoadBalanceStrategy.ROUND_ROBIN)

        # Simulate requests
        for _ in range(9):
            instance = await lb.get_instance("api")
            assert instance is not None

        # Mark one unhealthy
        await registry.update_health("api", "api-1", HealthStatus.UNHEALTHY)

        # Should only get healthy instances
        for _ in range(10):
            instance = await lb.get_instance("api")
            assert instance.service_id != "api-1"

        # Deregister a service
        await registry.deregister("api", "api-0")

        # Should still work with remaining instances
        instance = await lb.get_instance("api")
        assert instance.service_id == "api-2"

    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Test health check integration with registry."""
        registry = ServiceRegistry(heartbeat_timeout=300.0)
        checker = HealthChecker()

        # Register a service
        instance = ServiceInstance(
            service_id="api-1",
            service_name="api",
            host="localhost",
            port=8080,
            health_status=HealthStatus.HEALTHY
        )
        await registry.register(instance)

        # Register health check that uses registry
        async def api_health():
            instances = await registry.get_instances("api", healthy_only=False)
            if not instances:
                return ComponentHealth(
                    name="api",
                    status=HealthStatus.UNHEALTHY,
                    message="No instances"
                )
            healthy = sum(1 for i in instances if i.is_healthy)
            total = len(instances)
            if healthy == total:
                status = HealthStatus.HEALTHY
            elif healthy > 0:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            return ComponentHealth(
                name="api",
                status=status,
                message=f"{healthy}/{total} healthy"
            )

        checker.register_check("api", api_health)

        # Check health
        system = await checker.check_all()
        assert system.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_concurrent_registration(self):
        """Test concurrent service registration."""
        registry = ServiceRegistry(heartbeat_timeout=300.0)

        async def register_batch(start):
            for i in range(10):
                instance = ServiceInstance(
                    service_id=f"instance-{start}-{i}",
                    service_name="api",
                    host="localhost",
                    port=8080 + start * 10 + i,
                    health_status=HealthStatus.HEALTHY
                )
                await registry.register(instance)

        # Register concurrently
        await asyncio.gather(
            register_batch(0),
            register_batch(1),
            register_batch(2)
        )

        instances = await registry.get_instances("api", healthy_only=False)
        assert len(instances) == 30

    @pytest.mark.asyncio
    async def test_default_health_checks(self):
        """Test default health checks setup."""
        checker = HealthChecker()
        await create_default_health_checks(checker)

        # Check all default checks
        system = await checker.check_all()

        # Should have checks for cache, executor, monitor
        component_names = [c.name for c in system.components]
        assert "response_cache" in component_names
        assert "concurrent_executor" in component_names
        assert "performance_monitor" in component_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
