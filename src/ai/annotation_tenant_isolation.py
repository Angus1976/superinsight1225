"""Annotation Multi-Tenant Isolation Service.

This module provides comprehensive multi-tenant isolation for AI annotations:
- Automatic tenant_id filtering on all queries
- Cross-tenant access prevention
- Tenant validation and enforcement
- Integration with RBAC and audit services

Requirements:
- 7.6: Multi-tenant data isolation
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum


class TenantIsolationViolationType(str, Enum):
    """Type of tenant isolation violation."""
    MISSING_TENANT_ID = "missing_tenant_id"
    CROSS_TENANT_ACCESS = "cross_tenant_access"
    INVALID_TENANT_ID = "invalid_tenant_id"
    TENANT_MISMATCH = "tenant_mismatch"


@dataclass
class TenantContext:
    """Context for tenant operations."""
    tenant_id: UUID
    user_id: UUID
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TenantIsolationViolation:
    """Record of a tenant isolation violation."""
    violation_id: UUID = field(default_factory=uuid4)
    violation_type: TenantIsolationViolationType = TenantIsolationViolationType.CROSS_TENANT_ACCESS
    tenant_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    attempted_tenant_id: Optional[UUID] = None
    resource_type: str = ""
    resource_id: Optional[UUID] = None
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    blocked: bool = True


@dataclass
class QueryFilter:
    """Filter for database queries with tenant isolation."""
    tenant_id: UUID
    additional_filters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for query."""
        return {
            "tenant_id": self.tenant_id,
            **self.additional_filters
        }


class AnnotationTenantIsolationService:
    """Service for enforcing multi-tenant isolation in annotations."""

    def __init__(self):
        """Initialize tenant isolation service."""
        self._lock = asyncio.Lock()

        # Active tenant contexts
        self._contexts: Dict[str, TenantContext] = {}  # session_id -> context

        # Violation tracking
        self._violations: List[TenantIsolationViolation] = []

        # Tenant registry (in production, this would be in database)
        self._active_tenants: Dict[UUID, Dict[str, Any]] = {}

        # Statistics
        self._stats = {
            "total_checks": 0,
            "violations_detected": 0,
            "violations_blocked": 0
        }

    async def register_tenant(
        self,
        tenant_id: UUID,
        tenant_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Register a tenant in the system.

        Args:
            tenant_id: Tenant ID
            tenant_name: Tenant name
            metadata: Optional tenant metadata

        Returns:
            Tenant information
        """
        async with self._lock:
            tenant_info = {
                "tenant_id": tenant_id,
                "tenant_name": tenant_name,
                "registered_at": datetime.utcnow(),
                "is_active": True,
                "metadata": metadata or {}
            }
            self._active_tenants[tenant_id] = tenant_info
            return tenant_info

    async def create_context(
        self,
        tenant_id: UUID,
        user_id: UUID,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> TenantContext:
        """Create a tenant context for a session.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            session_id: Session identifier
            ip_address: User's IP address

        Returns:
            Created tenant context
        """
        # Validate tenant exists
        await self._validate_tenant(tenant_id)

        async with self._lock:
            context = TenantContext(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address
            )

            if session_id:
                self._contexts[session_id] = context

            return context

    async def get_context(
        self,
        session_id: str
    ) -> Optional[TenantContext]:
        """Get tenant context for a session.

        Args:
            session_id: Session identifier

        Returns:
            Tenant context or None
        """
        async with self._lock:
            return self._contexts.get(session_id)

    async def validate_tenant_access(
        self,
        context: TenantContext,
        resource_tenant_id: UUID,
        resource_type: str,
        resource_id: Optional[UUID] = None
    ) -> bool:
        """Validate that a user can access a resource in a tenant.

        Args:
            context: User's tenant context
            resource_tenant_id: Tenant ID of the resource
            resource_type: Type of resource
            resource_id: Resource ID

        Returns:
            True if access is allowed

        Raises:
            PermissionError: If access is denied
        """
        async with self._lock:
            self._stats["total_checks"] += 1

            # Check if tenant IDs match
            if context.tenant_id != resource_tenant_id:
                # Cross-tenant access attempt
                violation = TenantIsolationViolation(
                    violation_type=TenantIsolationViolationType.CROSS_TENANT_ACCESS,
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    attempted_tenant_id=resource_tenant_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    description=f"User from tenant {context.tenant_id} attempted to access resource in tenant {resource_tenant_id}",
                    ip_address=context.ip_address,
                    blocked=True
                )
                self._violations.append(violation)
                self._stats["violations_detected"] += 1
                self._stats["violations_blocked"] += 1

                raise PermissionError(
                    f"Cross-tenant access denied: Cannot access resource in tenant {resource_tenant_id} from tenant {context.tenant_id}"
                )

            return True

    async def enforce_tenant_filter(
        self,
        tenant_id: UUID,
        filters: Optional[Dict[str, Any]] = None
    ) -> QueryFilter:
        """Enforce tenant filtering on database queries.

        Args:
            tenant_id: Tenant ID to filter by
            filters: Additional filters

        Returns:
            Query filter with tenant_id enforced
        """
        # Validate tenant
        await self._validate_tenant(tenant_id)

        return QueryFilter(
            tenant_id=tenant_id,
            additional_filters=filters or {}
        )

    async def _validate_tenant(
        self,
        tenant_id: UUID
    ) -> None:
        """Validate that a tenant exists and is active.

        Args:
            tenant_id: Tenant ID

        Raises:
            ValueError: If tenant is invalid or inactive
        """
        if tenant_id not in self._active_tenants:
            violation = TenantIsolationViolation(
                violation_type=TenantIsolationViolationType.INVALID_TENANT_ID,
                tenant_id=tenant_id,
                description=f"Invalid tenant ID: {tenant_id}",
                blocked=True
            )
            self._violations.append(violation)
            self._stats["violations_detected"] += 1
            self._stats["violations_blocked"] += 1

            raise ValueError(f"Invalid tenant ID: {tenant_id}")

        tenant = self._active_tenants[tenant_id]
        if not tenant.get("is_active", False):
            raise ValueError(f"Tenant {tenant_id} is not active")

    async def validate_query_has_tenant_filter(
        self,
        query_filters: Dict[str, Any],
        expected_tenant_id: UUID
    ) -> bool:
        """Validate that a query includes proper tenant filtering.

        Args:
            query_filters: Query filters to validate
            expected_tenant_id: Expected tenant ID

        Returns:
            True if valid

        Raises:
            ValueError: If tenant filter is missing or incorrect
        """
        async with self._lock:
            self._stats["total_checks"] += 1

            # Check if tenant_id is in filters
            if "tenant_id" not in query_filters:
                violation = TenantIsolationViolation(
                    violation_type=TenantIsolationViolationType.MISSING_TENANT_ID,
                    tenant_id=expected_tenant_id,
                    description="Query missing tenant_id filter",
                    blocked=True
                )
                self._violations.append(violation)
                self._stats["violations_detected"] += 1
                self._stats["violations_blocked"] += 1

                raise ValueError("Query must include tenant_id filter")

            # Check if tenant_id matches expected
            if query_filters["tenant_id"] != expected_tenant_id:
                violation = TenantIsolationViolation(
                    violation_type=TenantIsolationViolationType.TENANT_MISMATCH,
                    tenant_id=expected_tenant_id,
                    attempted_tenant_id=query_filters["tenant_id"],
                    description=f"Query tenant_id {query_filters['tenant_id']} does not match context tenant_id {expected_tenant_id}",
                    blocked=True
                )
                self._violations.append(violation)
                self._stats["violations_detected"] += 1
                self._stats["violations_blocked"] += 1

                raise ValueError(
                    f"Query tenant_id mismatch: expected {expected_tenant_id}, got {query_filters['tenant_id']}"
                )

            return True

    async def wrap_query_with_tenant_filter(
        self,
        tenant_id: UUID,
        query_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Wrap a database query function with automatic tenant filtering.

        Args:
            tenant_id: Tenant ID
            query_func: Query function to wrap
            *args: Query function arguments
            **kwargs: Query function keyword arguments

        Returns:
            Query result
        """
        # Ensure tenant_id is in kwargs
        if "tenant_id" not in kwargs:
            kwargs["tenant_id"] = tenant_id

        # Validate tenant_id matches
        if kwargs["tenant_id"] != tenant_id:
            raise ValueError("Cannot override tenant_id in wrapped query")

        # Execute query
        return await query_func(*args, **kwargs)

    async def get_violations(
        self,
        tenant_id: Optional[UUID] = None,
        violation_type: Optional[TenantIsolationViolationType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[TenantIsolationViolation]:
        """Get tenant isolation violations.

        Args:
            tenant_id: Filter by tenant ID
            violation_type: Filter by violation type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum violations to return

        Returns:
            List of violations
        """
        async with self._lock:
            violations = self._violations

            # Apply filters
            if tenant_id:
                violations = [
                    v for v in violations
                    if v.tenant_id == tenant_id or v.attempted_tenant_id == tenant_id
                ]

            if violation_type:
                violations = [v for v in violations if v.violation_type == violation_type]

            if start_date:
                violations = [v for v in violations if v.timestamp >= start_date]

            if end_date:
                violations = [v for v in violations if v.timestamp <= end_date]

            # Sort by timestamp (newest first)
            violations.sort(key=lambda v: v.timestamp, reverse=True)

            return violations[:limit]

    async def get_statistics(
        self,
        tenant_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get tenant isolation statistics.

        Args:
            tenant_id: Optional tenant ID filter

        Returns:
            Dictionary of statistics
        """
        async with self._lock:
            if tenant_id:
                violations = [
                    v for v in self._violations
                    if v.tenant_id == tenant_id or v.attempted_tenant_id == tenant_id
                ]
            else:
                violations = self._violations

            violation_type_counts = {}
            for violation in violations:
                violation_type_counts[violation.violation_type.value] = \
                    violation_type_counts.get(violation.violation_type.value, 0) + 1

            return {
                **self._stats,
                "total_violations": len(violations),
                "violation_types": violation_type_counts,
                "active_tenants": len(self._active_tenants),
                "active_contexts": len(self._contexts)
            }

    async def clear_violations(
        self,
        tenant_id: Optional[UUID] = None,
        before_date: Optional[datetime] = None
    ) -> int:
        """Clear violation records.

        Args:
            tenant_id: Optional tenant ID filter
            before_date: Optional date filter

        Returns:
            Number of violations cleared
        """
        async with self._lock:
            if not tenant_id and not before_date:
                count = len(self._violations)
                self._violations.clear()
                return count

            filtered = []
            cleared = 0

            for violation in self._violations:
                should_clear = False

                if tenant_id and (violation.tenant_id == tenant_id or violation.attempted_tenant_id == tenant_id):
                    should_clear = True

                if before_date and violation.timestamp < before_date:
                    should_clear = True

                if should_clear:
                    cleared += 1
                else:
                    filtered.append(violation)

            self._violations = filtered
            return cleared


# Global instance
_annotation_tenant_isolation_service: Optional[AnnotationTenantIsolationService] = None
_isolation_lock = asyncio.Lock()


async def get_annotation_tenant_isolation_service() -> AnnotationTenantIsolationService:
    """Get or create the global annotation tenant isolation service.

    Returns:
        Annotation tenant isolation service instance
    """
    global _annotation_tenant_isolation_service

    async with _isolation_lock:
        if _annotation_tenant_isolation_service is None:
            _annotation_tenant_isolation_service = AnnotationTenantIsolationService()
        return _annotation_tenant_isolation_service


async def reset_annotation_tenant_isolation_service():
    """Reset the global annotation tenant isolation service (for testing)."""
    global _annotation_tenant_isolation_service

    async with _isolation_lock:
        _annotation_tenant_isolation_service = None


# Decorator for automatic tenant isolation
def enforce_tenant_isolation(tenant_id_param: str = "tenant_id"):
    """Decorator to enforce tenant isolation on a function.

    Args:
        tenant_id_param: Name of the tenant_id parameter

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Get tenant_id from kwargs
            tenant_id = kwargs.get(tenant_id_param)
            if not tenant_id:
                raise ValueError(f"Missing required parameter: {tenant_id_param}")

            # Get isolation service
            isolation_service = await get_annotation_tenant_isolation_service()

            # Validate tenant
            await isolation_service._validate_tenant(tenant_id)

            # Execute function
            return await func(*args, **kwargs)

        return wrapper
    return decorator
