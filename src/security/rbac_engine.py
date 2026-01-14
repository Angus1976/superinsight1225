"""
RBAC Engine for SuperInsight Platform.

Implements Role-Based Access Control with:
- Role creation and management
- Permission assignment
- Role inheritance
- Wildcard permission matching
- Permission caching
"""

import logging
import fnmatch
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select, func

from src.models.security import (
    RoleModel, UserRoleAssignmentModel, DynamicPolicyModel,
    AuditLogModel, SecurityEventModel, PolicyType
)

logger = logging.getLogger(__name__)


@dataclass
class Permission:
    """Permission data structure."""
    resource: str  # e.g., "projects/*", "datasets/123"
    action: str    # e.g., "read", "write", "delete", "*"
    conditions: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource": self.resource,
            "action": self.action,
            "conditions": self.conditions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Permission":
        return cls(
            resource=data.get("resource", "*"),
            action=data.get("action", "*"),
            conditions=data.get("conditions")
        )


@dataclass
class AccessDecision:
    """Access decision result."""
    allowed: bool
    reason: Optional[str] = None
    matched_permission: Optional[Permission] = None
    policy_applied: Optional[str] = None


class PermissionCache:
    """In-memory permission cache with TTL."""
    
    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.utcnow() - timestamp < self._ttl:
                return value
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set cache value with current timestamp."""
        self._cache[key] = (value, datetime.utcnow())
    
    def invalidate(self, pattern: str = "*") -> int:
        """Invalidate cache entries matching pattern."""
        if pattern == "*":
            count = len(self._cache)
            self._cache.clear()
            return count
        
        keys_to_remove = [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.utcnow()
        valid_count = sum(1 for _, (_, ts) in self._cache.items() if now - ts < self._ttl)
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_count,
            "ttl_seconds": self._ttl.total_seconds()
        }


class RBACEngine:
    """
    Role-Based Access Control Engine.
    
    Provides comprehensive RBAC functionality including:
    - Role creation and management
    - Permission assignment and checking
    - Role inheritance
    - Wildcard permission matching
    - Permission caching
    """
    
    def __init__(self, cache_ttl: int = 300):
        self.logger = logging.getLogger(__name__)
        self._cache = PermissionCache(ttl_seconds=cache_ttl)
    
    # ========================================================================
    # Role Management
    # ========================================================================
    
    def create_role(
        self,
        name: str,
        description: str,
        tenant_id: str,
        permissions: Optional[List[Dict[str, Any]]] = None,
        parent_role_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        is_system_role: bool = False,
        db: Session = None
    ) -> Optional[RoleModel]:
        """
        Create a new role.
        
        Args:
            name: Role name (unique within tenant)
            description: Role description
            tenant_id: Tenant identifier
            permissions: List of permission dictionaries
            parent_role_id: Parent role for inheritance
            created_by: User creating the role
            is_system_role: Whether this is a system-defined role
            db: Database session
            
        Returns:
            Created RoleModel or None if failed
        """
        try:
            # Check if role name already exists in tenant
            existing = db.query(RoleModel).filter(
                and_(
                    RoleModel.name == name,
                    RoleModel.tenant_id == tenant_id,
                    RoleModel.is_active == True
                )
            ).first()
            
            if existing:
                self.logger.warning(f"Role {name} already exists in tenant {tenant_id}")
                return None
            
            # Validate parent role if specified
            if parent_role_id:
                parent = db.query(RoleModel).filter(
                    and_(
                        RoleModel.id == parent_role_id,
                        RoleModel.tenant_id == tenant_id,
                        RoleModel.is_active == True
                    )
                ).first()
                if not parent:
                    self.logger.warning(f"Parent role {parent_role_id} not found")
                    return None
            
            # Create role
            role = RoleModel(
                name=name,
                description=description,
                tenant_id=tenant_id,
                permissions=permissions or [],
                parent_role_id=parent_role_id,
                created_by=created_by,
                is_system_role=is_system_role
            )
            
            db.add(role)
            db.commit()
            db.refresh(role)
            
            # Invalidate cache for tenant
            self._cache.invalidate(f"*:{tenant_id}:*")
            
            self.logger.info(f"Created role {name} in tenant {tenant_id}")
            return role
            
        except Exception as e:
            self.logger.error(f"Failed to create role {name}: {e}")
            db.rollback()
            return None
    
    def get_role(self, role_id: UUID, db: Session) -> Optional[RoleModel]:
        """Get role by ID."""
        return db.query(RoleModel).filter(
            and_(RoleModel.id == role_id, RoleModel.is_active == True)
        ).first()
    
    def get_role_by_name(
        self,
        name: str,
        tenant_id: str,
        db: Session
    ) -> Optional[RoleModel]:
        """Get role by name within tenant."""
        return db.query(RoleModel).filter(
            and_(
                RoleModel.name == name,
                RoleModel.tenant_id == tenant_id,
                RoleModel.is_active == True
            )
        ).first()
    
    def list_roles(
        self,
        tenant_id: str,
        include_inactive: bool = False,
        db: Session = None
    ) -> List[RoleModel]:
        """List all roles for a tenant."""
        query = db.query(RoleModel).filter(RoleModel.tenant_id == tenant_id)
        if not include_inactive:
            query = query.filter(RoleModel.is_active == True)
        return query.order_by(RoleModel.name).all()
    
    def update_role(
        self,
        role_id: UUID,
        updates: Dict[str, Any],
        db: Session
    ) -> bool:
        """Update role properties."""
        try:
            role = self.get_role(role_id, db)
            if not role:
                return False
            
            allowed_fields = ['name', 'description', 'permissions', 'is_active', 'role_metadata']
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(role, field, value)
            
            role.updated_at = datetime.utcnow()
            db.commit()
            
            # Invalidate cache
            self._cache.invalidate(f"*:{role.tenant_id}:*")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update role {role_id}: {e}")
            db.rollback()
            return False
    
    def delete_role(self, role_id: UUID, db: Session) -> bool:
        """Soft delete a role."""
        try:
            role = self.get_role(role_id, db)
            if not role:
                return False
            
            # Check if role has active assignments
            assignment_count = db.query(UserRoleAssignmentModel).filter(
                and_(
                    UserRoleAssignmentModel.role_id == role_id,
                    UserRoleAssignmentModel.is_active == True
                )
            ).count()
            
            if assignment_count > 0:
                self.logger.warning(f"Cannot delete role {role_id}: has {assignment_count} active assignments")
                return False
            
            role.is_active = False
            role.updated_at = datetime.utcnow()
            db.commit()
            
            # Invalidate cache
            self._cache.invalidate(f"*:{role.tenant_id}:*")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete role {role_id}: {e}")
            db.rollback()
            return False
    
    # ========================================================================
    # Role Assignment
    # ========================================================================
    
    def assign_role(
        self,
        user_id: UUID,
        role_id: UUID,
        assigned_by: Optional[UUID] = None,
        expires_at: Optional[datetime] = None,
        conditions: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Optional[UserRoleAssignmentModel]:
        """
        Assign a role to a user.
        
        Args:
            user_id: User to assign role to
            role_id: Role to assign
            assigned_by: User making the assignment
            expires_at: Optional expiration time
            conditions: Optional assignment conditions
            db: Database session
            
        Returns:
            UserRoleAssignmentModel or None if failed
        """
        try:
            # Verify role exists
            role = self.get_role(role_id, db)
            if not role:
                self.logger.warning(f"Role {role_id} not found")
                return None
            
            # Check for existing assignment
            existing = db.query(UserRoleAssignmentModel).filter(
                and_(
                    UserRoleAssignmentModel.user_id == user_id,
                    UserRoleAssignmentModel.role_id == role_id
                )
            ).first()
            
            if existing:
                if existing.is_active:
                    self.logger.info(f"User {user_id} already has role {role_id}")
                    return existing
                else:
                    # Reactivate existing assignment
                    existing.is_active = True
                    existing.assigned_by = assigned_by
                    existing.assigned_at = datetime.utcnow()
                    existing.expires_at = expires_at
                    existing.conditions = conditions
                    db.commit()
                    db.refresh(existing)
                    
                    # Invalidate cache
                    self._cache.invalidate(f"user:{user_id}:*")
                    
                    return existing
            
            # Create new assignment
            assignment = UserRoleAssignmentModel(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by,
                expires_at=expires_at,
                conditions=conditions
            )
            
            db.add(assignment)
            db.commit()
            db.refresh(assignment)
            
            # Invalidate cache
            self._cache.invalidate(f"user:{user_id}:*")
            
            self.logger.info(f"Assigned role {role_id} to user {user_id}")
            return assignment
            
        except Exception as e:
            self.logger.error(f"Failed to assign role {role_id} to user {user_id}: {e}")
            db.rollback()
            return None
    
    def revoke_role(
        self,
        user_id: UUID,
        role_id: UUID,
        db: Session
    ) -> bool:
        """Revoke a role from a user."""
        try:
            assignment = db.query(UserRoleAssignmentModel).filter(
                and_(
                    UserRoleAssignmentModel.user_id == user_id,
                    UserRoleAssignmentModel.role_id == role_id,
                    UserRoleAssignmentModel.is_active == True
                )
            ).first()
            
            if not assignment:
                return False
            
            assignment.is_active = False
            db.commit()
            
            # Invalidate cache
            self._cache.invalidate(f"user:{user_id}:*")
            
            self.logger.info(f"Revoked role {role_id} from user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to revoke role {role_id} from user {user_id}: {e}")
            db.rollback()
            return False
    
    def get_user_roles(self, user_id: UUID, db: Session) -> List[RoleModel]:
        """Get all active roles for a user."""
        now = datetime.utcnow()
        
        return db.query(RoleModel).join(
            UserRoleAssignmentModel,
            RoleModel.id == UserRoleAssignmentModel.role_id
        ).filter(
            and_(
                UserRoleAssignmentModel.user_id == user_id,
                UserRoleAssignmentModel.is_active == True,
                RoleModel.is_active == True,
                or_(
                    UserRoleAssignmentModel.expires_at.is_(None),
                    UserRoleAssignmentModel.expires_at > now
                )
            )
        ).all()
    
    # ========================================================================
    # Permission Checking
    # ========================================================================
    
    def check_permission(
        self,
        user_id: UUID,
        resource: str,
        action: str,
        tenant_id: str,
        db: Session
    ) -> AccessDecision:
        """
        Check if user has permission for resource/action.
        
        Args:
            user_id: User to check
            resource: Resource identifier (supports wildcards)
            action: Action to perform
            tenant_id: Tenant context
            db: Database session
            
        Returns:
            AccessDecision with result and details
        """
        # Check cache first
        cache_key = f"user:{user_id}:{tenant_id}:{resource}:{action}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Get user's permissions
        permissions = self._get_user_permissions(user_id, tenant_id, db)
        
        # Check for matching permission
        for perm in permissions:
            if self._match_permission(perm, resource, action):
                decision = AccessDecision(
                    allowed=True,
                    reason="Permission granted",
                    matched_permission=perm
                )
                self._cache.set(cache_key, decision)
                return decision
        
        decision = AccessDecision(
            allowed=False,
            reason="No matching permission found"
        )
        self._cache.set(cache_key, decision)
        return decision
    
    def _get_user_permissions(
        self,
        user_id: UUID,
        tenant_id: str,
        db: Session
    ) -> List[Permission]:
        """Get all permissions for a user (including inherited)."""
        cache_key = f"user_perms:{user_id}:{tenant_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Get user's roles
        roles = self.get_user_roles(user_id, db)
        
        # Collect all permissions (including inherited)
        all_permissions: Set[str] = set()
        for role in roles:
            role_perms = self._get_role_permissions_recursive(role, db)
            all_permissions.update(role_perms)
        
        # Convert to Permission objects
        permissions = []
        for perm_str in all_permissions:
            try:
                perm_dict = json.loads(perm_str)
                permissions.append(Permission.from_dict(perm_dict))
            except (json.JSONDecodeError, TypeError):
                # Handle simple string permissions
                parts = perm_str.split(":")
                if len(parts) >= 2:
                    permissions.append(Permission(resource=parts[0], action=parts[1]))
        
        self._cache.set(cache_key, permissions)
        return permissions
    
    def _get_role_permissions_recursive(
        self,
        role: RoleModel,
        db: Session,
        visited: Optional[Set[UUID]] = None
    ) -> Set[str]:
        """Recursively get role permissions including parent roles."""
        if visited is None:
            visited = set()
        
        # Prevent circular inheritance
        if role.id in visited:
            return set()
        visited.add(role.id)
        
        permissions = set()
        
        # Add role's direct permissions
        if role.permissions:
            for perm in role.permissions:
                if isinstance(perm, dict):
                    permissions.add(json.dumps(perm, sort_keys=True))
                else:
                    permissions.add(str(perm))
        
        # Add parent role's permissions
        if role.parent_role_id:
            parent = self.get_role(role.parent_role_id, db)
            if parent:
                parent_perms = self._get_role_permissions_recursive(parent, db, visited)
                permissions.update(parent_perms)
        
        return permissions
    
    def _match_permission(
        self,
        permission: Permission,
        resource: str,
        action: str
    ) -> bool:
        """
        Check if permission matches resource/action.
        
        Supports wildcards:
        - "*" matches everything
        - "projects/*" matches all projects
        - "projects/123" matches specific project
        """
        # Check action match
        if permission.action != "*" and permission.action != action:
            return False
        
        # Check resource match with wildcard support
        if permission.resource == "*":
            return True
        
        return fnmatch.fnmatch(resource, permission.resource)
    
    # ========================================================================
    # Batch Operations
    # ========================================================================
    
    def batch_check_permissions(
        self,
        user_id: UUID,
        checks: List[Tuple[str, str]],  # List of (resource, action) tuples
        tenant_id: str,
        db: Session
    ) -> Dict[str, AccessDecision]:
        """
        Check multiple permissions at once.
        
        Args:
            user_id: User to check
            checks: List of (resource, action) tuples
            tenant_id: Tenant context
            db: Database session
            
        Returns:
            Dictionary mapping "resource:action" to AccessDecision
        """
        results = {}
        
        # Get user permissions once
        permissions = self._get_user_permissions(user_id, tenant_id, db)
        
        for resource, action in checks:
            key = f"{resource}:{action}"
            
            # Check for matching permission
            matched = False
            matched_perm = None
            for perm in permissions:
                if self._match_permission(perm, resource, action):
                    matched = True
                    matched_perm = perm
                    break
            
            results[key] = AccessDecision(
                allowed=matched,
                reason="Permission granted" if matched else "No matching permission",
                matched_permission=matched_perm
            )
        
        return results
    
    # ========================================================================
    # Cache Management
    # ========================================================================
    
    def invalidate_user_cache(self, user_id: UUID) -> int:
        """Invalidate all cache entries for a user."""
        return self._cache.invalidate(f"user:{user_id}:*")
    
    def invalidate_tenant_cache(self, tenant_id: str) -> int:
        """Invalidate all cache entries for a tenant."""
        return self._cache.invalidate(f"*:{tenant_id}:*")
    
    def clear_cache(self) -> int:
        """Clear all cache entries."""
        return self._cache.invalidate("*")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()


# Global RBAC engine instance
_rbac_engine: Optional[RBACEngine] = None


def get_rbac_engine() -> RBACEngine:
    """Get or create the global RBAC engine instance."""
    global _rbac_engine
    if _rbac_engine is None:
        _rbac_engine = RBACEngine()
    return _rbac_engine
