"""
Permission Manager for RBAC system.

Provides core permission checking and management functionality with caching
and performance optimization.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json
from functools import lru_cache
import redis
from dataclasses import dataclass

from src.database.connection import get_db_session
from .models import (
    RoleModel, PermissionModel, RolePermissionModel, UserRoleModel,
    ResourcePermissionModel, FieldPermissionModel, DataAccessAuditModel,
    PermissionAction, SyncResourceType, FieldAccessLevel, AuditEventType,
    ResourceType  # Re-exported from security module
)

logger = logging.getLogger(__name__)


@dataclass
class PermissionContext:
    """Context for permission evaluation."""
    user_id: UUID
    tenant_id: str
    resource_type: ResourceType
    resource_id: Optional[str] = None
    action: Optional[PermissionAction] = None
    field_name: Optional[str] = None
    table_name: Optional[str] = None
    request_context: Optional[Dict[str, Any]] = None


@dataclass
class PermissionResult:
    """Result of permission check."""
    granted: bool
    reason: str
    field_access_level: Optional[FieldAccessLevel] = None
    masking_config: Optional[Dict[str, Any]] = None
    conditions: Optional[Dict[str, Any]] = None


class PermissionManager:
    """
    Core permission management service.
    
    Handles permission checking, caching, and audit logging with high performance.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.permission_cache: Dict[str, PermissionResult] = {}
        
    def check_permission(
        self,
        context: PermissionContext,
        db: Optional[Session] = None
    ) -> PermissionResult:
        """
        Check if user has permission for the specified action.
        
        Args:
            context: Permission context with user, resource, and action details
            db: Database session (optional, will create if not provided)
            
        Returns:
            PermissionResult with grant status and details
        """
        if db is None:
            db = next(get_db_session())
            
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(context)
            
            # Check cache first
            cached_result = self._get_cached_permission(cache_key)
            if cached_result:
                logger.debug(f"Permission cache hit for {cache_key}")
                return cached_result
            
            # Perform permission check
            result = self._evaluate_permission(context, db)
            
            # Cache the result
            self._cache_permission(cache_key, result)
            
            # Log the access attempt
            self._log_access_attempt(context, result, db)
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            # Fail secure - deny permission on error
            return PermissionResult(
                granted=False,
                reason=f"Permission check failed: {str(e)}"
            )
    
    def check_field_access(
        self,
        user_id: UUID,
        tenant_id: str,
        table_name: str,
        field_name: str,
        db: Optional[Session] = None
    ) -> PermissionResult:
        """
        Check field-level access permissions.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            table_name: Table name
            field_name: Field name
            db: Database session
            
        Returns:
            PermissionResult with field access details
        """
        context = PermissionContext(
            user_id=user_id,
            tenant_id=tenant_id,
            resource_type=ResourceType.SYNC_JOB,  # Default resource type
            table_name=table_name,
            field_name=field_name
        )
        
        if db is None:
            db = next(get_db_session())
            
        # Check field-specific permissions
        field_permission = db.query(FieldPermissionModel).filter(
            and_(
                FieldPermissionModel.tenant_id == tenant_id,
                FieldPermissionModel.table_name == table_name,
                FieldPermissionModel.field_name == field_name,
                or_(
                    FieldPermissionModel.user_id == user_id,
                    FieldPermissionModel.role_id.in_(
                        self._get_user_role_ids(user_id, tenant_id, db)
                    )
                )
            )
        ).first()
        
        if field_permission:
            result = PermissionResult(
                granted=field_permission.access_level != FieldAccessLevel.DENIED,
                reason=f"Field permission: {field_permission.access_level.value}",
                field_access_level=field_permission.access_level,
                masking_config=field_permission.masking_config
            )
        else:
            # Default to full access if no specific field permission
            result = PermissionResult(
                granted=True,
                reason="Default field access",
                field_access_level=FieldAccessLevel.FULL
            )
        
        # Log field access
        self._log_access_attempt(context, result, db)
        
        return result
    
    def get_user_permissions(
        self,
        user_id: UUID,
        tenant_id: str,
        db: Optional[Session] = None
    ) -> Dict[str, List[str]]:
        """
        Get all permissions for a user grouped by resource type.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            db: Database session
            
        Returns:
            Dictionary mapping resource types to lists of actions
        """
        if db is None:
            db = next(get_db_session())
            
        permissions = {}
        
        # Get user roles
        user_roles = self._get_user_roles(user_id, tenant_id, db)
        
        for role in user_roles:
            # Get role permissions
            role_permissions = db.query(RolePermissionModel).join(
                PermissionModel
            ).filter(
                and_(
                    RolePermissionModel.role_id == role.id,
                    RolePermissionModel.is_granted == True
                )
            ).all()
            
            for role_perm in role_permissions:
                resource_type = role_perm.permission.resource_type.value
                action = role_perm.permission.action.value
                
                if resource_type not in permissions:
                    permissions[resource_type] = []
                
                if action not in permissions[resource_type]:
                    permissions[resource_type].append(action)
        
        return permissions
    
    def grant_permission(
        self,
        user_id: UUID,
        tenant_id: str,
        resource_type: ResourceType,
        resource_id: str,
        action: PermissionAction,
        granted_by: UUID,
        valid_until: Optional[datetime] = None,
        conditions: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> bool:
        """
        Grant specific resource permission to user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            resource_type: Resource type
            resource_id: Resource ID
            action: Permission action
            granted_by: User who granted the permission
            valid_until: Permission expiry date
            conditions: Additional conditions
            db: Database session
            
        Returns:
            True if permission granted successfully
        """
        if db is None:
            db = next(get_db_session())
            
        try:
            # Check if permission already exists
            existing = db.query(ResourcePermissionModel).filter(
                and_(
                    ResourcePermissionModel.user_id == user_id,
                    ResourcePermissionModel.tenant_id == tenant_id,
                    ResourcePermissionModel.resource_type == resource_type,
                    ResourcePermissionModel.resource_id == resource_id,
                    ResourcePermissionModel.action == action
                )
            ).first()
            
            if existing:
                # Update existing permission
                existing.is_granted = True
                existing.valid_until = valid_until
                existing.conditions = conditions or {}
                existing.granted_by = granted_by
            else:
                # Create new permission
                permission = ResourcePermissionModel(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action,
                    is_granted=True,
                    valid_until=valid_until,
                    conditions=conditions or {},
                    granted_by=granted_by
                )
                db.add(permission)
            
            db.commit()
            
            # Clear cache for this user
            self._clear_user_cache(user_id, tenant_id)
            
            logger.info(f"Permission granted: {user_id} -> {resource_type.value}:{resource_id}:{action.value}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error granting permission: {e}")
            return False
    
    def revoke_permission(
        self,
        user_id: UUID,
        tenant_id: str,
        resource_type: ResourceType,
        resource_id: str,
        action: PermissionAction,
        db: Optional[Session] = None
    ) -> bool:
        """
        Revoke specific resource permission from user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            resource_type: Resource type
            resource_id: Resource ID
            action: Permission action
            db: Database session
            
        Returns:
            True if permission revoked successfully
        """
        if db is None:
            db = next(get_db_session())
            
        try:
            permission = db.query(ResourcePermissionModel).filter(
                and_(
                    ResourcePermissionModel.user_id == user_id,
                    ResourcePermissionModel.tenant_id == tenant_id,
                    ResourcePermissionModel.resource_type == resource_type,
                    ResourcePermissionModel.resource_id == resource_id,
                    ResourcePermissionModel.action == action
                )
            ).first()
            
            if permission:
                permission.is_granted = False
                db.commit()
                
                # Clear cache for this user
                self._clear_user_cache(user_id, tenant_id)
                
                logger.info(f"Permission revoked: {user_id} -> {resource_type.value}:{resource_id}:{action.value}")
                return True
            
            return False
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error revoking permission: {e}")
            return False
    
    def _evaluate_permission(self, context: PermissionContext, db: Session) -> PermissionResult:
        """Evaluate permission based on roles and resource-specific grants."""
        
        # Check resource-specific permissions first (highest priority)
        if context.resource_id and context.action:
            resource_perm = db.query(ResourcePermissionModel).filter(
                and_(
                    ResourcePermissionModel.user_id == context.user_id,
                    ResourcePermissionModel.tenant_id == context.tenant_id,
                    ResourcePermissionModel.resource_type == context.resource_type,
                    ResourcePermissionModel.resource_id == context.resource_id,
                    ResourcePermissionModel.action == context.action,
                    ResourcePermissionModel.is_granted == True,
                    or_(
                        ResourcePermissionModel.valid_until.is_(None),
                        ResourcePermissionModel.valid_until > datetime.utcnow()
                    )
                )
            ).first()
            
            if resource_perm:
                return PermissionResult(
                    granted=True,
                    reason="Resource-specific permission",
                    conditions=resource_perm.conditions
                )
        
        # Check role-based permissions
        user_roles = self._get_user_roles(context.user_id, context.tenant_id, db)
        
        for role in user_roles:
            role_permissions = db.query(RolePermissionModel).join(
                PermissionModel
            ).filter(
                and_(
                    RolePermissionModel.role_id == role.id,
                    RolePermissionModel.is_granted == True,
                    PermissionModel.resource_type == context.resource_type,
                    PermissionModel.action == context.action if context.action else True,
                    or_(
                        RolePermissionModel.valid_until.is_(None),
                        RolePermissionModel.valid_until > datetime.utcnow()
                    )
                )
            ).all()
            
            if role_permissions:
                # Check conditions if any
                for role_perm in role_permissions:
                    if self._evaluate_conditions(role_perm.conditions, context):
                        return PermissionResult(
                            granted=True,
                            reason=f"Role permission: {role.name}",
                            conditions=role_perm.conditions
                        )
        
        # No permission found
        return PermissionResult(
            granted=False,
            reason="No matching permission found"
        )
    
    def _get_user_roles(self, user_id: UUID, tenant_id: str, db: Session) -> List[RoleModel]:
        """Get active roles for user in tenant."""
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
    
    def _get_user_role_ids(self, user_id: UUID, tenant_id: str, db: Session) -> List[UUID]:
        """Get role IDs for user."""
        roles = self._get_user_roles(user_id, tenant_id, db)
        return [role.id for role in roles]
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], context: PermissionContext) -> bool:
        """Evaluate permission conditions."""
        if not conditions:
            return True
        
        # Simple condition evaluation - can be extended
        for key, value in conditions.items():
            if key == "time_range":
                current_hour = datetime.utcnow().hour
                if not (value.get("start", 0) <= current_hour <= value.get("end", 23)):
                    return False
            elif key == "ip_range":
                # IP range checking would go here
                pass
            elif key == "resource_owner":
                # Check if user owns the resource
                if context.request_context and context.request_context.get("owner_id") != str(context.user_id):
                    return False
        
        return True
    
    def _generate_cache_key(self, context: PermissionContext) -> str:
        """Generate cache key for permission check."""
        parts = [
            str(context.user_id),
            context.tenant_id,
            context.resource_type.value,
            context.resource_id or "none",
            context.action.value if context.action else "none"
        ]
        return ":".join(parts)
    
    def _get_cached_permission(self, cache_key: str) -> Optional[PermissionResult]:
        """Get cached permission result."""
        if self.redis_client:
            try:
                cached = self.redis_client.get(f"perm:{cache_key}")
                if cached:
                    data = json.loads(cached)
                    return PermissionResult(**data)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        return self.permission_cache.get(cache_key)
    
    def _cache_permission(self, cache_key: str, result: PermissionResult) -> None:
        """Cache permission result."""
        if self.redis_client:
            try:
                data = {
                    "granted": result.granted,
                    "reason": result.reason,
                    "field_access_level": result.field_access_level.value if result.field_access_level else None,
                    "masking_config": result.masking_config,
                    "conditions": result.conditions
                }
                self.redis_client.setex(
                    f"perm:{cache_key}",
                    self.cache_ttl,
                    json.dumps(data)
                )
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
        
        # Fallback to in-memory cache
        self.permission_cache[cache_key] = result
    
    def _clear_user_cache(self, user_id: UUID, tenant_id: str) -> None:
        """Clear cached permissions for user."""
        if self.redis_client:
            try:
                pattern = f"perm:{user_id}:{tenant_id}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Cache clear error: {e}")
        
        # Clear in-memory cache
        keys_to_remove = [k for k in self.permission_cache.keys() if k.startswith(f"{user_id}:{tenant_id}:")]
        for key in keys_to_remove:
            del self.permission_cache[key]
    
    def _log_access_attempt(self, context: PermissionContext, result: PermissionResult, db: Session) -> None:
        """Log access attempt for audit purposes."""
        try:
            audit_log = DataAccessAuditModel(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                event_type=AuditEventType.PERMISSION_GRANTED if result.granted else AuditEventType.PERMISSION_DENIED,
                resource_type=context.resource_type,
                resource_id=context.resource_id,
                table_name=context.table_name,
                field_names=[context.field_name] if context.field_name else None,
                action=context.action,
                permission_granted=result.granted,
                request_context=context.request_context or {},
                response_context={
                    "reason": result.reason,
                    "field_access_level": result.field_access_level.value if result.field_access_level else None
                }
            )
            
            db.add(audit_log)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging access attempt: {e}")
            db.rollback()