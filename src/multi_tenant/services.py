"""
Multi-tenant services for tenant and workspace management.

This module provides services for managing tenants, workspaces, and user associations
in a multi-tenant environment.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from src.database.multi_tenant_models import (
    TenantModel, WorkspaceModel, UserTenantAssociationModel, 
    UserWorkspaceAssociationModel, TenantResourceUsageModel,
    TenantStatus, WorkspaceStatus, TenantRole, WorkspaceRole
)
from src.security.models import UserModel
from src.database.rls_policies import set_tenant_context, clear_tenant_context

logger = logging.getLogger(__name__)


class TenantManager:
    """Service for managing tenants and their configurations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_tenant(
        self,
        tenant_id: str,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        max_users: int = 100,
        max_workspaces: int = 10,
        max_storage_gb: float = 100.0,
        max_api_calls_per_hour: int = 10000,
        billing_email: Optional[str] = None,
        billing_plan: str = "basic"
    ) -> TenantModel:
        """
        Create a new tenant.
        
        Args:
            tenant_id: Unique tenant identifier
            name: Tenant name (for internal use)
            display_name: Display name for the tenant
            description: Optional description
            configuration: Tenant configuration dictionary
            max_users: Maximum number of users allowed
            max_workspaces: Maximum number of workspaces allowed
            max_storage_gb: Maximum storage in GB
            max_api_calls_per_hour: Maximum API calls per hour
            billing_email: Billing contact email
            billing_plan: Billing plan type
            
        Returns:
            TenantModel: Created tenant
            
        Raises:
            ValueError: If tenant_id already exists
        """
        # Check if tenant already exists
        existing = self.session.query(TenantModel).filter(TenantModel.id == tenant_id).first()
        if existing:
            raise ValueError(f"Tenant with ID '{tenant_id}' already exists")
        
        # Create tenant
        tenant = TenantModel(
            id=tenant_id,
            name=name,
            display_name=display_name,
            description=description,
            configuration=configuration or {},
            max_users=max_users,
            max_workspaces=max_workspaces,
            max_storage_gb=max_storage_gb,
            max_api_calls_per_hour=max_api_calls_per_hour,
            billing_email=billing_email,
            billing_plan=billing_plan,
            status=TenantStatus.ACTIVE
        )
        
        self.session.add(tenant)
        self.session.flush()  # Get the ID
        
        # Create default workspace
        default_workspace = WorkspaceModel(
            tenant_id=tenant_id,
            name="default",
            display_name="Default Workspace",
            description="Default workspace for the tenant",
            is_default=True,
            status=WorkspaceStatus.ACTIVE
        )
        
        self.session.add(default_workspace)
        self.session.commit()
        
        logger.info(f"Created tenant: {tenant_id} with default workspace")
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantModel]:
        """Get tenant by ID."""
        return self.session.query(TenantModel).filter(TenantModel.id == tenant_id).first()
    
    def update_tenant(
        self,
        tenant_id: str,
        **updates
    ) -> Optional[TenantModel]:
        """
        Update tenant information.
        
        Args:
            tenant_id: Tenant ID to update
            **updates: Fields to update
            
        Returns:
            Updated tenant or None if not found
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None
        
        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        tenant.updated_at = datetime.utcnow()
        self.session.commit()
        
        logger.info(f"Updated tenant: {tenant_id}")
        return tenant
    
    def deactivate_tenant(self, tenant_id: str) -> bool:
        """
        Deactivate a tenant (soft delete).
        
        Args:
            tenant_id: Tenant ID to deactivate
            
        Returns:
            True if successful, False if tenant not found
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        tenant.status = TenantStatus.SUSPENDED
        tenant.updated_at = datetime.utcnow()
        self.session.commit()
        
        logger.info(f"Deactivated tenant: {tenant_id}")
        return True
    
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
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of tenants
        """
        query = self.session.query(TenantModel)
        
        if status:
            query = query.filter(TenantModel.status == status)
        
        return query.offset(offset).limit(limit).all()
    
    def get_tenant_usage(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get current resource usage for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Dictionary with usage statistics
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return {}
        
        # Get latest usage record
        usage = self.session.query(TenantResourceUsageModel).filter(
            TenantResourceUsageModel.tenant_id == tenant_id
        ).order_by(TenantResourceUsageModel.usage_date.desc()).first()
        
        return {
            "tenant_id": tenant_id,
            "current_users": tenant.current_users,
            "current_workspaces": tenant.current_workspaces,
            "current_storage_gb": tenant.current_storage_gb,
            "max_users": tenant.max_users,
            "max_workspaces": tenant.max_workspaces,
            "max_storage_gb": tenant.max_storage_gb,
            "max_api_calls_per_hour": tenant.max_api_calls_per_hour,
            "usage_stats": {
                "api_calls": usage.api_calls if usage else 0,
                "storage_bytes": usage.storage_bytes if usage else 0,
                "annotation_count": usage.annotation_count if usage else 0,
                "last_updated": usage.usage_date.isoformat() if usage else None
            }
        }


class WorkspaceManager:
    """Service for managing workspaces within tenants."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_workspace(
        self,
        tenant_id: str,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        is_default: bool = False
    ) -> WorkspaceModel:
        """
        Create a new workspace within a tenant.
        
        Args:
            tenant_id: Parent tenant ID
            name: Workspace name (unique within tenant)
            display_name: Display name for the workspace
            description: Optional description
            configuration: Workspace configuration dictionary
            is_default: Whether this is the default workspace
            
        Returns:
            WorkspaceModel: Created workspace
            
        Raises:
            ValueError: If workspace name already exists in tenant
        """
        # Check if workspace name already exists in tenant
        existing = self.session.query(WorkspaceModel).filter(
            and_(
                WorkspaceModel.tenant_id == tenant_id,
                WorkspaceModel.name == name
            )
        ).first()
        
        if existing:
            raise ValueError(f"Workspace '{name}' already exists in tenant '{tenant_id}'")
        
        # If this is set as default, unset other defaults
        if is_default:
            self.session.query(WorkspaceModel).filter(
                and_(
                    WorkspaceModel.tenant_id == tenant_id,
                    WorkspaceModel.is_default == True
                )
            ).update({"is_default": False})
        
        # Create workspace
        workspace = WorkspaceModel(
            tenant_id=tenant_id,
            name=name,
            display_name=display_name,
            description=description,
            configuration=configuration or {},
            is_default=is_default,
            status=WorkspaceStatus.ACTIVE
        )
        
        self.session.add(workspace)
        self.session.commit()
        
        logger.info(f"Created workspace: {name} in tenant: {tenant_id}")
        return workspace
    
    def get_workspace(self, workspace_id: UUID) -> Optional[WorkspaceModel]:
        """Get workspace by ID."""
        return self.session.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
    
    def get_workspace_by_name(self, tenant_id: str, name: str) -> Optional[WorkspaceModel]:
        """Get workspace by name within a tenant."""
        return self.session.query(WorkspaceModel).filter(
            and_(
                WorkspaceModel.tenant_id == tenant_id,
                WorkspaceModel.name == name
            )
        ).first()
    
    def list_workspaces(
        self,
        tenant_id: str,
        status: Optional[WorkspaceStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[WorkspaceModel]:
        """
        List workspaces within a tenant.
        
        Args:
            tenant_id: Tenant ID
            status: Filter by status
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of workspaces
        """
        query = self.session.query(WorkspaceModel).filter(
            WorkspaceModel.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(WorkspaceModel.status == status)
        
        return query.offset(offset).limit(limit).all()
    
    def update_workspace(
        self,
        workspace_id: UUID,
        **updates
    ) -> Optional[WorkspaceModel]:
        """
        Update workspace information.
        
        Args:
            workspace_id: Workspace ID to update
            **updates: Fields to update
            
        Returns:
            Updated workspace or None if not found
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return None
        
        for key, value in updates.items():
            if hasattr(workspace, key):
                setattr(workspace, key, value)
        
        workspace.updated_at = datetime.utcnow()
        self.session.commit()
        
        logger.info(f"Updated workspace: {workspace_id}")
        return workspace
    
    def archive_workspace(self, workspace_id: UUID) -> bool:
        """
        Archive a workspace (soft delete).
        
        Args:
            workspace_id: Workspace ID to archive
            
        Returns:
            True if successful, False if workspace not found
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return False
        
        workspace.status = WorkspaceStatus.ARCHIVED
        workspace.archived_at = datetime.utcnow()
        workspace.updated_at = datetime.utcnow()
        self.session.commit()
        
        logger.info(f"Archived workspace: {workspace_id}")
        return True


class UserTenantManager:
    """Service for managing user-tenant associations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def invite_user_to_tenant(
        self,
        user_id: UUID,
        tenant_id: str,
        role: TenantRole = TenantRole.MEMBER,
        invited_by: Optional[UUID] = None,
        is_default_tenant: bool = False
    ) -> UserTenantAssociationModel:
        """
        Invite a user to a tenant.
        
        Args:
            user_id: User ID to invite
            tenant_id: Tenant ID
            role: Role to assign
            invited_by: User ID who sent the invitation
            is_default_tenant: Whether this is the user's default tenant
            
        Returns:
            UserTenantAssociationModel: Created association
            
        Raises:
            ValueError: If association already exists
        """
        # Check if association already exists
        existing = self.session.query(UserTenantAssociationModel).filter(
            and_(
                UserTenantAssociationModel.user_id == user_id,
                UserTenantAssociationModel.tenant_id == tenant_id
            )
        ).first()
        
        if existing:
            raise ValueError(f"User {user_id} is already associated with tenant {tenant_id}")
        
        # If this is set as default, unset other defaults for this user
        if is_default_tenant:
            self.session.query(UserTenantAssociationModel).filter(
                and_(
                    UserTenantAssociationModel.user_id == user_id,
                    UserTenantAssociationModel.is_default_tenant == True
                )
            ).update({"is_default_tenant": False})
        
        # Create association
        association = UserTenantAssociationModel(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            invited_by=invited_by,
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),  # Auto-accept for now
            is_default_tenant=is_default_tenant,
            is_active=True
        )
        
        self.session.add(association)
        self.session.commit()
        
        logger.info(f"Added user {user_id} to tenant {tenant_id} with role {role}")
        return association
    
    def remove_user_from_tenant(self, user_id: UUID, tenant_id: str) -> bool:
        """
        Remove a user from a tenant.
        
        Args:
            user_id: User ID to remove
            tenant_id: Tenant ID
            
        Returns:
            True if successful, False if association not found
        """
        association = self.session.query(UserTenantAssociationModel).filter(
            and_(
                UserTenantAssociationModel.user_id == user_id,
                UserTenantAssociationModel.tenant_id == tenant_id
            )
        ).first()
        
        if not association:
            return False
        
        self.session.delete(association)
        self.session.commit()
        
        logger.info(f"Removed user {user_id} from tenant {tenant_id}")
        return True
    
    def update_user_tenant_role(
        self,
        user_id: UUID,
        tenant_id: str,
        role: TenantRole
    ) -> Optional[UserTenantAssociationModel]:
        """
        Update a user's role in a tenant.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            role: New role
            
        Returns:
            Updated association or None if not found
        """
        association = self.session.query(UserTenantAssociationModel).filter(
            and_(
                UserTenantAssociationModel.user_id == user_id,
                UserTenantAssociationModel.tenant_id == tenant_id
            )
        ).first()
        
        if not association:
            return None
        
        association.role = role
        association.updated_at = datetime.utcnow()
        self.session.commit()
        
        logger.info(f"Updated user {user_id} role in tenant {tenant_id} to {role}")
        return association
    
    def get_user_tenants(self, user_id: UUID) -> List[UserTenantAssociationModel]:
        """Get all tenants for a user."""
        return self.session.query(UserTenantAssociationModel).filter(
            and_(
                UserTenantAssociationModel.user_id == user_id,
                UserTenantAssociationModel.is_active == True
            )
        ).all()
    
    def get_tenant_users(self, tenant_id: str) -> List[UserTenantAssociationModel]:
        """Get all users for a tenant."""
        return self.session.query(UserTenantAssociationModel).filter(
            and_(
                UserTenantAssociationModel.tenant_id == tenant_id,
                UserTenantAssociationModel.is_active == True
            )
        ).all()


class ResourceQuotaManager:
    """Service for managing tenant resource quotas and usage."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def check_quota(self, tenant_id: str, resource_type: str, requested_amount: int = 1) -> bool:
        """
        Check if a tenant has quota available for a resource.
        
        Args:
            tenant_id: Tenant ID
            resource_type: Type of resource (users, workspaces, storage, api_calls)
            requested_amount: Amount of resource requested
            
        Returns:
            True if quota is available, False otherwise
        """
        tenant = self.session.query(TenantModel).filter(TenantModel.id == tenant_id).first()
        if not tenant:
            return False
        
        if resource_type == "users":
            return tenant.current_users + requested_amount <= tenant.max_users
        elif resource_type == "workspaces":
            return tenant.current_workspaces + requested_amount <= tenant.max_workspaces
        elif resource_type == "storage":
            return tenant.current_storage_gb + requested_amount <= tenant.max_storage_gb
        
        return True
    
    def update_usage(
        self,
        tenant_id: str,
        resource_type: str,
        amount: int,
        operation: str = "add"
    ) -> bool:
        """
        Update resource usage for a tenant.
        
        Args:
            tenant_id: Tenant ID
            resource_type: Type of resource
            amount: Amount to add or subtract
            operation: "add" or "subtract"
            
        Returns:
            True if successful, False otherwise
        """
        tenant = self.session.query(TenantModel).filter(TenantModel.id == tenant_id).first()
        if not tenant:
            return False
        
        multiplier = 1 if operation == "add" else -1
        
        if resource_type == "users":
            tenant.current_users = max(0, tenant.current_users + (amount * multiplier))
        elif resource_type == "workspaces":
            tenant.current_workspaces = max(0, tenant.current_workspaces + (amount * multiplier))
        elif resource_type == "storage":
            tenant.current_storage_gb = max(0, tenant.current_storage_gb + (amount * multiplier))
        
        tenant.updated_at = datetime.utcnow()
        self.session.commit()
        
        return True
    
    def record_usage(
        self,
        tenant_id: str,
        api_calls: int = 0,
        storage_bytes: int = 0,
        annotation_count: int = 0,
        usage_date: Optional[datetime] = None
    ) -> TenantResourceUsageModel:
        """
        Record resource usage for a tenant.
        
        Args:
            tenant_id: Tenant ID
            api_calls: Number of API calls
            storage_bytes: Storage used in bytes
            annotation_count: Number of annotations
            usage_date: Date of usage (defaults to today)
            
        Returns:
            TenantResourceUsageModel: Usage record
        """
        if usage_date is None:
            usage_date = datetime.utcnow().date()
        
        # Check if record already exists for this date
        existing = self.session.query(TenantResourceUsageModel).filter(
            and_(
                TenantResourceUsageModel.tenant_id == tenant_id,
                func.date(TenantResourceUsageModel.usage_date) == usage_date
            )
        ).first()
        
        if existing:
            # Update existing record
            existing.api_calls += api_calls
            existing.storage_bytes += storage_bytes
            existing.annotation_count += annotation_count
            existing.updated_at = datetime.utcnow()
            usage_record = existing
        else:
            # Create new record
            usage_record = TenantResourceUsageModel(
                tenant_id=tenant_id,
                api_calls=api_calls,
                storage_bytes=storage_bytes,
                annotation_count=annotation_count,
                usage_date=usage_date
            )
            self.session.add(usage_record)
        
        self.session.commit()
        return usage_record


class UserWorkspaceManager:
    """Service for managing user-workspace associations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def add_user_to_workspace(
        self,
        user_id: UUID,
        workspace_id: UUID,
        role: WorkspaceRole = WorkspaceRole.ANNOTATOR
    ) -> UserWorkspaceAssociationModel:
        """
        Add a user to a workspace with a specific role.
        
        Args:
            user_id: User ID to add
            workspace_id: Workspace ID
            role: Role to assign
            
        Returns:
            UserWorkspaceAssociationModel: Created association
            
        Raises:
            ValueError: If association already exists
        """
        # Check if association already exists
        existing = self.session.query(UserWorkspaceAssociationModel).filter(
            and_(
                UserWorkspaceAssociationModel.user_id == user_id,
                UserWorkspaceAssociationModel.workspace_id == workspace_id
            )
        ).first()
        
        if existing:
            raise ValueError(f"User {user_id} is already associated with workspace {workspace_id}")
        
        # Create association
        association = UserWorkspaceAssociationModel(
            user_id=user_id,
            workspace_id=workspace_id,
            role=role,
            is_active=True
        )
        
        self.session.add(association)
        self.session.commit()
        
        logger.info(f"Added user {user_id} to workspace {workspace_id} with role {role}")
        return association
    
    def remove_user_from_workspace(self, user_id: UUID, workspace_id: UUID) -> bool:
        """
        Remove a user from a workspace.
        
        Args:
            user_id: User ID to remove
            workspace_id: Workspace ID
            
        Returns:
            True if successful, False if association not found
        """
        association = self.session.query(UserWorkspaceAssociationModel).filter(
            and_(
                UserWorkspaceAssociationModel.user_id == user_id,
                UserWorkspaceAssociationModel.workspace_id == workspace_id
            )
        ).first()
        
        if not association:
            return False
        
        self.session.delete(association)
        self.session.commit()
        
        logger.info(f"Removed user {user_id} from workspace {workspace_id}")
        return True
    
    def update_user_workspace_role(
        self,
        user_id: UUID,
        workspace_id: UUID,
        role: WorkspaceRole
    ) -> Optional[UserWorkspaceAssociationModel]:
        """
        Update a user's role in a workspace.
        
        Args:
            user_id: User ID
            workspace_id: Workspace ID
            role: New role
            
        Returns:
            Updated association or None if not found
        """
        association = self.session.query(UserWorkspaceAssociationModel).filter(
            and_(
                UserWorkspaceAssociationModel.user_id == user_id,
                UserWorkspaceAssociationModel.workspace_id == workspace_id
            )
        ).first()
        
        if not association:
            return None
        
        association.role = role
        association.updated_at = datetime.utcnow()
        self.session.commit()
        
        logger.info(f"Updated user {user_id} role in workspace {workspace_id} to {role}")
        return association
    
    def get_user_workspaces(self, user_id: UUID, tenant_id: str = None) -> List[UserWorkspaceAssociationModel]:
        """
        Get all workspaces for a user, optionally filtered by tenant.
        
        Args:
            user_id: User ID
            tenant_id: Optional tenant ID filter
            
        Returns:
            List of workspace associations
        """
        query = self.session.query(UserWorkspaceAssociationModel).filter(
            and_(
                UserWorkspaceAssociationModel.user_id == user_id,
                UserWorkspaceAssociationModel.is_active == True
            )
        ).join(WorkspaceModel)
        
        if tenant_id:
            query = query.filter(WorkspaceModel.tenant_id == tenant_id)
        
        return query.all()
    
    def get_workspace_users(self, workspace_id: UUID) -> List[UserWorkspaceAssociationModel]:
        """Get all users for a workspace."""
        return self.session.query(UserWorkspaceAssociationModel).filter(
            and_(
                UserWorkspaceAssociationModel.workspace_id == workspace_id,
                UserWorkspaceAssociationModel.is_active == True
            )
        ).all()


class PermissionService:
    """Service for checking tenant and workspace permissions."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def has_tenant_permission(
        self,
        user_id: UUID,
        tenant_id: str,
        required_role: TenantRole = TenantRole.MEMBER
    ) -> bool:
        """
        Check if a user has the required role in a tenant.
        
        Args:
            user_id: User ID to check
            tenant_id: Tenant ID
            required_role: Minimum required role
            
        Returns:
            True if user has permission, False otherwise
        """
        association = self.session.query(UserTenantAssociationModel).filter(
            and_(
                UserTenantAssociationModel.user_id == user_id,
                UserTenantAssociationModel.tenant_id == tenant_id,
                UserTenantAssociationModel.is_active == True
            )
        ).first()
        
        if not association:
            return False
        
        # Define role hierarchy
        role_hierarchy = {
            TenantRole.VIEWER: 1,
            TenantRole.MEMBER: 2,
            TenantRole.ADMIN: 3,
            TenantRole.OWNER: 4
        }
        
        user_role_level = role_hierarchy.get(association.role, 0)
        required_role_level = role_hierarchy.get(required_role, 0)
        
        return user_role_level >= required_role_level
    
    def has_workspace_permission(
        self,
        user_id: UUID,
        workspace_id: UUID,
        required_role: WorkspaceRole = WorkspaceRole.VIEWER
    ) -> bool:
        """
        Check if a user has the required role in a workspace.
        
        Args:
            user_id: User ID to check
            workspace_id: Workspace ID
            required_role: Minimum required role
            
        Returns:
            True if user has permission, False otherwise
        """
        association = self.session.query(UserWorkspaceAssociationModel).filter(
            and_(
                UserWorkspaceAssociationModel.user_id == user_id,
                UserWorkspaceAssociationModel.workspace_id == workspace_id,
                UserWorkspaceAssociationModel.is_active == True
            )
        ).first()
        
        if not association:
            return False
        
        # Define role hierarchy
        role_hierarchy = {
            WorkspaceRole.VIEWER: 1,
            WorkspaceRole.ANNOTATOR: 2,
            WorkspaceRole.REVIEWER: 3,
            WorkspaceRole.ADMIN: 4
        }
        
        user_role_level = role_hierarchy.get(association.role, 0)
        required_role_level = role_hierarchy.get(required_role, 0)
        
        return user_role_level >= required_role_level
    
    def can_access_workspace(self, user_id: UUID, workspace_id: UUID) -> bool:
        """
        Check if a user can access a workspace (either through workspace or tenant permissions).
        
        Args:
            user_id: User ID to check
            workspace_id: Workspace ID
            
        Returns:
            True if user can access workspace, False otherwise
        """
        # First check direct workspace permission
        if self.has_workspace_permission(user_id, workspace_id, WorkspaceRole.VIEWER):
            return True
        
        # Then check tenant-level permission
        workspace = self.session.query(WorkspaceModel).filter(
            WorkspaceModel.id == workspace_id
        ).first()
        
        if workspace and self.has_tenant_permission(user_id, workspace.tenant_id, TenantRole.MEMBER):
            return True
        
        return False
    
    def get_user_context(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get the current user's tenant and workspace context.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user's tenant and workspace information
        """
        # Get user's tenants
        tenant_associations = self.session.query(UserTenantAssociationModel).filter(
            and_(
                UserTenantAssociationModel.user_id == user_id,
                UserTenantAssociationModel.is_active == True
            )
        ).all()
        
        # Get user's workspaces
        workspace_associations = self.session.query(UserWorkspaceAssociationModel).filter(
            and_(
                UserWorkspaceAssociationModel.user_id == user_id,
                UserWorkspaceAssociationModel.is_active == True
            )
        ).join(WorkspaceModel).all()
        
        # Find default tenant
        default_tenant = None
        for assoc in tenant_associations:
            if assoc.is_default_tenant:
                default_tenant = assoc.tenant_id
                break
        
        return {
            "user_id": str(user_id),
            "tenants": [
                {
                    "tenant_id": assoc.tenant_id,
                    "role": assoc.role.value,
                    "is_default": assoc.is_default_tenant
                }
                for assoc in tenant_associations
            ],
            "workspaces": [
                {
                    "workspace_id": str(assoc.workspace_id),
                    "tenant_id": assoc.workspace.tenant_id,
                    "role": assoc.role.value,
                    "workspace_name": assoc.workspace.name
                }
                for assoc in workspace_associations
            ],
            "default_tenant": default_tenant,
            "total_tenants": len(tenant_associations),
            "total_workspaces": len(workspace_associations)
        }