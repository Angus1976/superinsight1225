"""
Tenant Manager for Multi-Tenant Workspace module.

This module provides comprehensive tenant lifecycle management including:
- Tenant creation with default configuration and quotas
- Tenant updates and status management
- Tenant deletion with cascade handling
- Audit logging for all operations
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.database.multi_tenant_models import TenantModel, TenantStatus
from src.multi_tenant.workspace.models import (
    TenantQuotaModel, 
    QuotaUsageModel, 
    EntityType,
    TenantAuditLogModel,
    ExtendedTenantStatus
)
from src.multi_tenant.workspace.schemas import (
    TenantCreateConfig,
    TenantUpdateConfig,
    TenantConfig,
    TenantQuotaConfig,
)

logger = logging.getLogger(__name__)


class TenantOperationError(Exception):
    """Exception raised for tenant operation errors."""
    pass


class TenantNotFoundError(TenantOperationError):
    """Exception raised when tenant is not found."""
    pass


class TenantDisabledError(TenantOperationError):
    """Exception raised when tenant is disabled."""
    pass


class TenantAlreadyExistsError(TenantOperationError):
    """Exception raised when tenant already exists."""
    pass


class TenantManager:
    """
    Tenant Manager for managing tenant lifecycle.
    
    Provides methods for:
    - Creating tenants with default configuration and quotas
    - Updating tenant information
    - Managing tenant status (active/suspended/disabled)
    - Deleting tenants
    - Audit logging for all operations
    """
    
    def __init__(self, session: Session, audit_logger: Optional[Any] = None):
        """
        Initialize TenantManager.
        
        Args:
            session: SQLAlchemy database session
            audit_logger: Optional audit logger for recording operations
        """
        self.session = session
        self.audit_logger = audit_logger
    
    def create_tenant(self, config: TenantCreateConfig) -> TenantModel:
        """
        Create a new tenant with default configuration and quotas.
        
        Args:
            config: Tenant creation configuration
            
        Returns:
            Created TenantModel instance
            
        Raises:
            TenantAlreadyExistsError: If tenant with same name exists
        """
        # Generate unique tenant ID
        tenant_id = self._generate_tenant_id(config.name)
        
        # Check if tenant already exists
        existing = self.session.query(TenantModel).filter(
            TenantModel.id == tenant_id
        ).first()
        if existing:
            raise TenantAlreadyExistsError(f"Tenant with ID '{tenant_id}' already exists")
        
        # Get default configuration
        default_config = self._get_default_config()
        if config.config:
            # Merge with provided config
            default_config = TenantConfig(
                features={**default_config.features, **config.config.features},
                security={**default_config.security, **config.config.security},
                workspace_defaults={**default_config.workspace_defaults, **config.config.workspace_defaults},
                custom_settings={**default_config.custom_settings, **config.config.custom_settings},
            )
        
        # Get default quota
        default_quota = self._get_default_quota()
        if config.quota:
            default_quota = config.quota
        
        # Create tenant
        tenant = TenantModel(
            id=tenant_id,
            name=config.name,
            display_name=config.name,
            description=config.description,
            status=TenantStatus.ACTIVE,
            configuration=default_config.model_dump(),
            billing_email=config.admin_email,
            billing_plan=config.plan,
            max_users=default_quota.user_count,
            max_workspaces=100,  # Default workspace limit
            max_storage_gb=default_quota.storage_bytes / (1024 * 1024 * 1024),
            max_api_calls_per_hour=default_quota.api_call_count // 720,  # Convert monthly to hourly
        )
        
        self.session.add(tenant)
        self.session.flush()
        
        # Create quota record
        quota = TenantQuotaModel(
            id=uuid4(),
            tenant_id=tenant_id,
            storage_bytes=default_quota.storage_bytes,
            project_count=default_quota.project_count,
            user_count=default_quota.user_count,
            api_call_count=default_quota.api_call_count,
        )
        self.session.add(quota)
        
        # Create usage record
        usage = QuotaUsageModel(
            id=uuid4(),
            entity_id=tenant_id,
            entity_type=EntityType.TENANT,
            storage_bytes=0,
            project_count=0,
            user_count=0,
            api_call_count=0,
        )
        self.session.add(usage)
        
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=tenant_id,
            action="tenant_created",
            resource_type="tenant",
            resource_id=tenant_id,
            details={
                "name": config.name,
                "plan": config.plan,
                "admin_email": config.admin_email,
            }
        )
        
        logger.info(f"Created tenant: {tenant_id}")
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantModel]:
        """
        Get tenant by ID.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            TenantModel if found, None otherwise
        """
        return self.session.query(TenantModel).filter(
            TenantModel.id == tenant_id
        ).first()
    
    def get_tenant_or_raise(self, tenant_id: str) -> TenantModel:
        """
        Get tenant by ID or raise exception.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            TenantModel
            
        Raises:
            TenantNotFoundError: If tenant not found
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant '{tenant_id}' not found")
        return tenant
    
    def update_tenant(self, tenant_id: str, updates: TenantUpdateConfig) -> TenantModel:
        """
        Update tenant information.
        
        Args:
            tenant_id: Tenant ID to update
            updates: Update configuration
            
        Returns:
            Updated TenantModel
            
        Raises:
            TenantNotFoundError: If tenant not found
            TenantDisabledError: If tenant is disabled
        """
        tenant = self.get_tenant_or_raise(tenant_id)
        
        # Check if tenant is disabled
        if tenant.status == TenantStatus.SUSPENDED and hasattr(tenant, '_extended_status'):
            if tenant._extended_status == ExtendedTenantStatus.DISABLED:
                raise TenantDisabledError(f"Tenant '{tenant_id}' is disabled")
        
        # Apply updates
        update_details = {}
        if updates.name is not None:
            tenant.name = updates.name
            tenant.display_name = updates.name
            update_details["name"] = updates.name
        
        if updates.description is not None:
            tenant.description = updates.description
            update_details["description"] = updates.description
        
        if updates.admin_email is not None:
            tenant.billing_email = updates.admin_email
            update_details["admin_email"] = updates.admin_email
        
        if updates.plan is not None:
            tenant.billing_plan = updates.plan
            update_details["plan"] = updates.plan
        
        if updates.config is not None:
            tenant.configuration = updates.config.model_dump()
            update_details["config_updated"] = True
        
        tenant.updated_at = datetime.utcnow()
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=tenant_id,
            action="tenant_updated",
            resource_type="tenant",
            resource_id=tenant_id,
            details=update_details
        )
        
        logger.info(f"Updated tenant: {tenant_id}")
        return tenant
    
    def delete_tenant(self, tenant_id: str, hard_delete: bool = False) -> None:
        """
        Delete a tenant.
        
        Args:
            tenant_id: Tenant ID to delete
            hard_delete: If True, permanently delete; otherwise soft delete
            
        Raises:
            TenantNotFoundError: If tenant not found
        """
        tenant = self.get_tenant_or_raise(tenant_id)
        
        if hard_delete:
            # Delete quota and usage records first
            self.session.query(TenantQuotaModel).filter(
                TenantQuotaModel.tenant_id == tenant_id
            ).delete()
            self.session.query(QuotaUsageModel).filter(
                and_(
                    QuotaUsageModel.entity_id == tenant_id,
                    QuotaUsageModel.entity_type == EntityType.TENANT
                )
            ).delete()
            
            # Delete tenant
            self.session.delete(tenant)
        else:
            # Soft delete - set status to suspended
            tenant.status = TenantStatus.SUSPENDED
            tenant.updated_at = datetime.utcnow()
        
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=tenant_id,
            action="tenant_deleted" if hard_delete else "tenant_soft_deleted",
            resource_type="tenant",
            resource_id=tenant_id,
            details={"hard_delete": hard_delete}
        )
        
        logger.info(f"{'Deleted' if hard_delete else 'Soft deleted'} tenant: {tenant_id}")
    
    def set_status(self, tenant_id: str, status: TenantStatus) -> TenantModel:
        """
        Set tenant status.
        
        Args:
            tenant_id: Tenant ID
            status: New status
            
        Returns:
            Updated TenantModel
            
        Raises:
            TenantNotFoundError: If tenant not found
        """
        tenant = self.get_tenant_or_raise(tenant_id)
        
        old_status = tenant.status
        tenant.status = status
        tenant.updated_at = datetime.utcnow()
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=tenant_id,
            action="tenant_status_changed",
            resource_type="tenant",
            resource_id=tenant_id,
            details={
                "old_status": old_status.value,
                "new_status": status.value
            }
        )
        
        logger.info(f"Changed tenant {tenant_id} status from {old_status} to {status}")
        return tenant
    
    def is_operation_allowed(self, tenant_id: str) -> bool:
        """
        Check if operations are allowed for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            True if operations are allowed, False otherwise
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        # Only active tenants can perform operations
        return tenant.status == TenantStatus.ACTIVE
    
    def list_tenants(
        self,
        status: Optional[TenantStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TenantModel]:
        """
        List tenants with optional filtering.
        
        Args:
            status: Filter by status
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of TenantModel instances
        """
        query = self.session.query(TenantModel)
        
        if status:
            query = query.filter(TenantModel.status == status)
        
        return query.offset(offset).limit(limit).all()
    
    def _generate_tenant_id(self, name: str) -> str:
        """
        Generate a unique tenant ID from name.
        
        Args:
            name: Tenant name
            
        Returns:
            Unique tenant ID
        """
        # Convert name to lowercase, replace spaces with hyphens
        base_id = name.lower().replace(" ", "-")
        # Remove special characters
        base_id = "".join(c for c in base_id if c.isalnum() or c == "-")
        # Truncate if too long
        base_id = base_id[:50]
        
        # Check if ID exists, append number if needed
        candidate_id = base_id
        counter = 1
        while self.session.query(TenantModel).filter(TenantModel.id == candidate_id).first():
            candidate_id = f"{base_id}-{counter}"
            counter += 1
        
        return candidate_id
    
    def _get_default_config(self) -> TenantConfig:
        """
        Get default tenant configuration.
        
        Returns:
            Default TenantConfig
        """
        return TenantConfig(
            features={
                "ai_annotation": True,
                "quality_assessment": True,
                "billing": True,
                "cross_tenant_sharing": False,
            },
            security={
                "mfa_required": False,
                "session_timeout_minutes": 60,
                "ip_whitelist_enabled": False,
                "ip_whitelist": [],
            },
            workspace_defaults={
                "default_role": "member",
                "allow_guest_access": False,
            },
            custom_settings={}
        )
    
    def _get_default_quota(self) -> TenantQuotaConfig:
        """
        Get default tenant quota.
        
        Returns:
            Default TenantQuotaConfig
        """
        return TenantQuotaConfig(
            storage_bytes=10 * 1024 * 1024 * 1024,  # 10GB
            project_count=100,
            user_count=50,
            api_call_count=100000,  # per month
        )
    
    def _log_audit(
        self,
        tenant_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log an audit entry.
        
        Args:
            tenant_id: Tenant ID
            action: Action performed
            resource_type: Type of resource
            resource_id: Resource ID
            details: Additional details
            user_id: User who performed the action
            ip_address: Client IP address
            user_agent: Client user agent
        """
        try:
            audit_log = TenantAuditLogModel(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.session.add(audit_log)
            self.session.flush()
            
            # Also call external audit logger if provided
            if self.audit_logger:
                self.audit_logger.log(action, tenant_id, details)
        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")
