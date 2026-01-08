"""
Service Fault Tolerance and Degradation System for SuperInsight Platform.

Provides comprehensive fault tolerance capabilities including:
- Circuit breaker patterns
- Rate limiting and throttling
- Service degradation strategies
- Retry mechanisms with exponential backoff
- Bulkhead isolation
- Timeout management
- Graceful service degradation
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import random

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class DegradationLevel(Enum):
    """Service degradation levels."""
    NONE = "none"          # Full functionality
    MINIMAL = "minimal"    # Slight reduction in features
    MODERATE = "moderate"  # Significant feature reduction
    SEVERE = "severe"      # Basic functionality only
    CRITICAL = "critical"  # Emergency mode only
    
    @property
    def severity(self) -> int:
        """Get severity level for comparison."""
        severity_map = {
            "none": 0,
            "minimal": 1,
            "moderate": 2,
            "severe": 3,
            "critical": 4
        }
        return severity_map.get(self.value, 0)


class RetryStrategy(Enum):
    """Retry strategy types."""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    JITTERED_BACKOFF = "jittered_backoff"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 60.0
    half_open_max_calls: int = 3
    failure_rate_threshold: float = 0.5  # 50%
    minimum_throughput: int = 10


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    jitter: bool = True


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    max_requests: int = 100
    time_window: float = 60.0  # seconds
    burst_allowance: int = 10


@dataclass
class DegradationConfig:
    """Service degradation configuration."""
    degradation_thresholds: Dict[DegradationLevel, float] = field(default_factory=dict)
    recovery_thresholds: Dict[DegradationLevel, float] = field(default_factory=dict)
    feature_toggles: Dict[str, DegradationLevel] = field(default_factory=dict)


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.
    
    Prevents cascading failures by monitoring service health
    and temporarily blocking requests to failing services.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.half_open_calls = 0
        
        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        self.call_history = deque(maxlen=100)
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute a function call through the circuit breaker."""
        self.total_calls += 1
        
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f"Circuit breaker {self.name} moved to HALF_OPEN")
            else:
                raise CircuitBreakerOpenException(f"Circuit breaker {self.name} is OPEN")
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.config.half_open_max_calls:
                raise CircuitBreakerOpenException(f"Circuit breaker {self.name} HALF_OPEN limit reached")
        
        # Execute the function
        start_time = time.time()
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Record success
            self._record_success()
            
            return result
            
        except Exception as e:
            # Record failure
            self._record_failure()
            raise
        finally:
            # Record call in history
            duration = time.time() - start_time
            self.call_history.append({
                "timestamp": time.time(),
                "duration": duration,
                "success": True  # Will be overridden if exception occurred
            })
    
    def _record_success(self):
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.half_open_calls += 1
            
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"Circuit breaker {self.name} moved to CLOSED")
        
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def _record_failure(self):
        """Record a failed call."""
        self.total_failures += 1
        self.last_failure_time = time.time()
        
        if self.call_history:
            self.call_history[-1]["success"] = False
        
        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            
            if self._should_open_circuit():
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name} moved to OPEN")
        
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            logger.warning(f"Circuit breaker {self.name} moved back to OPEN")
    
    def _should_open_circuit(self) -> bool:
        """Check if circuit should be opened."""
        # Check failure count threshold
        if self.failure_count >= self.config.failure_threshold:
            return True
        
        # Check failure rate threshold
        if len(self.call_history) >= self.config.minimum_throughput:
            recent_calls = list(self.call_history)[-self.config.minimum_throughput:]
            failure_rate = sum(1 for call in recent_calls if not call["success"]) / len(recent_calls)
            
            if failure_rate >= self.config.failure_rate_threshold:
                return True
        
        return False
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset."""
        return time.time() - self.last_failure_time >= self.config.timeout_seconds
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        failure_rate = self.total_failures / self.total_calls if self.total_calls > 0 else 0
        
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "failure_rate": failure_rate,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }


class RateLimiter:
    """
    Rate limiter implementation using token bucket algorithm.
    
    Controls the rate of requests to prevent system overload.
    """
    
    def __init__(self, name: str, config: RateLimitConfig):
        self.name = name
        self.config = config
        self.tokens = config.max_requests
        self.last_refill = time.time()
        self.request_history = deque(maxlen=1000)
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the rate limiter."""
        current_time = time.time()
        
        # Refill tokens
        self._refill_tokens(current_time)
        
        # Check if enough tokens available
        if self.tokens >= tokens:
            self.tokens -= tokens
            self.request_history.append({
                "timestamp": current_time,
                "tokens": tokens,
                "allowed": True
            })
            return True
        else:
            self.request_history.append({
                "timestamp": current_time,
                "tokens": tokens,
                "allowed": False
            })
            return False
    
    def _refill_tokens(self, current_time: float):
        """Refill tokens based on time elapsed."""
        time_elapsed = current_time - self.last_refill
        tokens_to_add = (time_elapsed / self.config.time_window) * self.config.max_requests
        
        self.tokens = min(self.config.max_requests + self.config.burst_allowance, 
                         self.tokens + tokens_to_add)
        self.last_refill = current_time
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        current_time = time.time()
        recent_requests = [r for r in self.request_history 
                          if current_time - r["timestamp"] <= self.config.time_window]
        
        allowed_requests = sum(1 for r in recent_requests if r["allowed"])
        rejected_requests = len(recent_requests) - allowed_requests
        
        return {
            "name": self.name,
            "current_tokens": self.tokens,
            "max_tokens": self.config.max_requests,
            "recent_requests": len(recent_requests),
            "allowed_requests": allowed_requests,
            "rejected_requests": rejected_requests,
            "rejection_rate": rejected_requests / len(recent_requests) if recent_requests else 0
        }


class RetryMechanism:
    """
    Retry mechanism with various backoff strategies.
    
    Automatically retries failed operations with configurable strategies.
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    async def execute(self, func: Callable, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.debug(f"Retry attempt {attempt + 1} failed, waiting {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retry attempts failed: {e}")
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        if self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
            
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (2 ** attempt)
            
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * (attempt + 1)
            
        elif self.config.strategy == RetryStrategy.JITTERED_BACKOFF:
            base_delay = self.config.base_delay * (2 ** attempt)
            jitter = random.uniform(0, base_delay * 0.1)  # 10% jitter
            delay = base_delay + jitter
        
        else:
            delay = self.config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Apply jitter if enabled
        if self.config.jitter and self.config.strategy != RetryStrategy.JITTERED_BACKOFF:
            jitter = random.uniform(0, delay * 0.1)
            delay += jitter
        
        return delay


class ServiceDegradationManager:
    """
    Manages service degradation based on system health.
    
    Automatically degrades service functionality to maintain
    system stability under stress.
    """
    
    def __init__(self, service_name: str, config: DegradationConfig):
        self.service_name = service_name
        self.config = config
        self.current_level = DegradationLevel.NONE
        self.feature_states: Dict[str, bool] = {}
        self.degradation_history = deque(maxlen=100)
        
        # Initialize feature states
        for feature in config.feature_toggles:
            self.feature_states[feature] = True
    
    def evaluate_degradation(self, health_metrics: Dict[str, float]):
        """Evaluate and apply service degradation based on health metrics."""
        try:
            # Calculate overall health score
            health_score = self._calculate_health_score(health_metrics)
            
            # Determine appropriate degradation level
            new_level = self._determine_degradation_level(health_score)
            
            # Apply degradation if level changed
            if new_level != self.current_level:
                self._apply_degradation(new_level)
                
                # Record degradation event
                self.degradation_history.append({
                    "timestamp": time.time(),
                    "from_level": self.current_level.value,
                    "to_level": new_level.value,
                    "health_score": health_score,
                    "metrics": health_metrics.copy()
                })
                
                self.current_level = new_level
                
                logger.info(f"Service {self.service_name} degradation level changed to {new_level.value}")
        
        except Exception as e:
            logger.error(f"Error evaluating degradation for {self.service_name}: {e}")
    
    def _calculate_health_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall health score from metrics."""
        if not metrics:
            return 1.0
        
        # Simple average for now - could be weighted
        return sum(metrics.values()) / len(metrics)
    
    def _determine_degradation_level(self, health_score: float) -> DegradationLevel:
        """Determine appropriate degradation level based on health score."""
        thresholds = self.config.degradation_thresholds
        
        if health_score <= thresholds.get(DegradationLevel.CRITICAL, 0.1):
            return DegradationLevel.CRITICAL
        elif health_score <= thresholds.get(DegradationLevel.SEVERE, 0.3):
            return DegradationLevel.SEVERE
        elif health_score <= thresholds.get(DegradationLevel.MODERATE, 0.5):
            return DegradationLevel.MODERATE
        elif health_score <= thresholds.get(DegradationLevel.MINIMAL, 0.8):
            return DegradationLevel.MINIMAL
        else:
            return DegradationLevel.NONE
    
    def _apply_degradation(self, level: DegradationLevel):
        """Apply degradation by disabling features."""
        # Reset all features to enabled
        for feature in self.feature_states:
            self.feature_states[feature] = True
        
        # Disable features based on degradation level
        for feature, required_level in self.config.feature_toggles.items():
            if level.severity >= required_level.severity:  # More severe degradation
                self.feature_states[feature] = False
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is currently enabled."""
        return self.feature_states.get(feature, True)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current degradation status."""
        return {
            "service_name": self.service_name,
            "current_level": self.current_level.value,
            "feature_states": self.feature_states.copy(),
            "degradation_events": len(self.degradation_history)
        }


class FaultToleranceSystem:
    """
    Comprehensive fault tolerance system integrating all tolerance mechanisms.
    
    Coordinates circuit breakers, rate limiters, retry mechanisms,
    and service degradation for maximum system resilience.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.retry_mechanisms: Dict[str, RetryMechanism] = {}
        self.degradation_managers: Dict[str, ServiceDegradationManager] = {}
        
        # System state
        self.system_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.total_requests = 0
        self.blocked_requests = 0
        self.failed_requests = 0
        
        # Initialize default configurations
        self._setup_default_configurations()
    
    def _setup_default_configurations(self):
        """Setup default fault tolerance configurations."""
        # Default circuit breaker for critical services
        critical_services = ["database", "authentication", "storage"]
        for service in critical_services:
            self.register_circuit_breaker(
                service,
                CircuitBreakerConfig(
                    failure_threshold=3,
                    success_threshold=2,
                    timeout_seconds=30.0
                )
            )
        
        # Default rate limiters
        api_services = ["api_gateway", "annotation_service", "export_service"]
        for service in api_services:
            self.register_rate_limiter(
                service,
                RateLimitConfig(
                    max_requests=100,
                    time_window=60.0,
                    burst_allowance=20
                )
            )
        
        # Default retry mechanisms
        external_services = ["ai_services", "label_studio", "email_service"]
        for service in external_services:
            self.register_retry_mechanism(
                service,
                RetryConfig(
                    max_attempts=3,
                    base_delay=1.0,
                    strategy=RetryStrategy.EXPONENTIAL_BACKOFF
                )
            )
        
        # Default degradation managers
        degradable_services = ["annotation_service", "quality_service", "export_service"]
        for service in degradable_services:
            self.register_degradation_manager(
                service,
                DegradationConfig(
                    degradation_thresholds={
                        DegradationLevel.MINIMAL: 0.8,
                        DegradationLevel.MODERATE: 0.6,
                        DegradationLevel.SEVERE: 0.4,
                        DegradationLevel.CRITICAL: 0.2
                    },
                    feature_toggles={
                        "ai_annotation": DegradationLevel.MINIMAL,
                        "quality_checks": DegradationLevel.MODERATE,
                        "export_features": DegradationLevel.SEVERE,
                        "advanced_analytics": DegradationLevel.CRITICAL
                    }
                )
            )
    
    async def start_system(self):
        """Start the fault tolerance system."""
        if self.system_active:
            logger.warning("Fault tolerance system is already active")
            return
        
        self.system_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Fault tolerance system started")
    
    async def stop_system(self):
        """Stop the fault tolerance system."""
        self.system_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Fault tolerance system stopped")
    
    async def _monitoring_loop(self):
        """Monitor system health and apply degradation."""
        while self.system_active:
            try:
                # Update degradation based on system health
                await self._update_service_degradation()
                
                # Log system statistics
                self._log_system_statistics()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in fault tolerance monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _update_service_degradation(self):
        """Update service degradation based on current health metrics."""
        try:
            # Get health metrics from health monitor
            from src.system.health_monitor import health_monitor
            
            health_summary = health_monitor.get_metrics_summary()
            
            for service_name, degradation_manager in self.degradation_managers.items():
                # Extract relevant metrics for this service
                service_metrics = {}
                
                for metric_name, metric_data in health_summary.get("metrics", {}).items():
                    if service_name in metric_name.lower():
                        # Convert status to numeric score
                        status = metric_data.get("status", "unknown")
                        score = {
                            "healthy": 1.0,
                            "warning": 0.7,
                            "unhealthy": 0.3,
                            "unknown": 0.5
                        }.get(status, 0.5)
                        
                        service_metrics[metric_name] = score
                
                # Apply degradation evaluation
                if service_metrics:
                    degradation_manager.evaluate_degradation(service_metrics)
        
        except Exception as e:
            logger.error(f"Error updating service degradation: {e}")
    
    def _log_system_statistics(self):
        """Log system statistics periodically."""
        try:
            stats = self.get_system_statistics()
            
            logger.info(f"Fault Tolerance Stats - "
                       f"Total Requests: {stats['total_requests']}, "
                       f"Blocked: {stats['blocked_requests']}, "
                       f"Failed: {stats['failed_requests']}, "
                       f"Success Rate: {stats['success_rate']:.2%}")
        
        except Exception as e:
            logger.error(f"Error logging system statistics: {e}")
    
    def register_circuit_breaker(self, name: str, config: CircuitBreakerConfig):
        """Register a circuit breaker for a service."""
        self.circuit_breakers[name] = CircuitBreaker(name, config)
        logger.info(f"Registered circuit breaker for {name}")
    
    def register_rate_limiter(self, name: str, config: RateLimitConfig):
        """Register a rate limiter for a service."""
        self.rate_limiters[name] = RateLimiter(name, config)
        logger.info(f"Registered rate limiter for {name}")
    
    def register_retry_mechanism(self, name: str, config: RetryConfig):
        """Register a retry mechanism for a service."""
        self.retry_mechanisms[name] = RetryMechanism(config)
        logger.info(f"Registered retry mechanism for {name}")
    
    def register_degradation_manager(self, name: str, config: DegradationConfig):
        """Register a degradation manager for a service."""
        self.degradation_managers[name] = ServiceDegradationManager(name, config)
        logger.info(f"Registered degradation manager for {name}")
    
    async def execute_with_protection(self, service_name: str, func: Callable, 
                                    *args, **kwargs):
        """Execute a function with full fault tolerance protection."""
        self.total_requests += 1
        
        try:
            # Check rate limiting
            if service_name in self.rate_limiters:
                rate_limiter = self.rate_limiters[service_name]
                if not await rate_limiter.acquire():
                    self.blocked_requests += 1
                    raise RateLimitExceededException(f"Rate limit exceeded for {service_name}")
            
            # Execute with circuit breaker protection
            if service_name in self.circuit_breakers:
                circuit_breaker = self.circuit_breakers[service_name]
                
                # Execute with retry mechanism if available
                if service_name in self.retry_mechanisms:
                    retry_mechanism = self.retry_mechanisms[service_name]
                    
                    async def protected_call():
                        return await circuit_breaker.call(func, *args, **kwargs)
                    
                    return await retry_mechanism.execute(protected_call)
                else:
                    return await circuit_breaker.call(func, *args, **kwargs)
            
            # Execute with retry only
            elif service_name in self.retry_mechanisms:
                retry_mechanism = self.retry_mechanisms[service_name]
                return await retry_mechanism.execute(func, *args, **kwargs)
            
            # Execute without protection
            else:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
        
        except Exception as e:
            self.failed_requests += 1
            logger.error(f"Protected execution failed for {service_name}: {e}")
            raise
    
    def is_feature_enabled(self, service_name: str, feature_name: str) -> bool:
        """Check if a feature is enabled for a service."""
        if service_name in self.degradation_managers:
            return self.degradation_managers[service_name].is_feature_enabled(feature_name)
        return True  # Default to enabled if no degradation manager
    
    def get_circuit_breaker_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get circuit breaker status for a service."""
        if service_name in self.circuit_breakers:
            return self.circuit_breakers[service_name].get_statistics()
        return None
    
    def get_rate_limiter_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get rate limiter status for a service."""
        if service_name in self.rate_limiters:
            return self.rate_limiters[service_name].get_statistics()
        return None
    
    def get_degradation_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get degradation status for a service."""
        if service_name in self.degradation_managers:
            return self.degradation_managers[service_name].get_status()
        return None
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        try:
            success_rate = 1.0 - (self.failed_requests / self.total_requests) if self.total_requests > 0 else 1.0
            
            # Circuit breaker statistics
            circuit_breaker_stats = {}
            for name, cb in self.circuit_breakers.items():
                circuit_breaker_stats[name] = cb.get_statistics()
            
            # Rate limiter statistics
            rate_limiter_stats = {}
            for name, rl in self.rate_limiters.items():
                rate_limiter_stats[name] = rl.get_statistics()
            
            # Degradation statistics
            degradation_stats = {}
            for name, dm in self.degradation_managers.items():
                degradation_stats[name] = dm.get_status()
            
            return {
                "system_active": self.system_active,
                "total_requests": self.total_requests,
                "blocked_requests": self.blocked_requests,
                "failed_requests": self.failed_requests,
                "success_rate": success_rate,
                "circuit_breakers": circuit_breaker_stats,
                "rate_limiters": rate_limiter_stats,
                "degradation_managers": degradation_stats,
                "registered_services": {
                    "circuit_breakers": len(self.circuit_breakers),
                    "rate_limiters": len(self.rate_limiters),
                    "retry_mechanisms": len(self.retry_mechanisms),
                    "degradation_managers": len(self.degradation_managers)
                }
            }
        
        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            return {}


# Custom exceptions
class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class RateLimitExceededException(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


# Global fault tolerance system instance
fault_tolerance_system = FaultToleranceSystem()


# Convenience functions
async def start_fault_tolerance():
    """Start the global fault tolerance system."""
    await fault_tolerance_system.start_system()


async def stop_fault_tolerance():
    """Stop the global fault tolerance system."""
    await fault_tolerance_system.stop_system()


async def execute_with_protection(service_name: str, func: Callable, *args, **kwargs):
    """Execute a function with fault tolerance protection."""
    return await fault_tolerance_system.execute_with_protection(service_name, func, *args, **kwargs)


def is_feature_enabled(service_name: str, feature_name: str) -> bool:
    """Check if a feature is enabled for a service."""
    return fault_tolerance_system.is_feature_enabled(service_name, feature_name)


def get_fault_tolerance_status() -> Dict[str, Any]:
    """Get current fault tolerance system status."""
    return {
        "system_active": fault_tolerance_system.system_active,
        "total_services": (
            len(fault_tolerance_system.circuit_breakers) +
            len(fault_tolerance_system.rate_limiters) +
            len(fault_tolerance_system.retry_mechanisms) +
            len(fault_tolerance_system.degradation_managers)
        ),
        "statistics": fault_tolerance_system.get_system_statistics()
    }


# Decorator for easy fault tolerance integration
def fault_tolerant(service_name: str):
    """Decorator to add fault tolerance to a function."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            return await execute_with_protection(service_name, func, *args, **kwargs)
        return wrapper
    return decorator


# Context manager for feature toggles
class FeatureToggle:
    """Context manager for feature toggle checks."""
    
    def __init__(self, service_name: str, feature_name: str):
        self.service_name = service_name
        self.feature_name = feature_name
        self.enabled = False
    
    def __enter__(self):
        self.enabled = is_feature_enabled(self.service_name, self.feature_name)
        return self.enabled
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# Usage example:
# with FeatureToggle("annotation_service", "ai_annotation") as enabled:
#     if enabled:
#         # Execute AI annotation
#         pass
#     else:
#         # Use fallback manual annotation
#         pass