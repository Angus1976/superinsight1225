"""
API Middleware Module.

Provides middleware components for the FastAPI application.
"""

from src.api.middleware.rate_limiter import (
    AdminRateLimitMiddleware,
    RedisRateLimiter,
    InMemoryRateLimiter,
    RateLimitResult,
    create_admin_rate_limiter
)
from src.api.middleware.permission_enforcer import (
    PermissionEnforcerMiddleware,
    PermissionCache,
    PermissionRule,
    create_permission_enforcer,
    DEFAULT_PERMISSION_RULES
)

__all__ = [
    # Rate Limiting
    "AdminRateLimitMiddleware",
    "RedisRateLimiter",
    "InMemoryRateLimiter",
    "RateLimitResult",
    "create_admin_rate_limiter",
    # Permission Enforcement
    "PermissionEnforcerMiddleware",
    "PermissionCache",
    "PermissionRule",
    "create_permission_enforcer",
    "DEFAULT_PERMISSION_RULES"
]
