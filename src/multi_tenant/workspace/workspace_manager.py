"""
Workspace Manager for Multi-Tenant Workspace module.

This module provides comprehensive workspace management including:
- Workspace creation with configuration inheritance
- Workspace hierarchy management (parent-child relationships)
- Workspace templates
- Archive and restore functionality
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.database.multi_tenant_models import TenantModel
from src.multi_tenant.workspace.models import (
    ExtendedWorkspaceModel,
    ExtendedWorkspaceStatus,
    WorkspaceTemplateModel,
    TenantAuditLogModel,
)
from src.multi_tenant.workspace.schemas import (
    WorkspaceCreateConfig,
    WorkspaceUpdateConfig,
    WorkspaceNode,
)
from src.multi_tenant.workspace.tenant_manager import TenantManager, TenantNotFoundError

logger = logging.getLogger(__name__)


class WorkspaceOperationError(Exception):
    """Exception raised for workspace operation errors."""
    pass


class WorkspaceNotFoundError(WorkspaceOperationError):
    """Exception raised when workspace is not found."""
    pass


class WorkspaceHierarchyError(WorkspaceOperationError):
    """Exception raised for hierarchy-related errors."""
    pass


class WorkspaceAlreadyExistsError(WorkspaceOperationError):
    """Exception raised when workspace already exists."""
    pass


class WorkspaceManager:
    """
    Workspace Manager for managing workspace lifecycle and hierarchy.
    
    Provides methods for:
    - Creating workspaces with configuration inheritance
    - Managing workspace hierarchy
    - Creating workspaces from templates
    - Archiving and restoring workspaces
    """
    
    def __init__(self, session: Session, tenant_manager: Optional[TenantManager] = None):
        """
        Initialize WorkspaceManager.
        
        Args:
            session: SQLAlchemy database session
            tenant_manager: Optional TenantManager for tenant operations
        """
        self.session = session
        self.tenant_manager = tenant_manager or TenantManager(session)
    
    def create_workspace(
        self,
        tenant_id: str,
        config: WorkspaceCreateConfig
    ) -> ExtendedWorkspaceModel:
        """
        Create a new workspace within a tenant.
        
        Args:
            tenant_id: Parent tenant ID
            config: Workspace creation configuration
            
        Returns:
            Created ExtendedWorkspaceModel instance
            
        Raises:
            TenantNotFoundError: If tenant not found
            WorkspaceAlreadyExistsError: If workspace name exists in same parent
            WorkspaceNotFoundError: If parent workspace not found
        """
        # Verify tenant exists
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant '{tenant_id}' not found")
        
        # Verify parent workspace if specified
        if config.parent_id:
            parent = self.get_workspace(config.parent_id)
            if not parent:
                raise WorkspaceNotFoundError(f"Parent workspace '{config.parent_id}' not found")
            if parent.tenant_id != tenant_id:
                raise WorkspaceHierarchyError("Parent workspace belongs to different tenant")
        
        # Check for duplicate name in same parent
        existing = self.session.query(ExtendedWorkspaceModel).filter(
            and_(
                ExtendedWorkspaceModel.tenant_id == tenant_id,
                ExtendedWorkspaceModel.name == config.name,
                ExtendedWorkspaceModel.parent_id == config.parent_id
            )
        ).first()
        if existing:
            raise WorkspaceAlreadyExistsError(
                f"Workspace '{config.name}' already exists in this location"
            )
        
        # Inherit configuration from tenant
        workspace_config = self._inherit_config_from_tenant(tenant, config.config)
        
        # Create workspace
        workspace = ExtendedWorkspaceModel(
            id=uuid4(),
            tenant_id=tenant_id,
            parent_id=config.parent_id,
            name=config.name,
            description=config.description,
            status=ExtendedWorkspaceStatus.ACTIVE,
            config=workspace_config,
        )
        
        self.session.add(workspace)
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=tenant_id,
            action="workspace_created",
            resource_type="workspace",
            resource_id=str(workspace.id),
            details={
                "name": config.name,
                "parent_id": str(config.parent_id) if config.parent_id else None,
            }
        )
        
        logger.info(f"Created workspace: {workspace.id} in tenant: {tenant_id}")
        return workspace
    
    def create_from_template(
        self,
        tenant_id: str,
        template_id: UUID,
        name: str,
        parent_id: Optional[UUID] = None
    ) -> ExtendedWorkspaceModel:
        """
        Create a workspace from a template.
        
        Args:
            tenant_id: Parent tenant ID
            template_id: Template ID to use
            name: Workspace name
            parent_id: Optional parent workspace ID
            
        Returns:
            Created ExtendedWorkspaceModel instance
            
        Raises:
            WorkspaceNotFoundError: If template not found
        """
        # Get template
        template = self.session.query(WorkspaceTemplateModel).filter(
            WorkspaceTemplateModel.id == template_id
        ).first()
        
        if not template:
            raise WorkspaceNotFoundError(f"Template '{template_id}' not found")
        
        # Verify template is accessible (system template or belongs to tenant)
        if not template.is_system and template.tenant_id != tenant_id:
            raise WorkspaceOperationError("Template not accessible to this tenant")
        
        # Create workspace with template config
        config = WorkspaceCreateConfig(
            name=name,
            description=template.description,
            parent_id=parent_id,
            config=template.config,
        )
        
        workspace = self.create_workspace(tenant_id, config)
        
        # Log template usage
        self._log_audit(
            tenant_id=tenant_id,
            action="workspace_created_from_template",
            resource_type="workspace",
            resource_id=str(workspace.id),
            details={
                "template_id": str(template_id),
                "template_name": template.name,
            }
        )
        
        return workspace
    
    def get_workspace(self, workspace_id: UUID) -> Optional[ExtendedWorkspaceModel]:
        """
        Get workspace by ID.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            ExtendedWorkspaceModel if found, None otherwise
        """
        return self.session.query(ExtendedWorkspaceModel).filter(
            ExtendedWorkspaceModel.id == workspace_id
        ).first()
    
    def get_workspace_or_raise(self, workspace_id: UUID) -> ExtendedWorkspaceModel:
        """
        Get workspace by ID or raise exception.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            ExtendedWorkspaceModel
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found")
        return workspace
    
    def update_workspace(
        self,
        workspace_id: UUID,
        updates: WorkspaceUpdateConfig
    ) -> ExtendedWorkspaceModel:
        """
        Update workspace information.
        
        Args:
            workspace_id: Workspace ID to update
            updates: Update configuration
            
        Returns:
            Updated ExtendedWorkspaceModel
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        workspace = self.get_workspace_or_raise(workspace_id)
        
        update_details = {}
        if updates.name is not None:
            workspace.name = updates.name
            update_details["name"] = updates.name
        
        if updates.description is not None:
            workspace.description = updates.description
            update_details["description"] = updates.description
        
        if updates.config is not None:
            workspace.config = {**workspace.config, **updates.config}
            update_details["config_updated"] = True
        
        workspace.updated_at = datetime.utcnow()
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="workspace_updated",
            resource_type="workspace",
            resource_id=str(workspace_id),
            details=update_details
        )
        
        logger.info(f"Updated workspace: {workspace_id}")
        return workspace
    
    def delete_workspace(self, workspace_id: UUID, hard_delete: bool = False) -> None:
        """
        Delete a workspace.
        
        Args:
            workspace_id: Workspace ID to delete
            hard_delete: If True, permanently delete; otherwise soft delete
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
            WorkspaceHierarchyError: If workspace has children
        """
        workspace = self.get_workspace_or_raise(workspace_id)
        
        # Check for children
        children = self.session.query(ExtendedWorkspaceModel).filter(
            ExtendedWorkspaceModel.parent_id == workspace_id
        ).count()
        
        if children > 0 and hard_delete:
            raise WorkspaceHierarchyError(
                f"Cannot delete workspace with {children} children. Delete children first."
            )
        
        tenant_id = workspace.tenant_id
        
        if hard_delete:
            self.session.delete(workspace)
        else:
            workspace.status = ExtendedWorkspaceStatus.DELETED
            workspace.updated_at = datetime.utcnow()
        
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=tenant_id,
            action="workspace_deleted" if hard_delete else "workspace_soft_deleted",
            resource_type="workspace",
            resource_id=str(workspace_id),
            details={"hard_delete": hard_delete}
        )
        
        logger.info(f"{'Deleted' if hard_delete else 'Soft deleted'} workspace: {workspace_id}")
    
    def archive_workspace(self, workspace_id: UUID) -> ExtendedWorkspaceModel:
        """
        Archive a workspace.
        
        Args:
            workspace_id: Workspace ID to archive
            
        Returns:
            Archived ExtendedWorkspaceModel
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        workspace = self.get_workspace_or_raise(workspace_id)
        
        workspace.status = ExtendedWorkspaceStatus.ARCHIVED
        workspace.archived_at = datetime.utcnow()
        workspace.updated_at = datetime.utcnow()
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="workspace_archived",
            resource_type="workspace",
            resource_id=str(workspace_id),
            details={}
        )
        
        logger.info(f"Archived workspace: {workspace_id}")
        return workspace
    
    def restore_workspace(self, workspace_id: UUID) -> ExtendedWorkspaceModel:
        """
        Restore an archived workspace.
        
        Args:
            workspace_id: Workspace ID to restore
            
        Returns:
            Restored ExtendedWorkspaceModel
            
        Raises:
            WorkspaceNotFoundError: If workspace not found
            WorkspaceOperationError: If workspace is not archived
        """
        workspace = self.get_workspace_or_raise(workspace_id)
        
        if workspace.status != ExtendedWorkspaceStatus.ARCHIVED:
            raise WorkspaceOperationError("Workspace is not archived")
        
        workspace.status = ExtendedWorkspaceStatus.ACTIVE
        workspace.archived_at = None
        workspace.updated_at = datetime.utcnow()
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="workspace_restored",
            resource_type="workspace",
            resource_id=str(workspace_id),
            details={}
        )
        
        logger.info(f"Restored workspace: {workspace_id}")
        return workspace
    
    def move_workspace(
        self,
        workspace_id: UUID,
        new_parent_id: Optional[UUID]
    ) -> ExtendedWorkspaceModel:
        """
        Move a workspace to a new parent (adjust hierarchy).
        
        Args:
            workspace_id: Workspace ID to move
            new_parent_id: New parent workspace ID (None for root)
            
        Returns:
            Moved ExtendedWorkspaceModel
            
        Raises:
            WorkspaceNotFoundError: If workspace or parent not found
            WorkspaceHierarchyError: If move would create cycle
        """
        workspace = self.get_workspace_or_raise(workspace_id)
        
        # Verify new parent if specified
        if new_parent_id:
            new_parent = self.get_workspace(new_parent_id)
            if not new_parent:
                raise WorkspaceNotFoundError(f"Parent workspace '{new_parent_id}' not found")
            if new_parent.tenant_id != workspace.tenant_id:
                raise WorkspaceHierarchyError("Cannot move workspace to different tenant")
            
            # Check for cycle (new parent cannot be descendant of workspace)
            if self._is_descendant(new_parent_id, workspace_id):
                raise WorkspaceHierarchyError("Cannot move workspace to its own descendant")
        
        old_parent_id = workspace.parent_id
        workspace.parent_id = new_parent_id
        workspace.updated_at = datetime.utcnow()
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="workspace_moved",
            resource_type="workspace",
            resource_id=str(workspace_id),
            details={
                "old_parent_id": str(old_parent_id) if old_parent_id else None,
                "new_parent_id": str(new_parent_id) if new_parent_id else None,
            }
        )
        
        logger.info(f"Moved workspace: {workspace_id} to parent: {new_parent_id}")
        return workspace
    
    def get_hierarchy(self, tenant_id: str) -> List[WorkspaceNode]:
        """
        Get workspace hierarchy for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            List of root WorkspaceNode instances with children
        """
        # Get all workspaces for tenant
        workspaces = self.session.query(ExtendedWorkspaceModel).filter(
            and_(
                ExtendedWorkspaceModel.tenant_id == tenant_id,
                ExtendedWorkspaceModel.status != ExtendedWorkspaceStatus.DELETED
            )
        ).all()
        
        # Build hierarchy
        workspace_map = {w.id: w for w in workspaces}
        children_map: Dict[Optional[UUID], List[ExtendedWorkspaceModel]] = {}
        
        for workspace in workspaces:
            parent_id = workspace.parent_id
            if parent_id not in children_map:
                children_map[parent_id] = []
            children_map[parent_id].append(workspace)
        
        def build_node(workspace: ExtendedWorkspaceModel) -> WorkspaceNode:
            children = children_map.get(workspace.id, [])
            return WorkspaceNode(
                id=workspace.id,
                tenant_id=UUID(workspace.tenant_id) if isinstance(workspace.tenant_id, str) else workspace.tenant_id,
                parent_id=workspace.parent_id,
                name=workspace.name,
                description=workspace.description,
                status=workspace.status,
                config=workspace.config,
                created_at=workspace.created_at,
                children=[build_node(c) for c in children]
            )
        
        # Build tree from root nodes
        root_workspaces = children_map.get(None, [])
        return [build_node(w) for w in root_workspaces]
    
    def list_workspaces(
        self,
        tenant_id: str,
        parent_id: Optional[UUID] = None,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[ExtendedWorkspaceModel]:
        """
        List workspaces for a tenant.
        
        Args:
            tenant_id: Tenant ID
            parent_id: Filter by parent (None for root workspaces)
            include_archived: Include archived workspaces
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of ExtendedWorkspaceModel instances
        """
        query = self.session.query(ExtendedWorkspaceModel).filter(
            ExtendedWorkspaceModel.tenant_id == tenant_id
        )
        
        if parent_id is not None:
            query = query.filter(ExtendedWorkspaceModel.parent_id == parent_id)
        
        if not include_archived:
            query = query.filter(
                ExtendedWorkspaceModel.status != ExtendedWorkspaceStatus.ARCHIVED
            )
        
        query = query.filter(
            ExtendedWorkspaceModel.status != ExtendedWorkspaceStatus.DELETED
        )
        
        return query.offset(offset).limit(limit).all()
    
    def _inherit_config_from_tenant(
        self,
        tenant: TenantModel,
        workspace_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Inherit configuration from tenant.
        
        Args:
            tenant: Parent tenant
            workspace_config: Optional workspace-specific config
            
        Returns:
            Merged configuration
        """
        # Get tenant's workspace defaults
        tenant_config = tenant.configuration or {}
        defaults = tenant_config.get("workspace_defaults", {})
        
        # Merge with workspace-specific config
        if workspace_config:
            return {**defaults, **workspace_config}
        return defaults
    
    def _is_descendant(self, potential_descendant_id: UUID, ancestor_id: UUID) -> bool:
        """
        Check if a workspace is a descendant of another.
        
        Args:
            potential_descendant_id: ID to check
            ancestor_id: Potential ancestor ID
            
        Returns:
            True if potential_descendant is a descendant of ancestor
        """
        current = self.get_workspace(potential_descendant_id)
        visited = set()
        
        while current and current.parent_id:
            if current.parent_id in visited:
                # Cycle detected (shouldn't happen, but safety check)
                return False
            visited.add(current.id)
            
            if current.parent_id == ancestor_id:
                return True
            current = self.get_workspace(current.parent_id)
        
        return False
    
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
