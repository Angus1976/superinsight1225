"""
RBAC Service for role and permission management.

Provides high-level RBAC operations including role management, permission
assignment, and user role management with tenant isolation.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.database.connection import get_db_session
from .models import (
    RoleModel, PermissionModel, RolePermissionModel, UserRoleModel,
    ResourcePermissionModel, FieldPermissionModel,
    PermissionAction, ResourceType, FieldAccessLevel
)
from .permission_manager import PermissionManager, PermissionContext

logger = logging.getLogger(__name__)


class RBACService:
    """
    High-level RBAC service for role and permission management.
    
    Provides comprehensive role-based access control functionality with
    tenant isolation and hierarchical role support.
    """
    
    def __init__(self, permission_manager: Optional[PermissionManager] = None):
        self.permission_manager = permission_manager or PermissionManager()
    
    # ========================================================================
    # Role Management
    # ========================================================================
    
    def create_role(
        self,
        tenant_id: str,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        parent_role_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        db: Optional[Session] = None
    ) -> Optional[RoleModel]:
        """
        Create a new role in the tenant.
        
        Args:
            tenant_id: Tenant ID
            name: Role name (unique within tenant)
            display_name: Human-readable role name
            description: Role description
            parent_role_id: Parent role for inheritance
            created_by: User who created the role
            db: Database session
            
        Returns:
            Created role or None if failed
        """
        if db is None:
            db = next(get_db_session())
            
        try:
            # Check if role name already exists in tenant
            existing = db.query(RoleModel).filter(
                and_(
                    RoleModel.tenant_id == tenant_id,
                    RoleModel.name == name
                )
            ).first()
            
            if existing:
                logger.warning(f"Role {name} already exists in tenant {tenant_id}")
                return None
            
            # Determine role level
            level = 0
            if parent_role_id:
                parent_role = db.query(RoleModel).filter(RoleModel.id == parent_role_id).first()
                if parent_role:
                    level = parent_role.level + 1
            
            # Create role
            role = RoleModel(
                tenant_id=tenant_id,
                name=name,
                display_name=display_name,
                description=description,
                parent_role_id=parent_role_id,
                level=level,
                created_by=created_by
            )
            
            db.add(role)
            db.commit()
            db.refresh(role)
            
            logger.info(f"Role created: {name} in tenant {tenant_id}")
            return role
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating role: {e}")
            return None
    
    def get_role(self, role_id: UUID, db: Optional[Session] = None) -> Optional[RoleModel]:
        """Get role by ID."""
        if db is None:
            db = next(get_db_session())
            
        return db.query(RoleModel).filter(RoleModel.id == role_id).first()
    
    def get_tenant_roles(self, tenant_id: str, db: Optional[Session] = None) -> List[RoleModel]:
        """Get all roles in tenant."""
        if db is None:
            db = next(get_db_session())
            
        return db.query(RoleModel).filter(
            and_(
                RoleModel.tenant_id == tenant_id,
                RoleModel.is_active == True
            )
        ).order_by(RoleModel.level, RoleModel.name).all()
    
    def update_role(
        self,
        role_id: UUID,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        db: Optional[Session] = None
    ) -> bool:
        """Update role properties."""
        if db is None:
            db = next(get_db_session())
            
        try:
            role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
            if not role:
                return False
            
            if display_name is not None:
                role.display_name = display_name
            if description is not None:
                role.description = description
            if is_active is not None:
                role.is_active = is_active
            
            db.commit()
            logger.info(f"Role updated: {role.name}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating role: {e}")
            return False
    
    def delete_role(self, role_id: UUID, db: Optional[Session] = None) -> bool:
        """Soft delete role (deactivate)."""
        if db is None:
            db = next(get_db_session())
            
        try:
            role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
            if not role:
                return False
            
            # Check if role has active users
            active_users = db.query(UserRoleModel).filter(
                and_(
                    UserRoleModel.role_id == role_id,
                    UserRoleModel.is_active == True
                )
            ).count()
            
            if active_users > 0:
                logger.warning(f"Cannot delete role {role.name}: has {active_users} active users")
                return False
            
            role.is_active = False
            db.commit()
            
            logger.info(f"Role deleted: {role.name}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting role: {e}")
            return False
    
    # ========================================================================
    # Permission Management
    # ========================================================================
    
    def assign_permission_to_role(
        self,
        role_id: UUID,
        permission_id: UUID,
        granted_by: Optional[UUID] = None,
        conditions: Optional[Dict[str, Any]] = None,
        valid_until: Optional[datetime] = None,
        db: Optional[Session] = None
    ) -> bool:
        """
        Assign permission to role.
        
        Args:
            role_id: Role ID
            permission_id: Permission ID
            granted_by: User who granted the permission
            conditions: Additional conditions
            valid_until: Permission expiry date
            db: Database session
            
        Returns:
            True if permission assigned successfully
        """
        if db is None:
            db = next(get_db_session())
            
        try:
            # Check if assignment already exists
            existing = db.query(RolePermissionModel).filter(
                and_(
                    RolePermissionModel.role_id == role_id,
                    RolePermissionModel.permission_id == permission_id
                )
            ).first()
            
            if existing:
                # Update existing assignment
                existing.is_granted = True
                existing.conditions = conditions or {}
                existing.valid_until = valid_until
                existing.granted_by = granted_by
            else:
                # Create new assignment
                role_permission = RolePermissionModel(
                    role_id=role_id,
                    permission_id=permission_id,
                    is_granted=True,
                    conditions=conditions or {},
                    valid_until=valid_until,
                    granted_by=granted_by
                )
                db.add(role_permission)
            
            db.commit()
            logger.info(f"Permission {permission_id} assigned to role {role_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error assigning permission to role: {e}")
            return False
    
    def revoke_permission_from_role(
        self,
        role_id: UUID,
        permission_id: UUID,
        db: Optional[Session] = None
    ) -> bool:
        """Revoke permission from role."""
        if db is None:
            db = next(get_db_session())
            
        try:
            role_permission = db.query(RolePermissionModel).filter(
                and_(
                    RolePermissionModel.role_id == role_id,
                    RolePermissionModel.permission_id == permission_id
                )
            ).first()
            
            if role_permission:
                role_permission.is_granted = False
                db.commit()
                logger.info(f"Permission {permission_id} revoked from role {role_id}")
                return True
            
            return False
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error revoking permission from role: {e}")
            return False
    
    def get_role_permissions(self, role_id: UUID, db: Optional[Session] = None) -> List[PermissionModel]:
        """Get all permissions for a role."""
        if db is None:
            db = next(get_db_session())
            
        return db.query(PermissionModel).join(RolePermissionModel).filter(
            and_(
                RolePermissionModel.role_id == role_id,
                RolePermissionModel.is_granted == True,
                or_(
                    RolePermissionModel.valid_until.is_(None),
                    RolePermissionModel.valid_until > datetime.utcnow()
                )
            )
        ).all()
    
    # ========================================================================
    # User Role Management
    # ========================================================================
    
    def assign_role_to_user(
        self,
        user_id: UUID,
        role_id: UUID,
        tenant_id: str,
        assigned_by: UUID,
        is_primary: bool = False,
        valid_until: Optional[datetime] = None,
        assignment_reason: Optional[str] = None,
        db: Optional[Session] = None
    ) -> bool:
        """
        Assign role to user in tenant.
        
        Args:
            user_id: User ID
            role_id: Role ID
            tenant_id: Tenant ID
            assigned_by: User who assigned the role
            is_primary: Whether this is the primary role
            valid_until: Role assignment expiry
            assignment_reason: Reason for assignment
            db: Database session
            
        Returns:
            True if role assigned successfully
        """
        if db is None:
            db = next(get_db_session())
            
        try:
            # Check if assignment already exists
            existing = db.query(UserRoleModel).filter(
                and_(
                    UserRoleModel.user_id == user_id,
                    UserRoleModel.role_id == role_id,
                    UserRoleModel.tenant_id == tenant_id
                )
            ).first()
            
            if existing:
                # Update existing assignment
                existing.is_active = True
                existing.is_primary = is_primary
                existing.valid_until = valid_until
                existing.assignment_reason = assignment_reason
                existing.assigned_by = assigned_by
            else:
                # If this is primary role, unset other primary roles
                if is_primary:
                    db.query(UserRoleModel).filter(
                        and_(
                            UserRoleModel.user_id == user_id,
                            UserRoleModel.tenant_id == tenant_id,
                            UserRoleModel.is_primary == True
                        )
                    ).update({"is_primary": False})
                
                # Create new assignment
                user_role = UserRoleModel(
                    user_id=user_id,
                    role_id=role_id,
                    tenant_id=tenant_id,
                    assigned_by=assigned_by,
                    is_primary=is_primary,
                    valid_until=valid_until,
                    assignment_reason=assignment_reason
                )
                db.add(user_role)
            
            db.commit()
            logger.info(f"Role {role_id} assigned to user {user_id} in tenant {tenant_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error assigning role to user: {e}")
            return False
    
    def revoke_role_from_user(
        self,
        user_id: UUID,
        role_id: UUID,
        tenant_id: str,
        db: Optional[Session] = None
    ) -> bool:
        """Revoke role from user in tenant."""
        if db is None:
            db = next(get_db_session())
            
        try:
            user_role = db.query(UserRoleModel).filter(
                and_(
                    UserRoleModel.user_id == user_id,
                    UserRoleModel.role_id == role_id,
                    UserRoleModel.tenant_id == tenant_id
                )
            ).first()
            
            if user_role:
                user_role.is_active = False
                db.commit()
                logger.info(f"Role {role_id} revoked from user {user_id} in tenant {tenant_id}")
                return True
            
            return False
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error revoking role from user: {e}")
            return False
    
    def get_user_roles(
        self,
        user_id: UUID,
        tenant_id: str,
        db: Optional[Session] = None
    ) -> List[RoleModel]:
        """Get all active roles for user in tenant."""
        if db is None:
            db = next(get_db_session())
            
        return db.query(RoleModel).join(UserRoleModel).filter(
            and_(
                UserRoleModel.user_id == user_id,
                UserRoleModel.tenant_id == tenant_id,
                UserRoleModel.is_active == True,
                or_(
                    UserRoleModel.valid_until.is_(None),
                    UserRoleModel.valid_until > datetime.utcnow()
                ),
                RoleModel.is_active == True
            )
        ).all()
    
    def get_role_users(
        self,
        role_id: UUID,
        tenant_id: str,
        db: Optional[Session] = None
    ) -> List[UUID]:
        """Get all users with the specified role in tenant."""
        if db is None:
            db = next(get_db_session())
            
        user_roles = db.query(UserRoleModel).filter(
            and_(
                UserRoleModel.role_id == role_id,
                UserRoleModel.tenant_id == tenant_id,
                UserRoleModel.is_active == True,
                or_(
                    UserRoleModel.valid_until.is_(None),
                    UserRoleModel.valid_until > datetime.utcnow()
                )
            )
        ).all()
        
        return [ur.user_id for ur in user_roles]
    
    # ========================================================================
    # Field-Level Access Control
    # ========================================================================
    
    def set_field_permission(
        self,
        tenant_id: str,
        table_name: str,
        field_name: str,
        access_level: FieldAccessLevel,
        role_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        masking_config: Optional[Dict[str, Any]] = None,
        conditions: Optional[Dict[str, Any]] = None,
        created_by: UUID = None,
        db: Optional[Session] = None
    ) -> bool:
        """
        Set field-level access permission.
        
        Args:
            tenant_id: Tenant ID
            table_name: Table name
            field_name: Field name
            access_level: Access level (FULL, MASKED, HASHED, DENIED)
            role_id: Role ID (if role-based)
            user_id: User ID (if user-specific)
            masking_config: Masking configuration for MASKED access
            conditions: Additional conditions
            created_by: User who set the permission
            db: Database session
            
        Returns:
            True if permission set successfully
        """
        if db is None:
            db = next(get_db_session())
            
        if not role_id and not user_id:
            logger.error("Either role_id or user_id must be provided")
            return False
            
        try:
            # Check if permission already exists
            existing = db.query(FieldPermissionModel).filter(
                and_(
                    FieldPermissionModel.tenant_id == tenant_id,
                    FieldPermissionModel.table_name == table_name,
                    FieldPermissionModel.field_name == field_name,
                    FieldPermissionModel.role_id == role_id if role_id else True,
                    FieldPermissionModel.user_id == user_id if user_id else True
                )
            ).first()
            
            if existing:
                # Update existing permission
                existing.access_level = access_level
                existing.masking_config = masking_config or {}
                existing.conditions = conditions or {}
            else:
                # Create new permission
                field_permission = FieldPermissionModel(
                    tenant_id=tenant_id,
                    table_name=table_name,
                    field_name=field_name,
                    role_id=role_id,
                    user_id=user_id,
                    access_level=access_level,
                    masking_config=masking_config or {},
                    conditions=conditions or {},
                    created_by=created_by
                )
                db.add(field_permission)
            
            db.commit()
            logger.info(f"Field permission set: {table_name}.{field_name} -> {access_level.value}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error setting field permission: {e}")
            return False
    
    def get_field_permissions(
        self,
        tenant_id: str,
        table_name: Optional[str] = None,
        role_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        db: Optional[Session] = None
    ) -> List[FieldPermissionModel]:
        """Get field permissions based on filters."""
        if db is None:
            db = next(get_db_session())
            
        query = db.query(FieldPermissionModel).filter(
            FieldPermissionModel.tenant_id == tenant_id
        )
        
        if table_name:
            query = query.filter(FieldPermissionModel.table_name == table_name)
        if role_id:
            query = query.filter(FieldPermissionModel.role_id == role_id)
        if user_id:
            query = query.filter(FieldPermissionModel.user_id == user_id)
        
        return query.all()
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def check_user_permission(
        self,
        user_id: UUID,
        tenant_id: str,
        resource_type: ResourceType,
        action: PermissionAction,
        resource_id: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> bool:
        """
        Check if user has permission for action on resource.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            resource_type: Resource type
            action: Permission action
            resource_id: Specific resource ID
            request_context: Additional request context
            db: Database session
            
        Returns:
            True if user has permission
        """
        context = PermissionContext(
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            request_context=request_context
        )
        
        result = self.permission_manager.check_permission(context, db)
        return result.granted
    
    def get_user_accessible_resources(
        self,
        user_id: UUID,
        tenant_id: str,
        resource_type: ResourceType,
        action: PermissionAction,
        db: Optional[Session] = None
    ) -> List[str]:
        """
        Get list of resource IDs that user can access.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            resource_type: Resource type
            action: Permission action
            db: Database session
            
        Returns:
            List of accessible resource IDs
        """
        if db is None:
            db = next(get_db_session())
            
        # Get resource-specific permissions
        resource_perms = db.query(ResourcePermissionModel).filter(
            and_(
                ResourcePermissionModel.user_id == user_id,
                ResourcePermissionModel.tenant_id == tenant_id,
                ResourcePermissionModel.resource_type == resource_type,
                ResourcePermissionModel.action == action,
                ResourcePermissionModel.is_granted == True,
                or_(
                    ResourcePermissionModel.valid_until.is_(None),
                    ResourcePermissionModel.valid_until > datetime.utcnow()
                )
            )
        ).all()
        
        accessible_resources = [rp.resource_id for rp in resource_perms]
        
        # Check if user has general permission through roles
        if self.check_user_permission(user_id, tenant_id, resource_type, action, db=db):
            # User has general permission - would need to query actual resources
            # This is a simplified implementation
            pass
        
        return accessible_resources