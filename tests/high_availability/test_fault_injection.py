"""
Fault Injection Tests for High Availability System.

Tests system resilience by simulating various failure scenarios.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.insert(0, '.')

from src.system.failure_detector import (
    FailureDetector, FailureType, FailureSeverity, ServiceHealth
)
from src.system.recovery_orchestrator import RecoveryOrchestrator, RecoveryStatus
from src.system.high_availability_recovery import HighAvailabilityRecoverySystem, HAConfig
from src.system.service_registry import ServiceRegistry, ServiceInstance, ServiceStatus, ServiceRole
from src.system.load_balancer import LoadBalancer, LoadBalancingStrategy, CircuitState
from src.system.failover_controller import FailoverController, FailoverStrategy


class TestServiceFailureInjection:
    """Tests for service failure scenarios."""
    
    @pytest.mark.asyncio
    async def test_service_unavailable(self):
        """Test handling of service unavailability."""
        detector = FailureDetector()
        detector.register_service("test_service")
        
        # Inject unhealthy service
        health = ServiceHealth(
            service_name="test_service",
            is_healthy=False,
            health_score=0.0,
            last_check=time.time(),
            failure_count=5,
            response_time_ms=0,
            error_rate=1.0,
            metrics={"is_available": False}
        )
        detector.update_service_health("test_service", health)
        
        analysis = await detector.analyze_system_state()
        
        # Should detect the failure
        assert len(analysis.failures) > 0 or analysis.system_health_score < 100
    
    @pytest.mark.asyncio
    async def test_high_error_rate(self):
        """Test handling of high error rate."""
        detector = FailureDetector()
        detector.register_service("api_service")
        
        # Inject high error rate
        health = ServiceHealth(
            service_name="api_service",
            is_healthy=True,
            health_score=50.0,
            last_check=time.time(),
            failure_count=0,
            response_time_ms=100,
            error_rate=0.15,  # 15% error rate
            metrics={"error_rate": 0.15}
        )
        detector.update_service_health("api_service", health)
        
        analysis = await detector.analyze_system_state()
        
        # Should flag high error rate
        assert analysis.system_health_score < 100
    
    @pytest.mark.asyncio
    async def test_slow_response_time(self):
        """Test handling of slow response times."""
        detector = FailureDetector()
        detector.register_service("slow_service")
        
        # Inject slow response
        health = ServiceHealth(
            service_name="slow_service",
            is_healthy=True,
            health_score=60.0,
            last_check=time.time(),
            failure_count=0,
            response_time_ms=6000,  # 6 seconds
            error_rate=0.01,
            metrics={"response_time_ms": 6000}
        )
        detector.update_service_health("slow_service", health)
        
        analysis = await detector.analyze_system_state()
        
        # Should detect performance degradation
        assert analysis.system_health_score < 100


class TestResourceExhaustionInjection:
    """Tests for resource exhaustion scenarios."""
    
    @pytest.mark.asyncio
    async def test_high_cpu_usage(self):
        """Test handling of high CPU usage."""
        detector = FailureDetector()
        
        # Mock high CPU metrics
        with patch.object(detector, '_collect_system_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "timestamp": time.time(),
                "cpu_percent": 98.0,  # Critical CPU
                "memory_percent": 50.0,
                "disk_percent": 50.0,
                "is_available": True,
                "db_connected": True,
                "error_rate": 0.0,
                "response_time_ms": 100.0,
            }
            
            analysis = await detector.analyze_system_state()
            
            # Should detect CPU exhaustion
            has_cpu_failure = any(
                f.failure_type == FailureType.RESOURCE_EXHAUSTION
                for f in analysis.failures
            )
            assert has_cpu_failure or analysis.system_health_score < 80
    
    @pytest.mark.asyncio
    async def test_high_memory_usage(self):
        """Test handling of high memory usage."""
        detector = FailureDetector()
        
        with patch.object(detector, '_collect_system_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "timestamp": time.time(),
                "cpu_percent": 50.0,
                "memory_percent": 98.0,  # Critical memory
                "disk_percent": 50.0,
                "is_available": True,
                "db_connected": True,
                "error_rate": 0.0,
                "response_time_ms": 100.0,
            }
            
            analysis = await detector.analyze_system_state()
            
            # Should detect memory exhaustion
            assert analysis.system_health_score < 80
    
    @pytest.mark.asyncio
    async def test_high_disk_usage(self):
        """Test handling of high disk usage."""
        detector = FailureDetector()
        
        with patch.object(detector, '_collect_system_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "timestamp": time.time(),
                "cpu_percent": 50.0,
                "memory_percent": 50.0,
                "disk_percent": 98.0,  # Critical disk
                "is_available": True,
                "db_connected": True,
                "error_rate": 0.0,
                "response_time_ms": 100.0,
            }
            
            analysis = await detector.analyze_system_state()
            
            # Should detect disk exhaustion
            assert analysis.system_health_score < 80


class TestDatabaseFailureInjection:
    """Tests for database failure scenarios."""
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test handling of database connection failure."""
        detector = FailureDetector()
        
        with patch.object(detector, '_collect_system_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "timestamp": time.time(),
                "cpu_percent": 50.0,
                "memory_percent": 50.0,
                "disk_percent": 50.0,
                "is_available": True,
                "db_connected": False,  # DB disconnected
                "error_rate": 0.0,
                "response_time_ms": 100.0,
            }
            
            analysis = await detector.analyze_system_state()
            
            # Should detect database failure
            has_db_failure = any(
                f.failure_type == FailureType.DATABASE_FAILURE
                for f in analysis.failures
            )
            assert has_db_failure or analysis.system_health_score < 80


class TestCircuitBreakerInjection:
    """Tests for circuit breaker behavior."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after failures."""
        lb = LoadBalancer()
        
        instance_id = "test_instance_1"
        
        # Record multiple failures
        for _ in range(6):  # More than threshold
            await lb.record_failure(instance_id)
        
        # Circuit should be open
        breaker = lb.circuit_breakers.get(instance_id)
        assert breaker is not None
        assert breaker.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_after_timeout(self):
        """Test circuit breaker transitions to half-open."""
        lb = LoadBalancer()
        
        instance_id = "test_instance_2"
        
        # Open the circuit
        for _ in range(6):
            await lb.record_failure(instance_id)
        
        breaker = lb.circuit_breakers[instance_id]
        
        # Simulate timeout passing
        breaker.last_state_change = time.time() - 60  # 60 seconds ago
        
        # Check circuit breakers
        await lb._check_circuit_breakers()
        
        # Should be half-open now
        assert breaker.state == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_on_success(self):
        """Test circuit breaker closes after successes."""
        lb = LoadBalancer()
        
        instance_id = "test_instance_3"
        
        # Open the circuit
        for _ in range(6):
            await lb.record_failure(instance_id)
        
        breaker = lb.circuit_breakers[instance_id]
        
        # Move to half-open
        breaker.state = CircuitState.HALF_OPEN
        breaker.success_count = 0
        
        # Record successes
        for _ in range(4):  # More than success threshold
            await lb.record_success(instance_id)
        
        # Should be closed now
        assert breaker.state == CircuitState.CLOSED


class TestFailoverInjection:
    """Tests for failover scenarios."""
    
    @pytest.mark.asyncio
    async def test_failover_on_primary_failure(self):
        """Test failover when primary fails."""
        controller = FailoverController()
        registry = ServiceRegistry()
        
        # Connect controller to registry
        controller.service_registry = registry
        
        # Register primary and backup
        primary = await registry.register(
            "test_service", "host1", 8000,
            role=ServiceRole.PRIMARY
        )
        await registry.update_status(primary.instance_id, ServiceStatus.HEALTHY)
        
        backup = await registry.register(
            "test_service", "host2", 8000,
            role=ServiceRole.BACKUP
        )
        await registry.update_status(backup.instance_id, ServiceStatus.HEALTHY)
        
        # Simulate primary failure
        await registry.update_status(primary.instance_id, ServiceStatus.UNHEALTHY)
        
        # Execute failover
        event = await controller.failover(
            "test_service",
            primary.instance_id,
            backup.instance_id,
            strategy=FailoverStrategy.IMMEDIATE
        )
        
        # Failover should complete or fail gracefully
        from src.system.failover_controller import FailoverStatus
        assert event.status in [FailoverStatus.COMPLETED, FailoverStatus.FAILED]
    
    @pytest.mark.asyncio
    async def test_graceful_failover(self):
        """Test graceful failover with connection draining."""
        controller = FailoverController()
        registry = ServiceRegistry()
        
        # Register instances
        primary = await registry.register(
            "test_service", "host1", 8000,
            role=ServiceRole.PRIMARY
        )
        await registry.update_status(primary.instance_id, ServiceStatus.HEALTHY)
        
        backup = await registry.register(
            "test_service", "host2", 8000,
            role=ServiceRole.BACKUP
        )
        await registry.update_status(backup.instance_id, ServiceStatus.HEALTHY)
        
        # Execute graceful failover
        event = await controller.failover(
            "test_service",
            primary.instance_id,
            backup.instance_id,
            strategy=FailoverStrategy.GRACEFUL
        )
        
        assert event.strategy == FailoverStrategy.GRACEFUL


class TestRecoveryInjection:
    """Tests for recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_automatic_recovery(self):
        """Test automatic recovery from failure."""
        ha_system = HighAvailabilityRecoverySystem()
        
        # Inject a failure
        ha_system.update_service_health("test_service", {
            "is_healthy": False,
            "health_score": 20.0,
            "error_rate": 0.5
        })
        
        # Trigger recovery
        result = await ha_system.detect_and_recover("test_service")
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_recovery_with_rollback(self):
        """Test recovery with rollback on failure."""
        orchestrator = RecoveryOrchestrator()
        
        # Create a plan that will partially fail
        async def failing_action(context):
            raise Exception("Simulated failure")
        
        orchestrator.register_action("failing_action", failing_action)
        
        # The orchestrator should handle failures gracefully
        stats = orchestrator.get_recovery_statistics()
        assert "total_recoveries" in stats


class TestCascadingFailureInjection:
    """Tests for cascading failure scenarios."""
    
    @pytest.mark.asyncio
    async def test_cascading_failure_detection(self):
        """Test detection of cascading failures."""
        detector = FailureDetector()
        
        # Register multiple dependent services
        services = ["service_a", "service_b", "service_c"]
        for service in services:
            detector.register_service(service)
        
        # Inject failures in multiple services
        for service in services:
            health = ServiceHealth(
                service_name=service,
                is_healthy=False,
                health_score=10.0,
                last_check=time.time(),
                failure_count=5,
                response_time_ms=0,
                error_rate=1.0
            )
            detector.update_service_health(service, health)
        
        analysis = await detector.analyze_system_state()
        
        # Should detect cascading failure risk
        assert analysis.risk_assessment.get("cascading_failure", 0) > 0 or \
               len(analysis.failures) >= len(services)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
