"""
LLM Application Binding System - Metrics Module

Provides Prometheus metrics for monitoring LLM request performance,
cache efficiency, and failover events.

**Feature**: llm-application-binding
**Validates**: Requirements 13.1, 13.2, 13.3, 13.5, 15.1, 15.2
"""

import logging
from typing import Optional
from src.monitoring.prometheus_metrics import (
    metrics_registry,
    Counter,
    Histogram,
    Gauge,
)

logger = logging.getLogger(__name__)

# ============================================================================
# LLM Request Metrics
# ============================================================================

llm_requests_total = metrics_registry.register(
    Counter(
        name="llm_requests_total",
        description="Total number of LLM requests",
        labels=["application", "llm_config", "provider", "status"]
    )
)

llm_request_duration_seconds = metrics_registry.register(
    Histogram(
        name="llm_request_duration_seconds",
        description="LLM request duration in seconds",
        labels=["application", "llm_config", "provider"],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float('inf'))
    )
)

llm_token_usage_total = metrics_registry.register(
    Counter(
        name="llm_token_usage_total",
        description="Total number of tokens used",
        labels=["application", "llm_config", "provider", "token_type"]
    )
)

# ============================================================================
# LLM Failover Metrics
# ============================================================================

llm_failover_events_total = metrics_registry.register(
    Counter(
        name="llm_failover_events_total",
        description="Total number of LLM failover events",
        labels=["application", "from_llm", "to_llm", "reason"]
    )
)

llm_retry_attempts_total = metrics_registry.register(
    Counter(
        name="llm_retry_attempts_total",
        description="Total number of LLM retry attempts",
        labels=["application", "llm_config", "attempt"]
    )
)

# ============================================================================
# LLM Configuration Cache Metrics
# ============================================================================

llm_config_cache_hits_total = metrics_registry.register(
    Counter(
        name="llm_config_cache_hits_total",
        description="Total number of LLM configuration cache hits",
        labels=["application", "cache_tier"]
    )
)

llm_config_cache_misses_total = metrics_registry.register(
    Counter(
        name="llm_config_cache_misses_total",
        description="Total number of LLM configuration cache misses",
        labels=["application", "cache_tier"]
    )
)

llm_config_cache_hit_rate = metrics_registry.register(
    Gauge(
        name="llm_config_cache_hit_rate",
        description="LLM configuration cache hit rate (0-1)",
        labels=["application", "cache_tier"]
    )
)

llm_config_cache_invalidations_total = metrics_registry.register(
    Counter(
        name="llm_config_cache_invalidations_total",
        description="Total number of cache invalidation events",
        labels=["reason"]
    )
)

llm_config_load_duration_seconds = metrics_registry.register(
    Histogram(
        name="llm_config_load_duration_seconds",
        description="LLM configuration load duration in seconds",
        labels=["application", "source"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0, float('inf'))
    )
)

# ============================================================================
# LLM Success Rate Metrics
# ============================================================================

llm_success_rate = metrics_registry.register(
    Gauge(
        name="llm_success_rate",
        description="LLM request success rate (0-1)",
        labels=["application", "llm_config", "provider"]
    )
)

llm_average_response_time = metrics_registry.register(
    Gauge(
        name="llm_average_response_time_seconds",
        description="Average LLM response time in seconds",
        labels=["application", "llm_config", "provider"]
    )
)

# ============================================================================
# Helper Functions
# ============================================================================

def record_llm_request(
    application: str,
    llm_config: str,
    provider: str,
    duration: float,
    success: bool,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None
):
    """
    Record an LLM request with all relevant metrics.
    
    Args:
        application: Application code (e.g., "structuring")
        llm_config: LLM configuration name
        provider: Provider name (e.g., "openai")
        duration: Request duration in seconds
        success: Whether the request succeeded
        prompt_tokens: Number of prompt tokens used
        completion_tokens: Number of completion tokens used
    """
    status = "success" if success else "error"
    
    # Record request count
    llm_requests_total.inc(labels={
        "application": application,
        "llm_config": llm_config,
        "provider": provider,
        "status": status
    })
    
    # Record duration (only for successful requests)
    if success:
        llm_request_duration_seconds.observe(duration, labels={
            "application": application,
            "llm_config": llm_config,
            "provider": provider
        })
    
    # Record token usage
    if prompt_tokens is not None:
        llm_token_usage_total.inc(prompt_tokens, labels={
            "application": application,
            "llm_config": llm_config,
            "provider": provider,
            "token_type": "prompt"
        })
    
    if completion_tokens is not None:
        llm_token_usage_total.inc(completion_tokens, labels={
            "application": application,
            "llm_config": llm_config,
            "provider": provider,
            "token_type": "completion"
        })
    
    # Update success rate
    _update_success_rate(application, llm_config, provider)
    
    # Update average response time
    _update_average_response_time(application, llm_config, provider)


def record_llm_failover(
    application: str,
    from_llm: str,
    to_llm: str,
    reason: str
):
    """
    Record an LLM failover event.
    
    Args:
        application: Application code
        from_llm: Failed LLM configuration name
        to_llm: Target LLM configuration name
        reason: Failover reason (e.g., "timeout", "error", "max_retries")
    """
    llm_failover_events_total.inc(labels={
        "application": application,
        "from_llm": from_llm,
        "to_llm": to_llm,
        "reason": reason
    })
    
    logger.info(
        f"LLM failover: {application} from {from_llm} to {to_llm} (reason: {reason})"
    )


def record_llm_retry(
    application: str,
    llm_config: str,
    attempt: int
):
    """
    Record an LLM retry attempt.
    
    Args:
        application: Application code
        llm_config: LLM configuration name
        attempt: Retry attempt number (1, 2, 3, ...)
    """
    llm_retry_attempts_total.inc(labels={
        "application": application,
        "llm_config": llm_config,
        "attempt": str(attempt)
    })


def record_config_cache_hit(
    application: str,
    cache_tier: str = "local"
):
    """
    Record a configuration cache hit.
    
    Args:
        application: Application code
        cache_tier: Cache tier ("local" or "redis")
    """
    llm_config_cache_hits_total.inc(labels={
        "application": application,
        "cache_tier": cache_tier
    })
    
    _update_cache_hit_rate(application, cache_tier)


def record_config_cache_miss(
    application: str,
    cache_tier: str = "local"
):
    """
    Record a configuration cache miss.
    
    Args:
        application: Application code
        cache_tier: Cache tier ("local" or "redis")
    """
    llm_config_cache_misses_total.inc(labels={
        "application": application,
        "cache_tier": cache_tier
    })
    
    _update_cache_hit_rate(application, cache_tier)


def record_config_cache_invalidation(reason: str):
    """
    Record a cache invalidation event.
    
    Args:
        reason: Invalidation reason (e.g., "config_updated", "binding_updated")
    """
    llm_config_cache_invalidations_total.inc(labels={"reason": reason})


def record_config_load_duration(
    application: str,
    source: str,
    duration: float
):
    """
    Record configuration load duration.
    
    Args:
        application: Application code
        source: Configuration source ("database", "environment", "cache")
        duration: Load duration in seconds
    """
    llm_config_load_duration_seconds.observe(duration, labels={
        "application": application,
        "source": source
    })


# ============================================================================
# Internal Helper Functions
# ============================================================================

def _update_success_rate(application: str, llm_config: str, provider: str):
    """Update the success rate gauge for an LLM configuration."""
    labels = {
        "application": application,
        "llm_config": llm_config,
        "provider": provider
    }
    
    success_count = llm_requests_total.get(labels={**labels, "status": "success"})
    error_count = llm_requests_total.get(labels={**labels, "status": "error"})
    total = success_count + error_count
    
    if total > 0:
        rate = success_count / total
        llm_success_rate.set(rate, labels=labels)


def _update_average_response_time(application: str, llm_config: str, provider: str):
    """Update the average response time gauge for an LLM configuration."""
    labels = {
        "application": application,
        "llm_config": llm_config,
        "provider": provider
    }
    
    avg_time = llm_request_duration_seconds.get_average(labels=labels)
    llm_average_response_time.set(avg_time, labels=labels)


def _update_cache_hit_rate(application: str, cache_tier: str):
    """Update the cache hit rate gauge."""
    labels = {
        "application": application,
        "cache_tier": cache_tier
    }
    
    hits = llm_config_cache_hits_total.get(labels=labels)
    misses = llm_config_cache_misses_total.get(labels=labels)
    total = hits + misses
    
    if total > 0:
        rate = hits / total
        llm_config_cache_hit_rate.set(rate, labels=labels)


# ============================================================================
# Alert Thresholds
# ============================================================================

# Cache hit rate alert threshold (90%)
CACHE_HIT_RATE_ALERT_THRESHOLD = 0.90

# Success rate alert threshold (95%)
SUCCESS_RATE_ALERT_THRESHOLD = 0.95

# Average response time alert threshold (5 seconds)
RESPONSE_TIME_ALERT_THRESHOLD = 5.0


def check_cache_hit_rate_alert(application: str, cache_tier: str = "local") -> bool:
    """
    Check if cache hit rate is below alert threshold.
    
    Returns:
        True if alert should be triggered
    """
    rate = llm_config_cache_hit_rate.get(labels={
        "application": application,
        "cache_tier": cache_tier
    })
    
    if rate < CACHE_HIT_RATE_ALERT_THRESHOLD:
        logger.warning(
            f"Cache hit rate alert: {application} ({cache_tier}) = {rate:.2%} "
            f"(threshold: {CACHE_HIT_RATE_ALERT_THRESHOLD:.2%})"
        )
        return True
    
    return False


def check_success_rate_alert(
    application: str,
    llm_config: str,
    provider: str
) -> bool:
    """
    Check if success rate is below alert threshold.
    
    Returns:
        True if alert should be triggered
    """
    rate = llm_success_rate.get(labels={
        "application": application,
        "llm_config": llm_config,
        "provider": provider
    })
    
    if rate < SUCCESS_RATE_ALERT_THRESHOLD:
        logger.warning(
            f"Success rate alert: {application}/{llm_config} = {rate:.2%} "
            f"(threshold: {SUCCESS_RATE_ALERT_THRESHOLD:.2%})"
        )
        return True
    
    return False


def check_response_time_alert(
    application: str,
    llm_config: str,
    provider: str
) -> bool:
    """
    Check if average response time exceeds alert threshold.
    
    Returns:
        True if alert should be triggered
    """
    avg_time = llm_average_response_time.get(labels={
        "application": application,
        "llm_config": llm_config,
        "provider": provider
    })
    
    if avg_time > RESPONSE_TIME_ALERT_THRESHOLD:
        logger.warning(
            f"Response time alert: {application}/{llm_config} = {avg_time:.2f}s "
            f"(threshold: {RESPONSE_TIME_ALERT_THRESHOLD:.2f}s)"
        )
        return True
    
    return False


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Metrics
    "llm_requests_total",
    "llm_request_duration_seconds",
    "llm_token_usage_total",
    "llm_failover_events_total",
    "llm_retry_attempts_total",
    "llm_config_cache_hits_total",
    "llm_config_cache_misses_total",
    "llm_config_cache_hit_rate",
    "llm_config_cache_invalidations_total",
    "llm_config_load_duration_seconds",
    "llm_success_rate",
    "llm_average_response_time",
    # Helper functions
    "record_llm_request",
    "record_llm_failover",
    "record_llm_retry",
    "record_config_cache_hit",
    "record_config_cache_miss",
    "record_config_cache_invalidation",
    "record_config_load_duration",
    # Alert functions
    "check_cache_hit_rate_alert",
    "check_success_rate_alert",
    "check_response_time_alert",
    # Alert thresholds
    "CACHE_HIT_RATE_ALERT_THRESHOLD",
    "SUCCESS_RATE_ALERT_THRESHOLD",
    "RESPONSE_TIME_ALERT_THRESHOLD",
]
