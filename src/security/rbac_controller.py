"""
Role-Based Access Control (RBAC) Controller for SuperInsight Platform.

Extends the existing SecurityController with fine-grained RBAC capabilities,
including dynamic role management, permission hierarchies, and resource-level access control.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Union
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select, func

from src.security.controller import SecurityController
from src.security.models import (
    UserModel, UserRole, PermissionType, AuditAction
)
from src.security.rbac_models import (
    RoleModel, PermissionModel, RolePermissionModel, 
    UserRoleModel, ResourceModel, ResourcePermissionModel,
    PermissionScope, ResourceType
)
from src.security.permission_cache import get_permission_cache, get_cache_manager
from src.security.permission_audit_integration import get_permission_audit_integration

logger = logging.getLogger(__name__)


class RBACController(SecurityController):
    """
    Enhanced Role-Based Access Control controller.
    
    Extends SecurityController with comprehensive RBAC functionality including:
    - Dynamic role creation and management
    - Fine-grained permission assignment
    - Resource-level access control
    - Permission inheritance and hierarchies
    - Multi-tenant role isolation
    """
    
    def __init__(self, secret_key: str = "your-secret-key"):
        super().__init__(secret_key)
        # Use advanced caching system
        self.permission_cache = get_permission_cache()
        self.cache_manager = get_cache_manager()
        
        # Permission audit integration
        self.permission_audit = get_permission_audit_integration()
        
        # Legacy cache for backward compatibility
        self._permission_cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    # Role Management Methods
    
    def create_role(
        self,
        name: str,
        description: str,
        tenant_id: str,
        created_by: UUID,
        permissions: Optional[List[str]] = None,
        db: Session = None
    ) -> Optional[RoleModel]:
        """
        Create a new role with optional permissions.
        
        Args:
            name: Role name (unique within tenant)
            description: Role description
            tenant_id: Tenant identifier
            created_by: User creating the role
            permissions: List of permission names to assign
            db: Database session
            
        Returns:
            Created RoleModel or None if failed
        """
        try:
            # Check if role name already exists in tenant
            existing_role = db.query(RoleModel).filter(
                and_(
                    RoleModel.name == name,
                    RoleModel.tenant_id == tenant_id,
                    RoleModel.is_active == True
                )
            ).first()
            
            if existing_role:
                logger.warning(f"Role {name} already exists in tenant {tenant_id}")
                return None
            
            # Create role
            role = RoleModel(
                name=name,
                description=description,
                tenant_id=tenant_id,
                created_by=created_by
            )
            db.add(role)
            db.flush()  # Get the role ID
            
            # Assign permissions if provided
            if permissions:
                for permission_name in permissions:
                    permission = self.get_permission_by_name(permission_name, db)
                    if permission:
                        self.assign_permission_to_role(role.id, permission.id, db)
            
            db.commit()
            
            # Log role creation
            self.log_user_action(
                user_id=created_by,
                tenant_id=tenant_id,
                action=AuditAction.CREATE,
                resource_type="role",
                resource_id=str(role.id),
                details={"role_name": name, "permissions": permissions or []},
                db=db
            )
            
            return role
            
        except Exception as e:
            logger.error(f"Failed to create role {name}: {e}")
            db.rollback()
            return None
    
    def get_roles_for_tenant(
        self,
        tenant_id: str,
        include_inactive: bool = False,
        db: Session = None
    ) -> List[RoleModel]:
        """Get all roles for a tenant."""
        query = db.query(RoleModel).filter(RoleModel.tenant_id == tenant_id)
        
        if not include_inactive:
            query = query.filter(RoleModel.is_active == True)
        
        return query.order_by(RoleModel.name).all()
    
    def get_role_by_id(self, role_id: UUID, db: Session) -> Optional[RoleModel]:
        """Get a role by ID."""
        return db.query(RoleModel).filter(RoleModel.id == role_id).first()
    
    def update_role(
        self,
        role_id: UUID,
        updates: Dict[str, Any],
        updated_by: UUID,
        db: Session
    ) -> bool:
        """Update role properties."""
        try:
            role = self.get_role_by_id(role_id, db)
            if not role:
                return False
            
            # Update allowed fields
            allowed_fields = ['name', 'description', 'is_active']
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(role, field, value)
            
            role.updated_at = datetime.utcnow()
            db.commit()
            
            # Clear permission cache for this tenant
            self.cache_manager.handle_cache_invalidation(
                "tenant_update",
                {"tenant_id": role.tenant_id}
            )
            
            # Log role update
            self.log_user_action(
                user_id=updated_by,
                tenant_id=role.tenant_id,
                action=AuditAction.UPDATE,
                resource_type="role",
                resource_id=str(role_id),
                details={"updates": updates},
                db=db
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update role {role_id}: {e}")
            db.rollback()
            return False
    
    def delete_role(
        self,
        role_id: UUID,
        deleted_by: UUID,
        db: Session
    ) -> bool:
        """Soft delete a role (mark as inactive)."""
        try:
            role = self.get_role_by_id(role_id, db)
            if not role:
                return False
            
            # Check if role is assigned to any users
            user_count = db.query(UserRoleModel).filter(
                UserRoleModel.role_id == role_id
            ).count()
            
            if user_count > 0:
                logger.warning(f"Cannot delete role {role_id}: assigned to {user_count} users")
                return False
            
            role.is_active = False
            role.updated_at = datetime.utcnow()
            db.commit()
            
            # Clear permission cache
            self.cache_manager.handle_cache_invalidation(
                "tenant_update",
                {"tenant_id": role.tenant_id}
            )
            
            # Log role deletion
            self.log_user_action(
                user_id=deleted_by,
                tenant_id=role.tenant_id,
                action=AuditAction.DELETE,
                resource_type="role",
                resource_id=str(role_id),
                details={"role_name": role.name},
                db=db
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete role {role_id}: {e}")
            db.rollback()
            return False
    
    # Permission Management Methods
    
    def create_permission(
        self,
        name: str,
        description: str,
        scope: PermissionScope,
        resource_type: Optional[ResourceType] = None,
        created_by: UUID = None,
        db: Session = None
    ) -> Optional[PermissionModel]:
        """Create a new permission."""
        try:
            # Check if permission already exists
            existing = db.query(PermissionModel).filter(
                PermissionModel.name == name
            ).first()
            
            if existing:
                return existing
            
            permission = PermissionModel(
                name=name,
                description=description,
                scope=scope,
                resource_type=resource_type,
                created_by=created_by
            )
            db.add(permission)
            db.commit()
            
            return permission
            
        except Exception as e:
            logger.error(f"Failed to create permission {name}: {e}")
            db.rollback()
            return None
    
    def get_permission_by_name(self, name: str, db: Session) -> Optional[PermissionModel]:
        """Get permission by name."""
        return db.query(PermissionModel).filter(
            PermissionModel.name == name
        ).first()
    
    def assign_permission_to_role(
        self,
        role_id: UUID,
        permission_id: UUID,
        db: Session
    ) -> bool:
        """Assign a permission to a role."""
        try:
            # Check if assignment already exists
            existing = db.query(RolePermissionModel).filter(
                and_(
                    RolePermissionModel.role_id == role_id,
                    RolePermissionModel.permission_id == permission_id
                )
            ).first()
            
            if existing:
                return True
            
            assignment = RolePermissionModel(
                role_id=role_id,
                permission_id=permission_id
            )
            db.add(assignment)
            db.commit()
            
            # Clear permission cache
            role = self.get_role_by_id(role_id, db)
            if role:
                self.cache_manager.handle_cache_invalidation(
                    "role_permission_change",
                    {"role_id": str(role_id), "tenant_id": role.tenant_id}
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign permission {permission_id} to role {role_id}: {e}")
            db.rollback()
            return False
    
    def revoke_permission_from_role(
        self,
        role_id: UUID,
        permission_id: UUID,
        db: Session
    ) -> bool:
        """Revoke a permission from a role."""
        try:
            assignment = db.query(RolePermissionModel).filter(
                and_(
                    RolePermissionModel.role_id == role_id,
                    RolePermissionModel.permission_id == permission_id
                )
            ).first()
            
            if assignment:
                db.delete(assignment)
                db.commit()
                
                # Clear permission cache
                role = self.get_role_by_id(role_id, db)
                if role:
                    self.cache_manager.handle_cache_invalidation(
                        "role_permission_change",
                        {"role_id": str(role_id), "tenant_id": role.tenant_id}
                    )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to revoke permission {permission_id} from role {role_id}: {e}")
            db.rollback()
            return False
    
    # User Role Assignment Methods
    
    def assign_role_to_user(
        self,
        user_id: UUID,
        role_id: UUID,
        assigned_by: UUID,
        db: Session,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Assign a role to a user with audit logging."""
        try:
            # Verify user and role exist and are in same tenant
            user = self.get_user_by_id(user_id, db)
            role = self.get_role_by_id(role_id, db)
            
            if not user or not role:
                return False
            
            if user.tenant_id != role.tenant_id:
                logger.warning(f"Tenant mismatch: user {user_id} and role {role_id}")
                return False
            
            # Check if assignment already exists
            existing = db.query(UserRoleModel).filter(
                and_(
                    UserRoleModel.user_id == user_id,
                    UserRoleModel.role_id == role_id
                )
            ).first()
            
            if existing:
                return True
            
            assignment = UserRoleModel(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by
            )
            db.add(assignment)
            db.commit()
            
            # Clear permission cache
            self.cache_manager.handle_cache_invalidation(
                "user_role_change",
                {"user_id": str(user_id), "tenant_id": user.tenant_id}
            )
            
            # Log role assignment to audit system (async)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(
                    self.permission_audit.log_role_assignment(
                        user_id=user_id,
                        role_id=role_id,
                        assigned_by=assigned_by,
                        tenant_id=user.tenant_id,
                        role_name=role.name,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        db=db
                    )
                )
            except RuntimeError:
                # No event loop running, skip async logging
                pass
            
            # Log role assignment (existing audit)
            self.log_user_action(
                user_id=assigned_by,
                tenant_id=user.tenant_id,
                action=AuditAction.UPDATE,
                resource_type="user_role",
                resource_id=str(user_id),
                details={"role_assigned": role.name, "role_id": str(role_id)},
                db=db
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign role {role_id} to user {user_id}: {e}")
            db.rollback()
            return False
    
    def revoke_role_from_user(
        self,
        user_id: UUID,
        role_id: UUID,
        revoked_by: UUID,
        db: Session,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Revoke a role from a user with audit logging."""
        try:
            assignment = db.query(UserRoleModel).filter(
                and_(
                    UserRoleModel.user_id == user_id,
                    UserRoleModel.role_id == role_id
                )
            ).first()
            
            if assignment:
                role = self.get_role_by_id(role_id, db)
                user = self.get_user_by_id(user_id, db)
                
                db.delete(assignment)
                db.commit()
                
                # Clear permission cache
                self.cache_manager.handle_cache_invalidation(
                    "user_role_change",
                    {"user_id": str(user_id), "tenant_id": user.tenant_id}
                )
                
                # Log role revocation to audit system (async)
                if user and role:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            self.permission_audit.log_role_revocation(
                                user_id=user_id,
                                role_id=role_id,
                                revoked_by=revoked_by,
                                tenant_id=user.tenant_id,
                                role_name=role.name,
                                ip_address=ip_address,
                                user_agent=user_agent,
                                db=db
                            )
                        )
                    except RuntimeError:
                        # No event loop running, skip async logging
                        pass
                
                # Log role revocation (existing audit)
                if user and role:
                    self.log_user_action(
                        user_id=revoked_by,
                        tenant_id=user.tenant_id,
                        action=AuditAction.UPDATE,
                        resource_type="user_role",
                        resource_id=str(user_id),
                        details={"role_revoked": role.name, "role_id": str(role_id)},
                        db=db
                    )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to revoke role {role_id} from user {user_id}: {e}")
            db.rollback()
            return False
    
    def get_user_roles(self, user_id: UUID, db: Session) -> List[RoleModel]:
        """Get all roles assigned to a user."""
        return db.query(RoleModel).join(
            UserRoleModel, RoleModel.id == UserRoleModel.role_id
        ).filter(
            and_(
                UserRoleModel.user_id == user_id,
                RoleModel.is_active == True
            )
        ).all()
    
    def get_role_users(self, role_id: UUID, db: Session) -> List[UserModel]:
        """Get all users assigned to a role."""
        return db.query(UserModel).join(
            UserRoleModel, UserModel.id == UserRoleModel.user_id
        ).filter(
            and_(
                UserRoleModel.role_id == role_id,
                UserModel.is_active == True
            )
        ).all()
    
    # Enhanced Permission Checking Methods
    
    def check_user_permission(
        self,
        user_id: UUID,
        permission_name: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        db: Session = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Check if user has a specific permission with advanced caching and audit logging.
        
        Args:
            user_id: User identifier
            permission_name: Permission name to check
            resource_id: Optional specific resource ID
            resource_type: Optional resource type
            db: Database session
            ip_address: Optional IP address for audit logging
            user_agent: Optional user agent for audit logging
            
        Returns:
            True if user has permission
        """
        import time
        start_time = time.time()
        cache_hit = False
        result = False
        
        try:
            # Get user for tenant info
            user = self.get_user_by_id(user_id, db)
            if not user or not user.is_active:
                result = False
            else:
                # Check advanced cache first
                cached_result = self.permission_cache.get_permission(
                    user_id, permission_name, resource_id, resource_type, user.tenant_id
                )
                if cached_result is not None:
                    result = cached_result
                    cache_hit = True
                else:
                    # Admin users have all permissions
                    if user.role == UserRole.ADMIN:
                        result = True
                    else:
                        # Check through assigned roles
                        result = self._check_permission_through_roles(
                            user_id, permission_name, resource_id, resource_type, db
                        )
                    
                    # Cache result with advanced caching
                    self.permission_cache.set_permission(
                        user_id, permission_name, result, resource_id, resource_type, user.tenant_id
                    )
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Log permission check to audit system (async)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(
                    self.permission_audit.log_permission_check(
                        user_id=user_id,
                        tenant_id=user.tenant_id if user else "unknown",
                        permission_name=permission_name,
                        resource_id=resource_id,
                        resource_type=resource_type.value if resource_type else None,
                        result=result,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        cache_hit=cache_hit,
                        response_time_ms=response_time_ms,
                        db=db
                    )
                )
            except RuntimeError:
                # No event loop running, skip async logging
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"Permission check failed for user {user_id}, permission {permission_name}: {e}")
            return False
    
    def _check_permission_through_roles(
        self,
        user_id: UUID,
        permission_name: str,
        resource_id: Optional[str],
        resource_type: Optional[ResourceType],
        db: Session
    ) -> bool:
        """Check permission through user's assigned roles."""
        # Get user's roles and their permissions
        user_permissions = db.query(PermissionModel).join(
            RolePermissionModel, PermissionModel.id == RolePermissionModel.permission_id
        ).join(
            UserRoleModel, RolePermissionModel.role_id == UserRoleModel.role_id
        ).join(
            RoleModel, UserRoleModel.role_id == RoleModel.id
        ).filter(
            and_(
                UserRoleModel.user_id == user_id,
                RoleModel.is_active == True,
                PermissionModel.name == permission_name
            )
        ).all()
        
        if not user_permissions:
            return False
        
        # If no specific resource, check if user has the permission at all
        if not resource_id:
            return len(user_permissions) > 0
        
        # Check resource-specific permissions
        for permission in user_permissions:
            if permission.scope == PermissionScope.GLOBAL:
                return True
            elif permission.scope == PermissionScope.RESOURCE and resource_type:
                # Check if user has permission for this specific resource
                if self._check_resource_permission(user_id, resource_id, resource_type, permission.id, db):
                    return True
        
        return False
    
    def _check_resource_permission(
        self,
        user_id: UUID,
        resource_id: str,
        resource_type: ResourceType,
        permission_id: UUID,
        db: Session
    ) -> bool:
        """Check if user has permission for a specific resource."""
        # This would check resource-specific permissions
        # For now, we'll implement a basic check
        resource_permission = db.query(ResourcePermissionModel).filter(
            and_(
                ResourcePermissionModel.user_id == user_id,
                ResourcePermissionModel.resource_id == resource_id,
                ResourcePermissionModel.resource_type == resource_type,
                ResourcePermissionModel.permission_id == permission_id
            )
        ).first()
        
        return resource_permission is not None
    
    # Resource Management Methods
    
    def register_resource(
        self,
        resource_id: str,
        resource_type: ResourceType,
        name: str,
        tenant_id: str,
        owner_id: UUID,
        metadata: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Optional[ResourceModel]:
        """Register a new resource for permission management."""
        try:
            resource = ResourceModel(
                resource_id=resource_id,
                resource_type=resource_type,
                name=name,
                tenant_id=tenant_id,
                owner_id=owner_id,
                metadata=metadata or {}
            )
            db.add(resource)
            db.commit()
            
            return resource
            
        except Exception as e:
            logger.error(f"Failed to register resource {resource_id}: {e}")
            db.rollback()
            return None
    
    def grant_resource_permission(
        self,
        user_id: UUID,
        resource_id: str,
        resource_type: ResourceType,
        permission_id: UUID,
        granted_by: UUID,
        db: Session
    ) -> bool:
        """Grant a user permission for a specific resource."""
        try:
            # Check if permission already exists
            existing = db.query(ResourcePermissionModel).filter(
                and_(
                    ResourcePermissionModel.user_id == user_id,
                    ResourcePermissionModel.resource_id == resource_id,
                    ResourcePermissionModel.resource_type == resource_type,
                    ResourcePermissionModel.permission_id == permission_id
                )
            ).first()
            
            if existing:
                return True
            
            resource_permission = ResourcePermissionModel(
                user_id=user_id,
                resource_id=resource_id,
                resource_type=resource_type,
                permission_id=permission_id,
                granted_by=granted_by
            )
            db.add(resource_permission)
            db.commit()
            
            # Clear permission cache
            self.cache_manager.handle_cache_invalidation(
                "user_role_change",
                {"user_id": str(user_id), "tenant_id": None}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to grant resource permission: {e}")
            db.rollback()
            return False
    
    # Cache Management Methods
    
    def _clear_permission_cache(self, tenant_id: str):
        """Clear permission cache for a tenant (legacy method)."""
        keys_to_remove = [
            key for key in self._permission_cache.keys()
            if tenant_id in key
        ]
        for key in keys_to_remove:
            del self._permission_cache[key]
    
    def _clear_user_permission_cache(self, user_id: UUID):
        """Clear permission cache for a specific user (legacy method)."""
        keys_to_remove = [
            key for key in self._permission_cache.keys()
            if str(user_id) in key
        ]
        for key in keys_to_remove:
            del self._permission_cache[key]
    
    def clear_all_permission_cache(self):
        """Clear all permission cache."""
        self._permission_cache.clear()
        self.permission_cache.clear_all_cache()
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache performance statistics."""
        advanced_stats = self.permission_cache.get_cache_statistics()
        legacy_stats = {
            "legacy_cache_size": len(self._permission_cache),
            "legacy_cache_ttl": self._cache_ttl
        }
        
        return {
            **advanced_stats,
            **legacy_stats,
            "cache_system": "advanced_with_redis"
        }
    
    def optimize_permission_cache(self) -> Dict[str, Any]:
        """Analyze and optimize permission cache performance."""
        return self.permission_cache.optimize_cache()
    
    def warm_user_cache(
        self,
        user_id: UUID,
        common_permissions: Optional[List[str]] = None,
        db: Session = None
    ) -> bool:
        """
        Pre-warm cache with user's common permissions.
        
        Args:
            user_id: User to warm cache for
            common_permissions: List of common permissions to cache
            db: Database session
            
        Returns:
            True if successful
        """
        try:
            user = self.get_user_by_id(user_id, db)
            if not user:
                return False
            
            # Use provided permissions or default common ones
            if not common_permissions:
                common_permissions = [
                    "read_data", "write_data", "view_dashboard",
                    "manage_projects", "view_reports", "export_data"
                ]
            
            self.permission_cache.warm_user_permissions(
                user_id, common_permissions, user.tenant_id, db, self
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to warm cache for user {user_id}: {e}")
            return False
    
    def batch_check_permissions(
        self,
        user_id: UUID,
        permissions: List[str],
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        db: Session = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Check multiple permissions at once for better performance with audit logging.
        
        Args:
            user_id: User identifier
            permissions: List of permission names to check
            resource_id: Optional specific resource ID
            resource_type: Optional resource type
            db: Database session
            ip_address: Optional IP address for audit logging
            user_agent: Optional user agent for audit logging
            
        Returns:
            Dictionary mapping permission names to results
        """
        import time
        start_time = time.time()
        results = {}
        cache_hits = 0
        
        try:
            for permission_name in permissions:
                # Check cache first
                user = self.get_user_by_id(user_id, db)
                if user:
                    cached_result = self.permission_cache.get_permission(
                        user_id, permission_name, resource_id, resource_type, user.tenant_id
                    )
                    if cached_result is not None:
                        results[permission_name] = cached_result
                        cache_hits += 1
                        continue
                
                # Check permission normally
                results[permission_name] = self.check_user_permission(
                    user_id, permission_name, resource_id, resource_type, db
                )
            
            # Calculate total response time
            total_response_time_ms = (time.time() - start_time) * 1000
            
            # Log batch permission check to audit system (async)
            user = self.get_user_by_id(user_id, db)
            if user:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(
                        self.permission_audit.log_bulk_permission_check(
                            user_id=user_id,
                            tenant_id=user.tenant_id,
                            permissions=permissions,
                            results=results,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            cache_hits=cache_hits,
                            total_response_time_ms=total_response_time_ms,
                            db=db
                        )
                    )
                except RuntimeError:
                    # No event loop running, skip async logging
                    pass
            
            return results
            
        except Exception as e:
            logger.error(f"Batch permission check failed for user {user_id}: {e}")
            # Return False for all permissions on error
            return {perm: False for perm in permissions}
    
    # Utility Methods
    
    def get_user_effective_permissions(
        self,
        user_id: UUID,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get all effective permissions for a user."""
        user = self.get_user_by_id(user_id, db)
        if not user:
            return []
        
        permissions = []
        
        # Admin users have all permissions
        if user.role == UserRole.ADMIN:
            all_permissions = db.query(PermissionModel).all()
            for perm in all_permissions:
                permissions.append({
                    "permission": perm.name,
                    "scope": perm.scope.value,
                    "source": "admin_role",
                    "resource_type": perm.resource_type.value if perm.resource_type else None
                })
        else:
            # Get permissions through roles
            role_permissions = db.query(PermissionModel).join(
                RolePermissionModel, PermissionModel.id == RolePermissionModel.permission_id
            ).join(
                UserRoleModel, RolePermissionModel.role_id == UserRoleModel.role_id
            ).join(
                RoleModel, UserRoleModel.role_id == RoleModel.id
            ).filter(
                and_(
                    UserRoleModel.user_id == user_id,
                    RoleModel.is_active == True
                )
            ).all()
            
            for perm in role_permissions:
                permissions.append({
                    "permission": perm.name,
                    "scope": perm.scope.value,
                    "source": "role_assignment",
                    "resource_type": perm.resource_type.value if perm.resource_type else None
                })
        
        return permissions
    
    def validate_rbac_configuration(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        """Validate RBAC configuration for a tenant."""
        validation_result = {
            "valid": True,
            "issues": [],
            "statistics": {}
        }
        
        try:
            # Count roles and permissions
            roles_count = db.query(RoleModel).filter(
                and_(
                    RoleModel.tenant_id == tenant_id,
                    RoleModel.is_active == True
                )
            ).count()
            
            users_count = db.query(UserModel).filter(
                and_(
                    UserModel.tenant_id == tenant_id,
                    UserModel.is_active == True
                )
            ).count()
            
            # Check for users without roles
            users_without_roles = db.query(UserModel).filter(
                and_(
                    UserModel.tenant_id == tenant_id,
                    UserModel.is_active == True,
                    ~UserModel.id.in_(
                        db.query(UserRoleModel.user_id).distinct()
                    )
                )
            ).count()
            
            validation_result["statistics"] = {
                "roles_count": roles_count,
                "users_count": users_count,
                "users_without_roles": users_without_roles
            }
            
            # Add warnings for potential issues
            if users_without_roles > 0:
                validation_result["issues"].append(
                    f"{users_without_roles} users have no assigned roles"
                )
            
            if roles_count == 0:
                validation_result["issues"].append("No roles defined for tenant")
                validation_result["valid"] = False
            
        except Exception as e:
            logger.error(f"RBAC validation failed for tenant {tenant_id}: {e}")
            validation_result["valid"] = False
            validation_result["issues"].append(f"Validation error: {str(e)}")
        
        return validation_result