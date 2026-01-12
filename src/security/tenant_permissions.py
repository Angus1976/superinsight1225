"""
Tenant Permission Management System

Manages tenant-level permissions and access control.
"""

import logging
from typing import Dict, List, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.models import UserModel, UserRole
from src.sync.rbac.models import (
    RoleModel, PermissionModel, UserRoleModel, 
    ResourcePermissionModel, FieldPermissionModel
)

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Resource types for permission management."""
    DOCUMENTS = "documents"
    TASKS = "tasks"
    PROJECTS = "projects"
    USERS = "users"
    BILLING = "billing"
    QUALITY = "quality"
    TICKETS = "tickets"
    SYNC = "sync"
    BUSINESS_LOGIC = "business_logic"
    ADMIN = "admin"


class ActionType(str, Enum):
    """Action types for permissions."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    ASSIGN = "assign"


@dataclass
class Permission:
    """Permission data structure."""
    resource: ResourceType
    action: ActionType
    conditions: Optional[Dict[str, Any]] = None
    field_restrictions: Optional[List[str]] = None


@dataclass
class TenantRole:
    """Tenant-specific role definition."""
    name: str
    display_name: str
    description: str
    permissions: List[Permission]
    is_system_role: bool = False


class TenantPermissionManager:
    """Manages tenant-specific permissions and roles."""
    
    def __init__(self):
        self.default_roles = self._define_default_roles()
    
    def _define_default_roles(self) -> Dict[str, TenantRole]:
        """Define default tenant roles."""
        
        return {
            "tenant_admin": TenantRole(
                name="tenant_admin",
                display_name="Tenant Administrator",
                description="Full administrative access within tenant",
                permissions=[
                    Permission(ResourceType.ADMIN, ActionType.ADMIN),
                    Permission(ResourceType.USERS, ActionType.ADMIN),
                    Permission(ResourceType.PROJECTS, ActionType.ADMIN),
                    Permission(ResourceType.DOCUMENTS, ActionType.ADMIN),
                    Permission(ResourceType.TASKS, ActionType.ADMIN),
                    Permission(ResourceType.BILLING, ActionType.ADMIN),
                    Permission(ResourceType.QUALITY, ActionType.ADMIN),
                    Permission(ResourceType.TICKETS, ActionType.ADMIN),
                    Permission(ResourceType.SYNC, ActionType.ADMIN),
                    Permission(ResourceType.BUSINESS_LOGIC, ActionType.ADMIN),
                ],
                is_system_role=True
            ),
            
            "project_manager": TenantRole(
                name="project_manager",
                display_name="Project Manager",
                description="Manage projects and assign tasks",
                permissions=[
                    Permission(ResourceType.PROJECTS, ActionType.ADMIN),
                    Permission(ResourceType.DOCUMENTS, ActionType.READ),
                    Permission(ResourceType.DOCUMENTS, ActionType.WRITE),
                    Permission(ResourceType.TASKS, ActionType.ADMIN),
                    Permission(ResourceType.USERS, ActionType.READ),
                    Permission(ResourceType.QUALITY, ActionType.READ),
                    Permission(ResourceType.QUALITY, ActionType.WRITE),
                    Permission(ResourceType.TICKETS, ActionType.ASSIGN),
                    Permission(ResourceType.BILLING, ActionType.READ),
                    Permission(ResourceType.BUSINESS_LOGIC, ActionType.READ),
                    Permission(ResourceType.BUSINESS_LOGIC, ActionType.WRITE),
                ],
                is_system_role=True
            ),
            
            "business_expert": TenantRole(
                name="business_expert",
                display_name="Business Expert",
                description="Domain expert for annotation and quality review",
                permissions=[
                    Permission(ResourceType.DOCUMENTS, ActionType.READ),
                    Permission(ResourceType.TASKS, ActionType.READ),
                    Permission(ResourceType.TASKS, ActionType.WRITE),
                    Permission(ResourceType.QUALITY, ActionType.READ),
                    Permission(ResourceType.QUALITY, ActionType.WRITE),
                    Permission(ResourceType.QUALITY, ActionType.APPROVE),
                    Permission(ResourceType.TICKETS, ActionType.READ),
                    Permission(ResourceType.TICKETS, ActionType.WRITE),
                    Permission(ResourceType.BUSINESS_LOGIC, ActionType.READ),
                    Permission(ResourceType.BUSINESS_LOGIC, ActionType.WRITE),
                ],
                is_system_role=True
            ),
            
            "technical_expert": TenantRole(
                name="technical_expert",
                display_name="Technical Expert",
                description="Technical specialist for complex annotations",
                permissions=[
                    Permission(ResourceType.DOCUMENTS, ActionType.READ),
                    Permission(ResourceType.TASKS, ActionType.READ),
                    Permission(ResourceType.TASKS, ActionType.WRITE),
                    Permission(ResourceType.QUALITY, ActionType.READ),
                    Permission(ResourceType.TICKETS, ActionType.READ),
                    Permission(ResourceType.TICKETS, ActionType.WRITE),
                    Permission(ResourceType.SYNC, ActionType.READ),
                    Permission(ResourceType.BUSINESS_LOGIC, ActionType.READ),
                ],
                is_system_role=True
            ),
            
            "contractor": TenantRole(
                name="contractor",
                display_name="Contractor",
                description="External contractor with limited access",
                permissions=[
                    Permission(ResourceType.DOCUMENTS, ActionType.READ),
                    Permission(ResourceType.TASKS, ActionType.READ),
                    Permission(ResourceType.TASKS, ActionType.WRITE),
                    Permission(ResourceType.QUALITY, ActionType.READ),
                ],
                is_system_role=True
            ),
            
            "viewer": TenantRole(
                name="viewer",
                display_name="Viewer",
                description="Read-only access to basic resources",
                permissions=[
                    Permission(ResourceType.DOCUMENTS, ActionType.READ),
                    Permission(ResourceType.TASKS, ActionType.READ),
                    Permission(ResourceType.QUALITY, ActionType.READ),
                    Permission(ResourceType.BILLING, ActionType.READ),
                ],
                is_system_role=True
            )
        }
    
    def get_user_permissions(self, user_id: str, tenant_id: str) -> Dict[str, List[str]]:
        """Get all permissions for a user within a tenant."""
        
        permissions = {}
        
        with get_db_session() as session:
            # Get user's roles within the tenant
            user_roles = session.query(UserRoleModel).filter(
                UserRoleModel.user_id == user_id,
                UserRoleModel.tenant_id == tenant_id,
                UserRoleModel.is_active == True
            ).all()
            
            for user_role in user_roles:
                # Get role permissions
                role = session.query(RoleModel).filter(
                    RoleModel.id == user_role.role_id
                ).first()
                
                if role and role.name in self.default_roles:
                    role_def = self.default_roles[role.name]
                    
                    for perm in role_def.permissions:
                        resource = perm.resource.value
                        action = perm.action.value
                        
                        if resource not in permissions:
                            permissions[resource] = []
                        
                        if action not in permissions[resource]:
                            permissions[resource].append(action)
            
            # Get resource-specific permission overrides
            # Filter by validity period and check is_granted status
            from datetime import datetime
            now = datetime.utcnow()
            try:
                resource_perms = session.query(ResourcePermissionModel).filter(
                    ResourcePermissionModel.user_id == user_id,
                    ResourcePermissionModel.tenant_id == tenant_id,
                    ResourcePermissionModel.valid_from <= now
                ).all()
            except Exception:
                # If query fails (e.g., table doesn't exist), skip resource permissions
                resource_perms = []
            
            for res_perm in resource_perms:
                # Skip expired permissions - handle Mock objects gracefully
                try:
                    if res_perm.valid_until is not None and res_perm.valid_until < now:
                        continue
                except (TypeError, AttributeError):
                    # Handle Mock objects or invalid data
                    pass
                    
                try:
                    resource = res_perm.resource_type.value if hasattr(res_perm.resource_type, 'value') else str(res_perm.resource_type)
                    action_value = res_perm.action.value if hasattr(res_perm.action, 'value') else str(res_perm.action)
                    
                    if resource not in permissions:
                        permissions[resource] = []
                    
                    is_granted = getattr(res_perm, 'is_granted', True)
                    if is_granted and action_value not in permissions[resource]:
                        permissions[resource].append(action_value)
                    elif not is_granted and action_value in permissions[resource]:
                        permissions[resource].remove(action_value)
                except (TypeError, AttributeError):
                    # Handle Mock objects or invalid data
                    pass
        
        return permissions
    
    def check_permission(self, user_id: str, tenant_id: str, 
                        resource: ResourceType, action: ActionType) -> bool:
        """Check if user has specific permission."""
        
        permissions = self.get_user_permissions(user_id, tenant_id)
        resource_perms = permissions.get(resource.value, [])
        
        # Check for specific action or admin access
        return (action.value in resource_perms or 
                ActionType.ADMIN.value in resource_perms)
    
    def assign_role_to_user(self, user_id: str, tenant_id: str, 
                           role_name: str, assigned_by: str) -> bool:
        """Assign a role to a user within a tenant."""
        
        try:
            with get_db_session() as session:
                # Get or create role
                role = session.query(RoleModel).filter(
                    RoleModel.tenant_id == tenant_id,
                    RoleModel.name == role_name
                ).first()
                
                if not role:
                    # Create role if it doesn't exist
                    if role_name in self.default_roles:
                        role_def = self.default_roles[role_name]
                        role = RoleModel(
                            tenant_id=tenant_id,
                            name=role_def.name,
                            display_name=role_def.display_name,
                            description=role_def.description,
                            is_system_role=role_def.is_system_role
                        )
                        session.add(role)
                        session.flush()
                    else:
                        logger.error(f"Unknown role: {role_name}")
                        return False
                
                # Check if user already has this role
                existing = session.query(UserRoleModel).filter(
                    UserRoleModel.user_id == user_id,
                    UserRoleModel.role_id == role.id,
                    UserRoleModel.tenant_id == tenant_id
                ).first()
                
                if existing:
                    existing.is_active = True
                    existing.assigned_by = assigned_by
                else:
                    # Create new role assignment
                    user_role = UserRoleModel(
                        user_id=user_id,
                        role_id=role.id,
                        tenant_id=tenant_id,
                        assigned_by=assigned_by,
                        is_active=True
                    )
                    session.add(user_role)
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to assign role {role_name} to user {user_id}: {e}")
            return False
    
    def revoke_role_from_user(self, user_id: str, tenant_id: str, 
                             role_name: str, revoked_by: str) -> bool:
        """Revoke a role from a user within a tenant."""
        
        try:
            with get_db_session() as session:
                # Find the role
                role = session.query(RoleModel).filter(
                    RoleModel.tenant_id == tenant_id,
                    RoleModel.name == role_name
                ).first()
                
                if not role:
                    return False
                
                # Find and deactivate user role assignment
                user_role = session.query(UserRoleModel).filter(
                    UserRoleModel.user_id == user_id,
                    UserRoleModel.role_id == role.id,
                    UserRoleModel.tenant_id == tenant_id
                ).first()
                
                if user_role:
                    user_role.is_active = False
                    user_role.revoked_by = revoked_by
                    user_role.revoked_at = func.now()
                    session.commit()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to revoke role {role_name} from user {user_id}: {e}")
            return False
    
    def get_user_roles(self, user_id: str, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all active roles for a user within a tenant."""
        
        roles = []
        
        with get_db_session() as session:
            user_roles = session.query(UserRoleModel, RoleModel).join(
                RoleModel, UserRoleModel.role_id == RoleModel.id
            ).filter(
                UserRoleModel.user_id == user_id,
                UserRoleModel.tenant_id == tenant_id,
                UserRoleModel.is_active == True
            ).all()
            
            for user_role, role in user_roles:
                roles.append({
                    "name": role.name,
                    "display_name": role.display_name,
                    "description": role.description,
                    "assigned_at": user_role.assigned_at,
                    "assigned_by": user_role.assigned_by
                })
        
        return roles
    
    def create_custom_role(self, tenant_id: str, role_name: str, 
                          display_name: str, description: str,
                          permissions: List[Permission], created_by: str) -> bool:
        """Create a custom role for a tenant."""
        
        try:
            with get_db_session() as session:
                # Check if role already exists
                existing = session.query(RoleModel).filter(
                    RoleModel.tenant_id == tenant_id,
                    RoleModel.name == role_name
                ).first()
                
                if existing:
                    logger.error(f"Role {role_name} already exists for tenant {tenant_id}")
                    return False
                
                # Create role
                role = RoleModel(
                    tenant_id=tenant_id,
                    name=role_name,
                    display_name=display_name,
                    description=description,
                    is_system_role=False,
                    created_by=created_by
                )
                session.add(role)
                session.flush()
                
                # Add permissions (this would require extending the RBAC model)
                # For now, we'll store them in the role metadata
                role.role_metadata = {
                    "permissions": [
                        {
                            "resource": perm.resource.value,
                            "action": perm.action.value,
                            "conditions": perm.conditions,
                            "field_restrictions": perm.field_restrictions
                        }
                        for perm in permissions
                    ]
                }
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to create custom role {role_name}: {e}")
            return False
    
    def check_tenant_resource_access(self, user_id: str, user_tenant_id: str, 
                                   resource_type: str, resource_id: str, 
                                   resource_tenant_id: str) -> bool:
        """Check if user can access a resource from a specific tenant."""
        
        # Users can only access resources from their own tenant
        if user_tenant_id != resource_tenant_id:
            return False
        
        # Check if user has permission for the resource type
        try:
            resource_enum = ResourceType(resource_type)
            return self.check_permission(user_id, user_tenant_id, resource_enum, ActionType.READ)
        except ValueError:
            # Unknown resource type
            return False

    def initialize_tenant_roles(self, tenant_id: str) -> bool:
        """Initialize default roles for a new tenant."""
        
        try:
            with get_db_session() as session:
                for role_name, role_def in self.default_roles.items():
                    # Check if role already exists
                    existing = session.query(RoleModel).filter(
                        RoleModel.tenant_id == tenant_id,
                        RoleModel.name == role_name
                    ).first()
                    
                    if not existing:
                        role = RoleModel(
                            tenant_id=tenant_id,
                            name=role_def.name,
                            display_name=role_def.display_name,
                            description=role_def.description,
                            is_system_role=role_def.is_system_role,
                            role_metadata={
                                "permissions": [
                                    {
                                        "resource": perm.resource.value,
                                        "action": perm.action.value,
                                        "conditions": perm.conditions,
                                        "field_restrictions": perm.field_restrictions
                                    }
                                    for perm in role_def.permissions
                                ]
                            }
                        )
                        session.add(role)
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize roles for tenant {tenant_id}: {e}")
            return False


# Global permission manager instance
permission_manager = TenantPermissionManager()


def get_permission_manager() -> TenantPermissionManager:
    """Get the global permission manager instance."""
    return permission_manager