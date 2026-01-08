"""
Unit tests for Fault Tolerance System.

Tests circuit breakers, rate limiters, retry mechanisms,
and service degradation functionality.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.system.fault_tolerance_system import (
    FaultToleranceSystem,
    CircuitBreaker,
    RateLimiter,
    RetryMechanism,
    ServiceDegradationManager,
    CircuitBreakerConfig,
    RateLimitConfig,
    RetryConfig,
    DegradationConfig,
    CircuitState,
    DegradationLevel,
    RetryStrategy,
    CircuitBreakerOpenException,
    RateLimitExceededException,
    fault_tolerance_system,
    start_fault_tolerance,
    stop_fault_tolerance,
    execute_with_protection,
    is_feature_enabled,
    get_fault_tolerance_status,
    fault_tolerant,
    FeatureToggle
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=30.0
        )
        
        cb = CircuitBreaker("test_service", config)
        
        assert cb.name == "test_service"
        assert cb.config == config
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.total_calls == 0
        assert cb.total_failures == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success_call(self):
        """Test successful function call through circuit breaker."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker("test_service", config)
        
        async def success_func():
            return "success"
        
        result = await cb.call(success_func)
        
        assert result == "success"
        assert cb.total_calls == 1
        assert cb.total_failures == 0
        assert cb.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_call(self):
        """Test failed function call through circuit breaker."""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("test_service", config)
        
        async def failure_func():
            raise Exception("Test failure")
        
        # First failure
        with pytest.raises(Exception, match="Test failure"):
            await cb.call(failure_func)
        
        assert cb.total_calls == 1
        assert cb.total_failures == 1
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED
        
        # Second failure - should open circuit
        with pytest.raises(Exception, match="Test failure"):
            await cb.call(failure_func)
        
        assert cb.total_calls == 2
        assert cb.total_failures == 2
        assert cb.failure_count == 2
        assert cb.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state(self):
        """Test circuit breaker in open state."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=1.0)
        cb = CircuitBreaker("test_service", config)
        
        # Force circuit to open
        cb.state = CircuitState.OPEN
        cb.last_failure_time = time.time()
        
        async def test_func():
            return "success"
        
        # Should reject calls when open
        with pytest.raises(CircuitBreakerOpenException):
            await cb.call(test_func)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery through half-open state."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0.1
        )
        cb = CircuitBreaker("test_service", config)
        
        # Force circuit to open
        cb.state = CircuitState.OPEN
        cb.last_failure_time = time.time() - 1.0  # Past timeout
        
        async def success_func():
            return "success"
        
        # First call should move to half-open
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.HALF_OPEN
        
        # Second successful call should close circuit
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_breaker_statistics(self):
        """Test circuit breaker statistics."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker("test_service", config)
        
        cb.total_calls = 10
        cb.total_failures = 3
        
        stats = cb.get_statistics()
        
        assert stats["name"] == "test_service"
        assert stats["state"] == CircuitState.CLOSED.value
        assert stats["total_calls"] == 10
        assert stats["total_failures"] == 3
        assert stats["failure_rate"] == 0.3


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        config = RateLimitConfig(
            max_requests=100,
            time_window=60.0,
            burst_allowance=10
        )
        
        rl = RateLimiter("test_service", config)
        
        assert rl.name == "test_service"
        assert rl.config == config
        assert rl.tokens == config.max_requests
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_tokens(self):
        """Test token acquisition."""
        config = RateLimitConfig(max_requests=5, time_window=60.0)
        rl = RateLimiter("test_service", config)
        
        # Should be able to acquire tokens
        assert await rl.acquire(1) == True
        assert abs(rl.tokens - 4) < 0.1  # Allow for floating point precision
        
        assert await rl.acquire(2) == True
        assert abs(rl.tokens - 2) < 0.1
        
        assert await rl.acquire(2) == True
        assert abs(rl.tokens - 0) < 0.1
        
        # Should fail when no tokens left
        assert await rl.acquire(1) == False
    
    @pytest.mark.asyncio
    async def test_rate_limiter_token_refill(self):
        """Test token refill over time."""
        config = RateLimitConfig(max_requests=10, time_window=1.0)  # 1 second window
        rl = RateLimiter("test_service", config)
        
        # Consume all tokens
        await rl.acquire(10)
        assert abs(rl.tokens - 0) < 0.1  # Allow for floating point precision
        
        # Simulate time passage
        rl.last_refill = time.time() - 0.5  # Half second ago
        
        # Should refill some tokens
        await rl.acquire(0)  # Trigger refill
        assert rl.tokens > 0
    
    def test_rate_limiter_statistics(self):
        """Test rate limiter statistics."""
        config = RateLimitConfig(max_requests=100)
        rl = RateLimiter("test_service", config)
        
        stats = rl.get_statistics()
        
        assert stats["name"] == "test_service"
        assert stats["current_tokens"] == 100
        assert stats["max_tokens"] == 100
        assert stats["recent_requests"] == 0
        assert stats["rejection_rate"] == 0


class TestRetryMechanism:
    """Test retry mechanism functionality."""
    
    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test successful execution on first attempt."""
        config = RetryConfig(max_attempts=3)
        retry = RetryMechanism(config)
        
        async def success_func():
            return "success"
        
        result = await retry.execute(success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test successful execution after initial failures."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        retry = RetryMechanism(config)
        
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await retry.execute(flaky_func)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_all_attempts_fail(self):
        """Test when all retry attempts fail."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        retry = RetryMechanism(config)
        
        async def failure_func():
            raise Exception("Persistent failure")
        
        with pytest.raises(Exception, match="Persistent failure"):
            await retry.execute(failure_func)
    
    def test_retry_delay_calculation(self):
        """Test retry delay calculation strategies."""
        # Fixed delay (disable jitter for testing)
        config = RetryConfig(strategy=RetryStrategy.FIXED_DELAY, base_delay=1.0, jitter=False)
        retry = RetryMechanism(config)
        
        assert retry._calculate_delay(0) == 1.0
        assert retry._calculate_delay(1) == 1.0
        assert retry._calculate_delay(2) == 1.0
        
        # Exponential backoff (disable jitter for testing)
        config = RetryConfig(strategy=RetryStrategy.EXPONENTIAL_BACKOFF, base_delay=1.0, jitter=False)
        retry = RetryMechanism(config)
        
        assert retry._calculate_delay(0) == 1.0
        assert retry._calculate_delay(1) == 2.0
        assert retry._calculate_delay(2) == 4.0
        
        # Linear backoff (disable jitter for testing)
        config = RetryConfig(strategy=RetryStrategy.LINEAR_BACKOFF, base_delay=1.0, jitter=False)
        retry = RetryMechanism(config)
        
        assert retry._calculate_delay(0) == 1.0
        assert retry._calculate_delay(1) == 2.0
        assert retry._calculate_delay(2) == 3.0


class TestServiceDegradationManager:
    """Test service degradation manager functionality."""
    
    def test_degradation_manager_initialization(self):
        """Test degradation manager initialization."""
        config = DegradationConfig(
            degradation_thresholds={
                DegradationLevel.MINIMAL: 0.8,
                DegradationLevel.MODERATE: 0.6
            },
            feature_toggles={
                "feature1": DegradationLevel.MINIMAL,
                "feature2": DegradationLevel.MODERATE
            }
        )
        
        dm = ServiceDegradationManager("test_service", config)
        
        assert dm.service_name == "test_service"
        assert dm.current_level == DegradationLevel.NONE
        assert dm.feature_states["feature1"] == True
        assert dm.feature_states["feature2"] == True
    
    def test_degradation_level_determination(self):
        """Test degradation level determination."""
        config = DegradationConfig(
            degradation_thresholds={
                DegradationLevel.MINIMAL: 0.8,
                DegradationLevel.MODERATE: 0.6,
                DegradationLevel.SEVERE: 0.4,
                DegradationLevel.CRITICAL: 0.2
            }
        )
        
        dm = ServiceDegradationManager("test_service", config)
        
        assert dm._determine_degradation_level(1.0) == DegradationLevel.NONE
        assert dm._determine_degradation_level(0.7) == DegradationLevel.MINIMAL
        assert dm._determine_degradation_level(0.5) == DegradationLevel.MODERATE
        assert dm._determine_degradation_level(0.3) == DegradationLevel.SEVERE
        assert dm._determine_degradation_level(0.1) == DegradationLevel.CRITICAL
    
    def test_feature_degradation(self):
        """Test feature degradation based on health metrics."""
        config = DegradationConfig(
            degradation_thresholds={
                DegradationLevel.MINIMAL: 0.8,
                DegradationLevel.MODERATE: 0.6
            },
            feature_toggles={
                "feature1": DegradationLevel.MINIMAL,
                "feature2": DegradationLevel.MODERATE
            }
        )
        
        dm = ServiceDegradationManager("test_service", config)
        
        # Healthy state - all features enabled
        dm.evaluate_degradation({"metric1": 0.9, "metric2": 0.95})
        assert dm.is_feature_enabled("feature1") == True
        assert dm.is_feature_enabled("feature2") == True
        
        # Minimal degradation - feature1 disabled, feature2 still enabled
        dm.evaluate_degradation({"metric1": 0.7, "metric2": 0.75})  # Average 0.725 -> MINIMAL
        assert dm.is_feature_enabled("feature1") == False
        assert dm.is_feature_enabled("feature2") == True
        
        # Moderate degradation - both features disabled
        dm.evaluate_degradation({"metric1": 0.5, "metric2": 0.7})  # Average 0.6 -> MODERATE
        assert dm.is_feature_enabled("feature1") == False
        assert dm.is_feature_enabled("feature2") == False
    
    def test_degradation_status(self):
        """Test degradation status reporting."""
        config = DegradationConfig()
        dm = ServiceDegradationManager("test_service", config)
        
        status = dm.get_status()
        
        assert status["service_name"] == "test_service"
        assert status["current_level"] == DegradationLevel.NONE.value
        assert "feature_states" in status
        assert "degradation_events" in status


class TestFaultToleranceSystem:
    """Test fault tolerance system integration."""
    
    def test_system_initialization(self):
        """Test system initialization."""
        system = FaultToleranceSystem()
        
        assert not system.system_active
        assert len(system.circuit_breakers) > 0  # Default configurations
        assert len(system.rate_limiters) > 0
        assert len(system.retry_mechanisms) > 0
        assert len(system.degradation_managers) > 0
    
    @pytest.mark.asyncio
    async def test_system_start_stop(self):
        """Test system start and stop."""
        system = FaultToleranceSystem()
        
        await system.start_system()
        assert system.system_active == True
        assert system.monitoring_task is not None
        
        await system.stop_system()
        assert system.system_active == False
    
    def test_component_registration(self):
        """Test component registration."""
        system = FaultToleranceSystem()
        
        # Register circuit breaker
        cb_config = CircuitBreakerConfig()
        system.register_circuit_breaker("new_service", cb_config)
        assert "new_service" in system.circuit_breakers
        
        # Register rate limiter
        rl_config = RateLimitConfig()
        system.register_rate_limiter("new_service", rl_config)
        assert "new_service" in system.rate_limiters
        
        # Register retry mechanism
        retry_config = RetryConfig()
        system.register_retry_mechanism("new_service", retry_config)
        assert "new_service" in system.retry_mechanisms
        
        # Register degradation manager
        deg_config = DegradationConfig()
        system.register_degradation_manager("new_service", deg_config)
        assert "new_service" in system.degradation_managers
    
    @pytest.mark.asyncio
    async def test_protected_execution(self):
        """Test protected function execution."""
        system = FaultToleranceSystem()
        
        # Register components for test service
        system.register_circuit_breaker("test_service", CircuitBreakerConfig())
        system.register_rate_limiter("test_service", RateLimitConfig(max_requests=10))
        
        async def test_func():
            return "protected_result"
        
        result = await system.execute_with_protection("test_service", test_func)
        assert result == "protected_result"
        assert system.total_requests == 1
    
    @pytest.mark.asyncio
    async def test_rate_limit_protection(self):
        """Test rate limit protection."""
        system = FaultToleranceSystem()
        
        # Register rate limiter with low limit
        system.register_rate_limiter("test_service", RateLimitConfig(max_requests=1))
        
        async def test_func():
            return "result"
        
        # First call should succeed
        result = await system.execute_with_protection("test_service", test_func)
        assert result == "result"
        
        # Second call should be rate limited
        with pytest.raises(RateLimitExceededException):
            await system.execute_with_protection("test_service", test_func)
    
    def test_feature_toggle_check(self):
        """Test feature toggle checking."""
        system = FaultToleranceSystem()
        
        # Register degradation manager
        config = DegradationConfig(
            feature_toggles={"test_feature": DegradationLevel.MINIMAL}
        )
        system.register_degradation_manager("test_service", config)
        
        # Feature should be enabled by default
        assert system.is_feature_enabled("test_service", "test_feature") == True
        
        # Unknown service should default to enabled
        assert system.is_feature_enabled("unknown_service", "test_feature") == True
    
    def test_system_statistics(self):
        """Test system statistics."""
        system = FaultToleranceSystem()
        
        stats = system.get_system_statistics()
        
        assert "system_active" in stats
        assert "total_requests" in stats
        assert "success_rate" in stats
        assert "circuit_breakers" in stats
        assert "rate_limiters" in stats
        assert "degradation_managers" in stats
        assert "registered_services" in stats


class TestConvenienceFunctions:
    """Test convenience functions and decorators."""
    
    @pytest.mark.asyncio
    async def test_global_functions(self):
        """Test global convenience functions."""
        # Test start/stop functions
        await start_fault_tolerance()
        assert fault_tolerance_system.system_active == True
        
        await stop_fault_tolerance()
        assert fault_tolerance_system.system_active == False
    
    @pytest.mark.asyncio
    async def test_execute_with_protection_function(self):
        """Test global execute_with_protection function."""
        async def test_func():
            return "global_result"
        
        result = await execute_with_protection("test_service", test_func)
        assert result == "global_result"
    
    def test_is_feature_enabled_function(self):
        """Test global is_feature_enabled function."""
        enabled = is_feature_enabled("test_service", "test_feature")
        assert isinstance(enabled, bool)
    
    def test_get_fault_tolerance_status_function(self):
        """Test global get_fault_tolerance_status function."""
        status = get_fault_tolerance_status()
        
        assert "system_active" in status
        assert "total_services" in status
        assert "statistics" in status
    
    @pytest.mark.asyncio
    async def test_fault_tolerant_decorator(self):
        """Test fault_tolerant decorator."""
        @fault_tolerant("test_service")
        async def decorated_func():
            return "decorated_result"
        
        result = await decorated_func()
        assert result == "decorated_result"
    
    def test_feature_toggle_context_manager(self):
        """Test FeatureToggle context manager."""
        with FeatureToggle("test_service", "test_feature") as enabled:
            assert isinstance(enabled, bool)


if __name__ == "__main__":
    pytest.main([__file__])