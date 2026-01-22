"""
LLM Integration Module for SuperInsight platform.

This module provides health monitoring, batch processing, rate limiting,
audit logging, and management for LLM providers.
"""

from .health_monitor import HealthMonitor, get_health_monitor
from .batch_processor import (
    LLMBatchProcessor,
    LLMRequest,
    LLMRequestResult,
    BatchProgress,
    BatchResult,
    BatchStatus,
    get_batch_processor,
)
from .rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitExceededError,
    TokenBucket,
    get_rate_limiter,
    reset_rate_limiter,
    DEFAULT_RATE_LIMITS,
)
from .log_sanitizer import (
    LogSanitizer,
    SanitizationPattern,
    SanitizationResult,
    get_sanitizer,
    sanitize_log,
    sanitize_for_audit,
)
from .audit_service import (
    LLMAuditService,
    LLMAuditEntry,
    LLMConfigAction,
    get_llm_audit_service,
)

__all__ = [
    # Health Monitor
    "HealthMonitor",
    "get_health_monitor",
    # Batch Processor
    "LLMBatchProcessor",
    "LLMRequest",
    "LLMRequestResult",
    "BatchProgress",
    "BatchResult",
    "BatchStatus",
    "get_batch_processor",
    # Rate Limiter
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitExceededError",
    "TokenBucket",
    "get_rate_limiter",
    "reset_rate_limiter",
    "DEFAULT_RATE_LIMITS",
    # Log Sanitizer
    "LogSanitizer",
    "SanitizationPattern",
    "SanitizationResult",
    "get_sanitizer",
    "sanitize_log",
    "sanitize_for_audit",
    # Audit Service
    "LLMAuditService",
    "LLMAuditEntry",
    "LLMConfigAction",
    "get_llm_audit_service",
]
