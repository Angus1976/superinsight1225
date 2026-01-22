"""
Permission Enforcement Middleware for Admin Configuration API.

Enforces permission checks for all admin configuration operations.
Returns 403 Forbidden for unauthorized access attempts.

This implementation follows async-safety rules:
- Uses asyncio.Lock() instead of threading.Lock()
- All I/O operations are async
- No blocking operations in async context
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set, Callable, Any
from uuid import UUID

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class PermissionCache:
    """
    Async-safe cache for permission decisions.

    Caches permission check results to avoid repeated database queries.
    Implements automatic cache invalidation on permission changes.
    """

    def __init__(self, ttl_seconds: int = 60, max_size: int = 10000):
        """
        Initialize permission cache.

        Args:
            ttl_seconds: Time-to-live for cache entries
            max_size: Maximum number of cache entries
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()  # Async-safe lock

    def _make_key(
        self,
        user_id: str,
        tenant_id: str,
        resource: str,
        action: str
    ) -> str:
        """Generate cache key for permission check."""
        return f"{user_id}:{tenant_id}:{resource}:{action}"

    async def get(
        self,
        user_id: str,
        tenant_id: str,
        resource: str,
        action: str
    ) -> Optional[bool]:
        """
        Get cached permission decision.

        Returns:
            True/False if cached, None if not found or expired
        """
        key = self._make_key(user_id, tenant_id, resource, action)

        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            # Check if expired
            if time.time() - entry["timestamp"] > self.ttl_seconds:
                del self._cache[key]
                return None

            return entry["allowed"]

    async def set(
        self,
        user_id: str,
        tenant_id: str,
        resource: str,
        action: str,
        allowed: bool
    ) -> None:
        """Cache a permission decision."""
        key = self._make_key(user_id, tenant_id, resource, action)

        async with self._lock:
            # Evict oldest entries if at capacity
            if len(self._cache) >= self.max_size:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k]["timestamp"]
                )
                del self._cache[oldest_key]

            self._cache[key] = {
                "allowed": allowed,
                "timestamp": time.time()
            }

    async def invalidate_user(self, user_id: str) -> int:
        """
        Invalidate all cached permissions for a user.

        Returns:
            Number of invalidated entries
        """
        async with self._lock:
            keys_to_delete = [
                k for k in self._cache.keys()
                if k.startswith(f"{user_id}:")
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    async def invalidate_tenant(self, tenant_id: str) -> int:
        """
        Invalidate all cached permissions for a tenant.

        Returns:
            Number of invalidated entries
        """
        async with self._lock:
            keys_to_delete = [
                k for k in self._cache.keys()
                if f":{tenant_id}:" in k
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    async def invalidate_all(self) -> int:
        """
        Invalidate all cached permissions.

        Returns:
            Number of invalidated entries
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count


class PermissionRule:
    """Permission rule for resource access."""

    def __init__(
        self,
        resource_pattern: str,
        required_permissions: Set[str],
        allow_readonly: bool = False
    ):
        """
        Initialize permission rule.

        Args:
            resource_pattern: URL pattern (e.g., "/api/v1/admin/config/*")
            required_permissions: Set of required permission strings
            allow_readonly: Whether to allow read-only access without full permissions
        """
        self.resource_pattern = resource_pattern
        self.required_permissions = required_permissions
        self.allow_readonly = allow_readonly

    def matches(self, path: str) -> bool:
        """Check if rule matches the given path."""
        import fnmatch
        return fnmatch.fnmatch(path, self.resource_pattern)


# Default permission rules for admin configuration
DEFAULT_PERMISSION_RULES: List[PermissionRule] = [
    # LLM Configuration
    PermissionRule(
        resource_pattern="/api/v1/admin/config/llm",
        required_permissions={"admin.config.llm.read", "admin.config.llm.write"},
        allow_readonly=True
    ),
    PermissionRule(
        resource_pattern="/api/v1/admin/config/llm/*",
        required_permissions={"admin.config.llm.read", "admin.config.llm.write"},
        allow_readonly=True
    ),

    # Database Configuration
    PermissionRule(
        resource_pattern="/api/v1/admin/config/databases",
        required_permissions={"admin.config.database.read", "admin.config.database.write"},
        allow_readonly=True
    ),
    PermissionRule(
        resource_pattern="/api/v1/admin/config/databases/*",
        required_permissions={"admin.config.database.read", "admin.config.database.write"},
        allow_readonly=True
    ),

    # Sync Strategy
    PermissionRule(
        resource_pattern="/api/v1/admin/config/sync",
        required_permissions={"admin.config.sync.read", "admin.config.sync.write"},
        allow_readonly=True
    ),
    PermissionRule(
        resource_pattern="/api/v1/admin/config/sync/*",
        required_permissions={"admin.config.sync.read", "admin.config.sync.write"},
        allow_readonly=True
    ),

    # Configuration History
    PermissionRule(
        resource_pattern="/api/v1/admin/config/history",
        required_permissions={"admin.config.history.read"},
        allow_readonly=True
    ),
    PermissionRule(
        resource_pattern="/api/v1/admin/config/history/*",
        required_permissions={"admin.config.history.read", "admin.config.history.rollback"},
        allow_readonly=True
    ),

    # SQL Builder
    PermissionRule(
        resource_pattern="/api/v1/admin/sql-builder/*",
        required_permissions={"admin.sql.read", "admin.sql.execute"},
        allow_readonly=True
    ),

    # Third-Party Tools
    PermissionRule(
        resource_pattern="/api/v1/admin/config/third-party",
        required_permissions={"admin.config.third-party.read", "admin.config.third-party.write"},
        allow_readonly=True
    ),
    PermissionRule(
        resource_pattern="/api/v1/admin/config/third-party/*",
        required_permissions={"admin.config.third-party.read", "admin.config.third-party.write"},
        allow_readonly=True
    ),

    # Dashboard
    PermissionRule(
        resource_pattern="/api/v1/admin/dashboard",
        required_permissions={"admin.dashboard.read"},
        allow_readonly=True
    ),
    PermissionRule(
        resource_pattern="/api/v1/admin/dashboard/*",
        required_permissions={"admin.dashboard.read"},
        allow_readonly=True
    ),
]


class PermissionEnforcerMiddleware(BaseHTTPMiddleware):
    """
    Permission enforcement middleware for admin configuration API.

    Checks user permissions for all configuration operations.
    Enforces read-only and query-only modes based on user permissions.
    Returns 403 Forbidden for unauthorized access attempts.

    Features:
    - Permission caching with automatic invalidation
    - Read-only mode support
    - Detailed error messages
    - Audit logging for access attempts
    """

    # HTTP methods that are considered read-only
    READONLY_METHODS = {"GET", "HEAD", "OPTIONS"}

    # HTTP methods that require write permissions
    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(
        self,
        app: ASGIApp,
        permission_checker: Optional[Callable] = None,
        rules: Optional[List[PermissionRule]] = None,
        cache_ttl: int = 60,
        exclude_paths: Optional[List[str]] = None,
        enable_audit: bool = True
    ):
        """
        Initialize permission enforcer middleware.

        Args:
            app: ASGI application
            permission_checker: Async function to check permissions
            rules: List of permission rules
            cache_ttl: Cache time-to-live in seconds
            exclude_paths: Paths to exclude from permission checks
            enable_audit: Whether to log access attempts
        """
        super().__init__(app)
        self.permission_checker = permission_checker
        self.rules = rules or DEFAULT_PERMISSION_RULES
        self.cache = PermissionCache(ttl_seconds=cache_ttl)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/api/v1/health",
            "/api/v1/system/status",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
        self.enable_audit = enable_audit

    def _get_matching_rule(self, path: str) -> Optional[PermissionRule]:
        """Find the first rule that matches the path."""
        for rule in self.rules:
            if rule.matches(path):
                return rule
        return None

    def _is_readonly_request(self, method: str) -> bool:
        """Check if request method is read-only."""
        return method.upper() in self.READONLY_METHODS

    def _get_required_permission(
        self,
        rule: PermissionRule,
        method: str
    ) -> Optional[str]:
        """
        Get the specific permission required for this request.

        Returns:
            Permission string or None if no specific permission found
        """
        is_readonly = self._is_readonly_request(method)

        # For read-only requests, look for .read permission
        if is_readonly:
            for perm in rule.required_permissions:
                if perm.endswith(".read"):
                    return perm

        # For write requests, look for .write permission
        for perm in rule.required_permissions:
            if perm.endswith(".write"):
                return perm

        # Return first permission if no specific match
        return next(iter(rule.required_permissions), None)

    async def _check_permission(
        self,
        user_id: str,
        tenant_id: str,
        resource: str,
        action: str,
        request: Request
    ) -> bool:
        """
        Check if user has required permission.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            resource: Resource being accessed
            action: Action being performed (read/write)
            request: FastAPI request object

        Returns:
            True if permitted, False otherwise
        """
        # Check cache first
        cached = await self.cache.get(user_id, tenant_id, resource, action)
        if cached is not None:
            return cached

        # Use custom permission checker if provided
        if self.permission_checker:
            try:
                allowed = await self.permission_checker(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    resource=resource,
                    action=action,
                    request=request
                )
                await self.cache.set(user_id, tenant_id, resource, action, allowed)
                return allowed
            except Exception as e:
                logger.error(f"Permission check failed: {e}")
                # Fail closed - deny access on error
                return False

        # Default: check user permissions from request state
        user_permissions = getattr(request.state, "permissions", set())

        # Check if user has the required permission
        allowed = resource in user_permissions or action in user_permissions

        await self.cache.set(user_id, tenant_id, resource, action, allowed)
        return allowed

    def _log_access_attempt(
        self,
        user_id: str,
        tenant_id: str,
        path: str,
        method: str,
        allowed: bool,
        reason: Optional[str] = None
    ) -> None:
        """Log access attempt for audit purposes."""
        if not self.enable_audit:
            return

        log_level = logging.INFO if allowed else logging.WARNING
        logger.log(
            log_level,
            f"Permission check: user={user_id} tenant={tenant_id} "
            f"path={path} method={method} allowed={allowed} reason={reason}"
        )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Apply permission enforcement to request.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint

        Returns:
            Response

        Raises:
            HTTPException: 403 if permission denied
        """
        path = str(request.url.path)
        method = request.method

        # Skip excluded paths
        for exclude in self.exclude_paths:
            if path.startswith(exclude):
                return await call_next(request)

        # Check if path matches any rule
        rule = self._get_matching_rule(path)
        if rule is None:
            # No rule matches - allow access (or deny based on config)
            return await call_next(request)

        # Get user and tenant info from request state
        user_id = getattr(request.state, "user_id", None)
        tenant_id = getattr(request.state, "tenant_id", None)

        if not user_id:
            # Try to get from headers
            user_id = request.headers.get("X-User-ID")

        if not tenant_id:
            tenant_id = request.headers.get("X-Tenant-ID")

        # If no user ID, deny access
        if not user_id:
            self._log_access_attempt(
                user_id="unknown",
                tenant_id=tenant_id or "unknown",
                path=path,
                method=method,
                allowed=False,
                reason="No user ID"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "access_denied",
                    "message": "Authentication required",
                    "code": "PERMISSION_DENIED"
                }
            )

        # Check for read-only access
        is_readonly = self._is_readonly_request(method)

        # Get required permission
        required_permission = self._get_required_permission(rule, method)
        action = "read" if is_readonly else "write"

        # Check permission
        allowed = await self._check_permission(
            user_id=str(user_id),
            tenant_id=tenant_id or "default",
            resource=required_permission or path,
            action=action,
            request=request
        )

        # Handle read-only mode
        if not allowed and is_readonly and rule.allow_readonly:
            # Check if user has at least read permission
            read_permission = next(
                (p for p in rule.required_permissions if p.endswith(".read")),
                None
            )
            if read_permission:
                allowed = await self._check_permission(
                    user_id=str(user_id),
                    tenant_id=tenant_id or "default",
                    resource=read_permission,
                    action="read",
                    request=request
                )

        self._log_access_attempt(
            user_id=str(user_id),
            tenant_id=tenant_id or "unknown",
            path=path,
            method=method,
            allowed=allowed,
            reason=f"Required: {required_permission}"
        )

        if not allowed:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "permission_denied",
                    "message": f"You do not have permission to perform this action",
                    "required_permission": required_permission,
                    "action": action,
                    "code": "PERMISSION_DENIED"
                }
            )

        return await call_next(request)

    async def invalidate_user_permissions(self, user_id: str) -> int:
        """
        Invalidate cached permissions for a user.
        Call this when user permissions change.

        Returns:
            Number of invalidated cache entries
        """
        return await self.cache.invalidate_user(user_id)

    async def invalidate_tenant_permissions(self, tenant_id: str) -> int:
        """
        Invalidate cached permissions for a tenant.
        Call this when tenant permissions change.

        Returns:
            Number of invalidated cache entries
        """
        return await self.cache.invalidate_tenant(tenant_id)

    async def invalidate_all_permissions(self) -> int:
        """
        Invalidate all cached permissions.
        Call this when permission rules change globally.

        Returns:
            Number of invalidated cache entries
        """
        return await self.cache.invalidate_all()


def create_permission_enforcer(
    permission_checker: Optional[Callable] = None,
    rules: Optional[List[PermissionRule]] = None,
    cache_ttl: int = 60,
    exclude_paths: Optional[List[str]] = None
) -> Callable:
    """
    Factory function to create permission enforcer middleware.

    Args:
        permission_checker: Custom permission checker function
        rules: Custom permission rules
        cache_ttl: Cache TTL in seconds
        exclude_paths: Paths to exclude

    Returns:
        Middleware factory function
    """
    def middleware_factory(app: ASGIApp) -> PermissionEnforcerMiddleware:
        return PermissionEnforcerMiddleware(
            app=app,
            permission_checker=permission_checker,
            rules=rules,
            cache_ttl=cache_ttl,
            exclude_paths=exclude_paths
        )

    return middleware_factory
