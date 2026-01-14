"""
Quota Manager for Multi-Tenant Workspace module.

This module provides comprehensive quota management including:
- Quota setting and retrieval
- Usage tracking
- Quota checking with warnings and blocking
- Quota inheritance
- Temporary quota increases
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.multi_tenant.workspace.models import (
    TenantQuotaModel,
    QuotaUsageModel,
    TemporaryQuotaModel,
    EntityType,
    TenantAuditLogModel,
)
from src.multi_tenant.workspace.schemas import (
    QuotaConfig,
    QuotaUsageData,
    QuotaCheckResult,
    TemporaryQuotaConfig,
    ResourceType,
)

logger = logging.getLogger(__name__)


class QuotaOperationError(Exception):
    """Exception raised for quota operation errors."""
    pass


class QuotaExceededError(QuotaOperationError):
    """Exception raised when quota is exceeded."""
    pass


class QuotaNotFoundError(QuotaOperationError):
    """Exception raised when quota is not found."""
    pass


# Warning threshold (80%)
WARNING_THRESHOLD = 0.8
# Blocking threshold (100%)
BLOCKING_THRESHOLD = 1.0


class QuotaManager:
    """
    Quota Manager for managing resource quotas and usage.
    
    Provides methods for:
    - Setting and retrieving quotas
    - Tracking resource usage
    - Checking quota limits with warnings
    - Managing temporary quota increases
    - Quota inheritance from tenant to workspace
    """
    
    def __init__(
        self,
        session: Session,
        notification_callback: Optional[Callable[[str, str, str], None]] = None
    ):
        """
        Initialize QuotaManager.
        
        Args:
            session: SQLAlchemy database session
            notification_callback: Optional callback for sending notifications
                                   (entity_id, message, severity)
        """
        self.session = session
        self.notification_callback = notification_callback
    
    def set_quota(
        self,
        entity_id: str,
        entity_type: EntityType,
        quota_config: QuotaConfig
    ) -> TenantQuotaModel:
        """
        Set quota for an entity (tenant or workspace).
        
        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            quota_config: Quota configuration
            
        Returns:
            Created or updated TenantQuotaModel
        """
        # For tenants, use TenantQuotaModel
        if entity_type == EntityType.TENANT:
            quota = self.session.query(TenantQuotaModel).filter(
                TenantQuotaModel.tenant_id == entity_id
            ).first()
            
            if quota:
                # Update existing quota
                quota.storage_bytes = quota_config.storage_bytes
                quota.project_count = quota_config.project_count
                quota.user_count = quota_config.user_count
                quota.api_call_count = quota_config.api_call_count
            else:
                # Create new quota
                quota = TenantQuotaModel(
                    id=uuid4(),
                    tenant_id=entity_id,
                    storage_bytes=quota_config.storage_bytes,
                    project_count=quota_config.project_count,
                    user_count=quota_config.user_count,
                    api_call_count=quota_config.api_call_count,
                )
                self.session.add(quota)
            
            self.session.commit()
            
            # Log audit
            self._log_audit(
                tenant_id=entity_id,
                action="quota_set",
                resource_type="quota",
                resource_id=entity_id,
                details={
                    "entity_type": entity_type.value,
                    "storage_bytes": quota_config.storage_bytes,
                    "project_count": quota_config.project_count,
                    "user_count": quota_config.user_count,
                    "api_call_count": quota_config.api_call_count,
                }
            )
            
            logger.info(f"Set quota for {entity_type.value} {entity_id}")
            return quota
        else:
            # For workspaces, we could use a separate model or store in config
            # For now, raise not implemented
            raise QuotaOperationError("Workspace-level quotas not yet implemented")
    
    def get_quota(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> QuotaConfig:
        """
        Get quota for an entity.
        
        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            
        Returns:
            QuotaConfig
            
        Raises:
            QuotaNotFoundError: If quota not found
        """
        if entity_type == EntityType.TENANT:
            quota = self.session.query(TenantQuotaModel).filter(
                TenantQuotaModel.tenant_id == entity_id
            ).first()
            
            if not quota:
                raise QuotaNotFoundError(f"Quota not found for {entity_type.value} {entity_id}")
            
            # Check for temporary quota
            temp_quota = self._get_active_temporary_quota(entity_id, entity_type)
            
            return QuotaConfig(
                storage_bytes=temp_quota.storage_bytes if temp_quota and temp_quota.storage_bytes else quota.storage_bytes,
                project_count=temp_quota.project_count if temp_quota and temp_quota.project_count else quota.project_count,
                user_count=temp_quota.user_count if temp_quota and temp_quota.user_count else quota.user_count,
                api_call_count=temp_quota.api_call_count if temp_quota and temp_quota.api_call_count else quota.api_call_count,
            )
        else:
            raise QuotaOperationError("Workspace-level quotas not yet implemented")
    
    def get_usage(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> QuotaUsageData:
        """
        Get current usage for an entity.
        
        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            
        Returns:
            QuotaUsageData
        """
        usage = self.session.query(QuotaUsageModel).filter(
            and_(
                QuotaUsageModel.entity_id == entity_id,
                QuotaUsageModel.entity_type == entity_type
            )
        ).first()
        
        if not usage:
            # Return zero usage if not found
            return QuotaUsageData(
                storage_bytes=0,
                project_count=0,
                user_count=0,
                api_call_count=0,
                last_updated=datetime.utcnow()
            )
        
        return QuotaUsageData(
            storage_bytes=usage.storage_bytes,
            project_count=usage.project_count,
            user_count=usage.user_count,
            api_call_count=usage.api_call_count,
            last_updated=usage.last_updated
        )
    
    def check_quota(
        self,
        entity_id: str,
        entity_type: EntityType,
        resource_type: ResourceType,
        amount: int = 1
    ) -> QuotaCheckResult:
        """
        Check if an operation is allowed based on quota.
        
        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            resource_type: Type of resource to check
            amount: Amount to add
            
        Returns:
            QuotaCheckResult with allowed status and percentage
        """
        try:
            quota = self.get_quota(entity_id, entity_type)
        except QuotaNotFoundError:
            # If no quota set, allow operation
            return QuotaCheckResult(allowed=True, percentage=0)
        
        usage = self.get_usage(entity_id, entity_type)
        
        # Get current and limit values
        resource_field = resource_type.value
        current = getattr(usage, resource_field, 0)
        limit = getattr(quota, resource_field, 0)
        
        if limit == 0:
            # No limit set
            return QuotaCheckResult(allowed=True, percentage=0)
        
        # Calculate percentage after operation
        new_total = current + amount
        percentage = (new_total / limit) * 100
        
        # Check if blocked (100% or more)
        if percentage >= BLOCKING_THRESHOLD * 100:
            return QuotaCheckResult(
                allowed=False,
                percentage=min(percentage, 100),
                reason=f"Quota exceeded for {resource_type.value}"
            )
        
        # Check if warning (80% or more)
        warning = None
        if percentage >= WARNING_THRESHOLD * 100:
            warning = f"{resource_type.value} usage at {percentage:.1f}%"
            # Send notification
            if self.notification_callback:
                self.notification_callback(entity_id, warning, "warning")
        
        return QuotaCheckResult(
            allowed=True,
            percentage=percentage,
            warning=warning
        )
    
    def increment_usage(
        self,
        entity_id: str,
        entity_type: EntityType,
        resource_type: ResourceType,
        amount: int = 1
    ) -> QuotaUsageData:
        """
        Increment usage for a resource.
        
        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            resource_type: Type of resource
            amount: Amount to add (can be negative for decrement)
            
        Returns:
            Updated QuotaUsageData
        """
        usage = self.session.query(QuotaUsageModel).filter(
            and_(
                QuotaUsageModel.entity_id == entity_id,
                QuotaUsageModel.entity_type == entity_type
            )
        ).first()
        
        if not usage:
            # Create usage record
            usage = QuotaUsageModel(
                id=uuid4(),
                entity_id=entity_id,
                entity_type=entity_type,
                storage_bytes=0,
                project_count=0,
                user_count=0,
                api_call_count=0,
            )
            self.session.add(usage)
        
        # Update the specific resource
        resource_field = resource_type.value
        current_value = getattr(usage, resource_field, 0)
        new_value = max(0, current_value + amount)  # Don't go below 0
        setattr(usage, resource_field, new_value)
        
        self.session.commit()
        
        logger.debug(f"Updated {resource_type.value} usage for {entity_type.value} {entity_id}: {current_value} -> {new_value}")
        
        return QuotaUsageData(
            storage_bytes=usage.storage_bytes,
            project_count=usage.project_count,
            user_count=usage.user_count,
            api_call_count=usage.api_call_count,
            last_updated=usage.last_updated
        )
    
    def decrement_usage(
        self,
        entity_id: str,
        entity_type: EntityType,
        resource_type: ResourceType,
        amount: int = 1
    ) -> QuotaUsageData:
        """
        Decrement usage for a resource.
        
        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            resource_type: Type of resource
            amount: Amount to subtract
            
        Returns:
            Updated QuotaUsageData
        """
        return self.increment_usage(entity_id, entity_type, resource_type, -amount)
    
    def set_temporary_quota(
        self,
        entity_id: str,
        entity_type: EntityType,
        config: TemporaryQuotaConfig
    ) -> TemporaryQuotaModel:
        """
        Set a temporary quota increase.
        
        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            config: Temporary quota configuration
            
        Returns:
            Created TemporaryQuotaModel
        """
        # Expire any existing temporary quotas
        self.session.query(TemporaryQuotaModel).filter(
            and_(
                TemporaryQuotaModel.entity_id == entity_id,
                TemporaryQuotaModel.entity_type == entity_type,
                TemporaryQuotaModel.expires_at > datetime.utcnow()
            )
        ).update({"expires_at": datetime.utcnow()})
        
        # Create new temporary quota
        temp_quota = TemporaryQuotaModel(
            id=uuid4(),
            entity_id=entity_id,
            entity_type=entity_type,
            storage_bytes=config.quota.storage_bytes,
            project_count=config.quota.project_count,
            user_count=config.quota.user_count,
            api_call_count=config.quota.api_call_count,
            expires_at=config.expires_at,
            reason=config.reason,
        )
        
        self.session.add(temp_quota)
        self.session.commit()
        
        # Log audit
        tenant_id = entity_id if entity_type == EntityType.TENANT else "unknown"
        self._log_audit(
            tenant_id=tenant_id,
            action="temporary_quota_set",
            resource_type="temporary_quota",
            resource_id=str(temp_quota.id),
            details={
                "entity_id": entity_id,
                "entity_type": entity_type.value,
                "expires_at": config.expires_at.isoformat(),
                "reason": config.reason,
            }
        )
        
        logger.info(f"Set temporary quota for {entity_type.value} {entity_id} until {config.expires_at}")
        return temp_quota
    
    def inherit_quota(
        self,
        workspace_id: str,
        tenant_id: str
    ) -> QuotaConfig:
        """
        Inherit quota from tenant to workspace.
        
        Args:
            workspace_id: Workspace ID
            tenant_id: Parent tenant ID
            
        Returns:
            Inherited QuotaConfig
        """
        # Get tenant quota
        tenant_quota = self.get_quota(tenant_id, EntityType.TENANT)
        
        # For now, workspaces inherit full tenant quota
        # In a real implementation, you might want to divide or limit
        return tenant_quota
    
    def get_quota_summary(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> Dict[str, Any]:
        """
        Get a summary of quota and usage.
        
        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            
        Returns:
            Dictionary with quota, usage, and percentages
        """
        try:
            quota = self.get_quota(entity_id, entity_type)
        except QuotaNotFoundError:
            return {"error": "Quota not found"}
        
        usage = self.get_usage(entity_id, entity_type)
        
        def calc_percentage(used: int, limit: int) -> float:
            if limit == 0:
                return 0
            return (used / limit) * 100
        
        return {
            "entity_id": entity_id,
            "entity_type": entity_type.value,
            "quota": quota.model_dump(),
            "usage": usage.model_dump(),
            "percentages": {
                "storage": calc_percentage(usage.storage_bytes, quota.storage_bytes),
                "projects": calc_percentage(usage.project_count, quota.project_count),
                "users": calc_percentage(usage.user_count, quota.user_count),
                "api_calls": calc_percentage(usage.api_call_count, quota.api_call_count),
            },
            "warnings": [
                resource for resource, pct in [
                    ("storage", calc_percentage(usage.storage_bytes, quota.storage_bytes)),
                    ("projects", calc_percentage(usage.project_count, quota.project_count)),
                    ("users", calc_percentage(usage.user_count, quota.user_count)),
                    ("api_calls", calc_percentage(usage.api_call_count, quota.api_call_count)),
                ] if pct >= WARNING_THRESHOLD * 100
            ]
        }
    
    def _get_active_temporary_quota(
        self,
        entity_id: str,
        entity_type: EntityType
    ) -> Optional[TemporaryQuotaModel]:
        """Get active temporary quota if exists."""
        return self.session.query(TemporaryQuotaModel).filter(
            and_(
                TemporaryQuotaModel.entity_id == entity_id,
                TemporaryQuotaModel.entity_type == entity_type,
                TemporaryQuotaModel.expires_at > datetime.utcnow()
            )
        ).first()
    
    def _log_audit(
        self,
        tenant_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> None:
        """Log an audit entry."""
        try:
            audit_log = TenantAuditLogModel(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
            )
            self.session.add(audit_log)
            self.session.flush()
        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")
