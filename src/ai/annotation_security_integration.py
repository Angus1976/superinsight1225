"""Annotation Security Integration Module.

This module provides unified security integration for AI annotation operations:
- Combines audit, RBAC, PII, and tenant isolation services
- Provides security middleware for API endpoints
- Offers convenience decorators for secure operations
- Ensures all annotation operations are properly secured

Requirements:
- 7.1: Audit logging
- 7.2: RBAC enforcement
- 7.3: PII desensitization
- 7.6: Multi-tenant isolation
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass, field
from functools import wraps

from .annotation_audit_service import (
    get_annotation_audit_service,
    AnnotationAuditService,
    AnnotationOperationType,
    AnnotationObjectType,
)
from .annotation_rbac_service import (
    get_annotation_rbac_service,
    AnnotationRBACService,
    AnnotationPermission,
)
from .annotation_pii_service import (
    get_annotation_pii_service,
    AnnotationPIIService,
    DesensitizationStrategy,
)
from .annotation_tenant_isolation import (
    get_annotation_tenant_isolation_service,
    AnnotationTenantIsolationService,
    TenantContext,
)


@dataclass
class SecureAnnotationContext:
    """Secure context for annotation operations."""
    tenant_id: UUID
    user_id: UUID
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Services
    audit_service: Optional[AnnotationAuditService] = None
    rbac_service: Optional[AnnotationRBACService] = None
    pii_service: Optional[AnnotationPIIService] = None
    isolation_service: Optional[AnnotationTenantIsolationService] = None


@dataclass
class SecureOperationResult:
    """Result of a secure annotation operation."""
    success: bool = False
    data: Any = None
    error: Optional[str] = None
    audit_log_id: Optional[UUID] = None
    pii_detections: int = 0
    permission_check_passed: bool = False


class AnnotationSecurityIntegration:
    """Unified security integration for annotation operations."""

    def __init__(self):
        """Initialize security integration."""
        self._audit_service: Optional[AnnotationAuditService] = None
        self._rbac_service: Optional[AnnotationRBACService] = None
        self._pii_service: Optional[AnnotationPIIService] = None
        self._isolation_service: Optional[AnnotationTenantIsolationService] = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize all security services."""
        async with self._lock:
            if not self._audit_service:
                self._audit_service = await get_annotation_audit_service()
            if not self._rbac_service:
                self._rbac_service = await get_annotation_rbac_service()
            if not self._pii_service:
                self._pii_service = await get_annotation_pii_service()
            if not self._isolation_service:
                self._isolation_service = await get_annotation_tenant_isolation_service()

    async def create_secure_context(
        self,
        tenant_id: UUID,
        user_id: UUID,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> SecureAnnotationContext:
        """Create a secure context for annotation operations.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            session_id: Session identifier
            ip_address: IP address
            user_agent: User agent string

        Returns:
            Secure annotation context
        """
        await self.initialize()

        # Create tenant isolation context
        await self._isolation_service.create_context(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address
        )

        return SecureAnnotationContext(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            audit_service=self._audit_service,
            rbac_service=self._rbac_service,
            pii_service=self._pii_service,
            isolation_service=self._isolation_service
        )

    async def execute_secure_operation(
        self,
        context: SecureAnnotationContext,
        operation_type: AnnotationOperationType,
        object_type: AnnotationObjectType,
        object_id: UUID,
        required_permission: AnnotationPermission,
        operation_func: Callable,
        operation_description: str = "",
        project_id: Optional[UUID] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state_func: Optional[Callable] = None,
        desensitize_input: bool = False,
        **operation_kwargs
    ) -> SecureOperationResult:
        """Execute an annotation operation with full security checks.

        Args:
            context: Secure annotation context
            operation_type: Type of operation
            object_type: Type of object
            object_id: Object ID
            required_permission: Required permission
            operation_func: Function to execute
            operation_description: Description
            project_id: Project ID (if applicable)
            before_state: State before operation
            after_state_func: Function to get state after operation
            desensitize_input: Whether to desensitize input text
            **operation_kwargs: Arguments for operation_func

        Returns:
            Secure operation result
        """
        result = SecureOperationResult()

        try:
            # 1. Multi-tenant isolation check
            await context.isolation_service.validate_tenant_access(
                context=TenantContext(
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    session_id=context.session_id,
                    ip_address=context.ip_address
                ),
                resource_tenant_id=context.tenant_id,
                resource_type=object_type.value,
                resource_id=object_id
            )

            # 2. RBAC permission check
            permission_check = await context.rbac_service.check_permission(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                permission=required_permission,
                scope="project" if project_id else "tenant",
                scope_id=project_id
            )

            if not permission_check.allowed:
                result.error = f"Permission denied: {permission_check.reason}"
                result.permission_check_passed = False

                # Log failed permission check
                await context.audit_service.log_operation(
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    operation_type=operation_type,
                    object_type=object_type,
                    object_id=object_id,
                    project_id=project_id,
                    operation_description=f"PERMISSION DENIED: {operation_description}",
                    ip_address=context.ip_address,
                    user_agent=context.user_agent
                )

                return result

            result.permission_check_passed = True

            # 3. PII desensitization (if requested)
            if desensitize_input and "text" in operation_kwargs:
                pii_result = await context.pii_service.desensitize_for_llm(
                    text=operation_kwargs["text"],
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    audit_service=context.audit_service
                )
                operation_kwargs["text"] = pii_result.desensitized_text
                result.pii_detections = len(pii_result.detections)

            # 4. Execute operation
            operation_result = await operation_func(**operation_kwargs)
            result.data = operation_result
            result.success = True

            # 5. Get after state
            after_state = None
            if after_state_func:
                after_state = await after_state_func(operation_result)

            # 6. Audit logging
            audit_entry = await context.audit_service.log_operation(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                operation_type=operation_type,
                object_type=object_type,
                object_id=object_id,
                project_id=project_id,
                before_state=before_state or {},
                after_state=after_state or {},
                operation_description=operation_description,
                ip_address=context.ip_address,
                user_agent=context.user_agent
            )
            result.audit_log_id = audit_entry.log_id

        except PermissionError as e:
            result.error = str(e)
            result.success = False

        except Exception as e:
            result.error = f"Operation failed: {str(e)}"
            result.success = False

            # Log error
            if context.audit_service:
                await context.audit_service.log_operation(
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    operation_type=operation_type,
                    object_type=object_type,
                    object_id=object_id,
                    project_id=project_id,
                    operation_description=f"ERROR: {operation_description}: {str(e)}",
                    ip_address=context.ip_address,
                    user_agent=context.user_agent
                )

        return result

    async def check_and_log_access(
        self,
        context: SecureAnnotationContext,
        permission: AnnotationPermission,
        resource_type: str,
        resource_id: UUID,
        project_id: Optional[UUID] = None
    ) -> bool:
        """Check permission and log access attempt.

        Args:
            context: Secure context
            permission: Required permission
            resource_type: Type of resource
            resource_id: Resource ID
            project_id: Project ID

        Returns:
            True if access allowed
        """
        # Check permission
        permission_check = await context.rbac_service.check_permission(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            permission=permission,
            scope="project" if project_id else "tenant",
            scope_id=project_id
        )

        # Log access attempt
        await context.audit_service.log_operation(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            operation_type=AnnotationOperationType.UPDATE,
            object_type=AnnotationObjectType.ANNOTATION,
            object_id=resource_id,
            project_id=project_id,
            operation_description=f"Access check: {permission.value} - {'ALLOWED' if permission_check.allowed else 'DENIED'}",
            ip_address=context.ip_address,
            user_agent=context.user_agent
        )

        return permission_check.allowed

    async def get_security_summary(
        self,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get security summary for a tenant.

        Args:
            tenant_id: Tenant ID
            start_date: Start date filter
            end_date: End date filter

        Returns:
            Security summary
        """
        await self.initialize()

        # Get audit statistics
        audit_stats = await self._audit_service.get_statistics(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )

        # Get isolation violations
        isolation_stats = await self._isolation_service.get_statistics(
            tenant_id=tenant_id
        )

        return {
            "tenant_id": str(tenant_id),
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
            "audit": audit_stats,
            "isolation": isolation_stats,
            "generated_at": datetime.utcnow().isoformat()
        }


# Global instance
_security_integration: Optional[AnnotationSecurityIntegration] = None
_integration_lock = asyncio.Lock()


async def get_security_integration() -> AnnotationSecurityIntegration:
    """Get or create the global security integration.

    Returns:
        Annotation security integration instance
    """
    global _security_integration

    async with _integration_lock:
        if _security_integration is None:
            _security_integration = AnnotationSecurityIntegration()
            await _security_integration.initialize()
        return _security_integration


async def reset_security_integration():
    """Reset the global security integration (for testing)."""
    global _security_integration

    async with _integration_lock:
        _security_integration = None


# Convenience decorator for secure annotation operations
def secure_annotation_operation(
    operation_type: AnnotationOperationType,
    object_type: AnnotationObjectType,
    required_permission: AnnotationPermission,
    desensitize_input: bool = False
):
    """Decorator for securing annotation operations.

    Args:
        operation_type: Type of operation
        object_type: Type of object
        required_permission: Required permission
        desensitize_input: Whether to desensitize input

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(
            context: SecureAnnotationContext,
            object_id: UUID,
            project_id: Optional[UUID] = None,
            **kwargs
        ) -> SecureOperationResult:
            integration = await get_security_integration()

            result = await integration.execute_secure_operation(
                context=context,
                operation_type=operation_type,
                object_type=object_type,
                object_id=object_id,
                required_permission=required_permission,
                operation_func=func,
                operation_description=f"{func.__name__}",
                project_id=project_id,
                desensitize_input=desensitize_input,
                context=context,
                object_id=object_id,
                project_id=project_id,
                **kwargs
            )

            return result

        return wrapper
    return decorator
