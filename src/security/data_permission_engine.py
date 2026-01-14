"""
Data Permission Engine for SuperInsight Platform.

Implements data-level permission control including:
- Dataset/Record/Field level permissions
- Tag-based permissions (ABAC)
- Temporary permission grants
- Permission caching with Redis
"""

import logging
import json
import fnmatch
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select

from src.models.data_permission import (
    DataPermissionModel, DataPermissionAction, ResourceLevel,
    DataClassificationModel, SensitivityLevel
)
from src.schemas.data_permission import (
    PermissionResult, GrantPermissionRequest, TemporaryGrant
)

logger = logging.getLogger(__name__)


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


class DataPermissionEngine:
    """
    Data Permission Engine.
    
    Provides comprehensive data-level permission control:
    - Dataset level permissions
    - Record level permissions (row-level security)
    - Field level permissions (column-level security)
    - Tag-based permissions (ABAC)
    - Temporary permission grants
    - Permission caching
    """
    
    def __init__(self, cache_ttl: int = 300, redis_client=None):
        self.logger = logging.getLogger(__name__)
        self._local_cache = PermissionCache(ttl_seconds=cache_ttl)
        self._redis = redis_client
        self._cache_ttl = cache_ttl
    
    # ========================================================================
    # Permission Checking
    # ========================================================================
    
    async def check_dataset_permission(
        self,
        user_id: str,
        dataset_id: str,
        action: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> PermissionResult:
        """
        Check dataset-level permission.
        
        Args:
            user_id: User requesting access
            dataset_id: Dataset identifier
            action: Action to perform (read, write, delete, export)
            tenant_id: Tenant context
            db: Database session
            user_roles: Optional list of user's role IDs
            
        Returns:
            PermissionResult with decision and details
        """
        cache_key = f"dataset:{tenant_id}:{user_id}:{dataset_id}:{action}"
        
        # Check cache
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        # Check permissions
        result = await self._check_permission(
            user_id=user_id,
            resource_level=ResourceLevel.DATASET,
            resource_type="dataset",
            resource_id=dataset_id,
            action=action,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
        
        # Cache result
        self._set_cached(cache_key, result)
        
        return result
    
    async def check_record_permission(
        self,
        user_id: str,
        dataset_id: str,
        record_id: str,
        action: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> PermissionResult:
        """
        Check record-level permission (row-level security).
        
        First checks dataset permission, then record-specific permission.
        """
        # First check dataset permission
        dataset_result = await self.check_dataset_permission(
            user_id=user_id,
            dataset_id=dataset_id,
            action=action,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
        
        if not dataset_result.allowed and not dataset_result.requires_approval:
            return dataset_result
        
        cache_key = f"record:{tenant_id}:{user_id}:{dataset_id}:{record_id}:{action}"
        
        # Check cache
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        # Check record-specific permissions
        result = await self._check_permission(
            user_id=user_id,
            resource_level=ResourceLevel.RECORD,
            resource_type="record",
            resource_id=f"{dataset_id}:{record_id}",
            action=action,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles,
            parent_allowed=dataset_result.allowed
        )
        
        # Cache result
        self._set_cached(cache_key, result)
        
        return result
    
    async def check_field_permission(
        self,
        user_id: str,
        dataset_id: str,
        field_name: str,
        action: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> PermissionResult:
        """
        Check field-level permission (column-level security).
        
        First checks dataset permission, then field-specific permission.
        """
        # First check dataset permission
        dataset_result = await self.check_dataset_permission(
            user_id=user_id,
            dataset_id=dataset_id,
            action=action,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles
        )
        
        if not dataset_result.allowed and not dataset_result.requires_approval:
            return dataset_result
        
        cache_key = f"field:{tenant_id}:{user_id}:{dataset_id}:{field_name}:{action}"
        
        # Check cache
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        # Check field-specific permissions
        result = await self._check_permission(
            user_id=user_id,
            resource_level=ResourceLevel.FIELD,
            resource_type="field",
            resource_id=dataset_id,
            field_name=field_name,
            action=action,
            tenant_id=tenant_id,
            db=db,
            user_roles=user_roles,
            parent_allowed=dataset_result.allowed
        )
        
        # Cache result
        self._set_cached(cache_key, result)
        
        return result
    
    async def check_tag_based_permission(
        self,
        user_id: str,
        resource_tags: List[str],
        action: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None
    ) -> PermissionResult:
        """
        Check tag-based permission (ABAC).
        
        Checks if user has permission for resources with given tags.
        """
        if not resource_tags:
            return PermissionResult(allowed=True, reason="No tags to check")
        
        # Get user's tag-based permissions
        now = datetime.utcnow()
        
        query = db.query(DataPermissionModel).filter(
            and_(
                DataPermissionModel.tenant_id == tenant_id,
                DataPermissionModel.is_active == True,
                DataPermissionModel.action == action,
                or_(
                    DataPermissionModel.expires_at.is_(None),
                    DataPermissionModel.expires_at > now
                )
            )
        )
        
        # Filter by user or roles
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        role_conditions = [DataPermissionModel.user_id == user_uuid]
        
        if user_roles:
            role_uuids = [UUID(r) if isinstance(r, str) else r for r in user_roles]
            role_conditions.append(DataPermissionModel.role_id.in_(role_uuids))
        
        query = query.filter(or_(*role_conditions))
        
        permissions = query.all()
        
        # Check if any permission covers the resource tags
        for perm in permissions:
            if perm.tags:
                # Check if permission tags match resource tags
                if set(perm.tags).intersection(set(resource_tags)):
                    return PermissionResult(
                        allowed=True,
                        reason=f"Tag-based permission matched: {perm.tags}"
                    )
        
        return PermissionResult(
            allowed=False,
            reason=f"No tag-based permission for tags: {resource_tags}"
        )
    
    async def _check_permission(
        self,
        user_id: str,
        resource_level: ResourceLevel,
        resource_type: str,
        resource_id: str,
        action: str,
        tenant_id: str,
        db: Session,
        user_roles: Optional[List[str]] = None,
        field_name: Optional[str] = None,
        parent_allowed: bool = False
    ) -> PermissionResult:
        """Internal permission check logic."""
        now = datetime.utcnow()
        
        # Build query
        query = db.query(DataPermissionModel).filter(
            and_(
                DataPermissionModel.tenant_id == tenant_id,
                DataPermissionModel.resource_level == resource_level,
                DataPermissionModel.resource_type == resource_type,
                DataPermissionModel.is_active == True,
                or_(
                    DataPermissionModel.expires_at.is_(None),
                    DataPermissionModel.expires_at > now
                )
            )
        )
        
        # Resource ID matching (support wildcards)
        query = query.filter(
            or_(
                DataPermissionModel.resource_id == resource_id,
                DataPermissionModel.resource_id == "*"
            )
        )
        
        # Field name for field-level permissions
        if field_name:
            query = query.filter(
                or_(
                    DataPermissionModel.field_name == field_name,
                    DataPermissionModel.field_name == "*",
                    DataPermissionModel.field_name.is_(None)
                )
            )
        
        # Action matching
        try:
            action_enum = DataPermissionAction(action)
            query = query.filter(DataPermissionModel.action == action_enum)
        except ValueError:
            return PermissionResult(allowed=False, reason=f"Invalid action: {action}")
        
        # Filter by user or roles
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        role_conditions = [DataPermissionModel.user_id == user_uuid]
        
        if user_roles:
            role_uuids = [UUID(r) if isinstance(r, str) else r for r in user_roles]
            role_conditions.append(DataPermissionModel.role_id.in_(role_uuids))
        
        query = query.filter(or_(*role_conditions))
        
        permissions = query.all()
        
        if permissions:
            # Check conditions if any
            for perm in permissions:
                if perm.conditions:
                    # Evaluate conditions (simplified)
                    if not self._evaluate_conditions(perm.conditions):
                        continue
                
                return PermissionResult(
                    allowed=True,
                    reason="Permission granted",
                    conditions_applied=perm.conditions
                )
        
        # If parent allowed and no explicit deny, inherit
        if parent_allowed:
            return PermissionResult(
                allowed=True,
                reason="Inherited from parent resource"
            )
        
        # Check if approval is required
        classification = await self._get_resource_classification(
            dataset_id=resource_id.split(":")[0] if ":" in resource_id else resource_id,
            tenant_id=tenant_id,
            db=db
        )
        
        if classification and classification.sensitivity_level in [
            SensitivityLevel.CONFIDENTIAL,
            SensitivityLevel.TOP_SECRET
        ]:
            return PermissionResult(
                allowed=False,
                reason="Sensitive data requires approval",
                requires_approval=True
            )
        
        return PermissionResult(
            allowed=False,
            reason="No matching permission found"
        )
    
    def _evaluate_conditions(self, conditions: Dict[str, Any]) -> bool:
        """Evaluate permission conditions."""
        # Simplified condition evaluation
        # In production, this would be more sophisticated
        if not conditions:
            return True
        
        # Time-based conditions
        if "time_range" in conditions:
            time_range = conditions["time_range"]
            now = datetime.utcnow()
            
            if "start_hour" in time_range:
                if now.hour < time_range["start_hour"]:
                    return False
            
            if "end_hour" in time_range:
                if now.hour >= time_range["end_hour"]:
                    return False
        
        return True
    
    async def _get_resource_classification(
        self,
        dataset_id: str,
        tenant_id: str,
        db: Session
    ) -> Optional[DataClassificationModel]:
        """Get resource classification for sensitivity check."""
        return db.query(DataClassificationModel).filter(
            and_(
                DataClassificationModel.tenant_id == tenant_id,
                DataClassificationModel.dataset_id == dataset_id,
                DataClassificationModel.field_name.is_(None)  # Dataset-level classification
            )
        ).first()
    
    # ========================================================================
    # Permission Grant/Revoke
    # ========================================================================
    
    async def grant_permission(
        self,
        request: GrantPermissionRequest,
        tenant_id: str,
        granted_by: UUID,
        db: Session
    ) -> DataPermissionModel:
        """
        Grant a permission.
        
        Args:
            request: Grant permission request
            tenant_id: Tenant context
            granted_by: User granting the permission
            db: Database session
            
        Returns:
            Created DataPermissionModel
        """
        permission = DataPermissionModel(
            tenant_id=tenant_id,
            resource_level=request.resource_level,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            field_name=request.field_name,
            user_id=request.user_id,
            role_id=request.role_id,
            action=request.action,
            conditions=request.conditions,
            tags=request.tags,
            granted_by=granted_by,
            expires_at=request.expires_at,
            is_temporary=request.is_temporary
        )
        
        db.add(permission)
        db.commit()
        db.refresh(permission)
        
        # Invalidate cache
        self._invalidate_user_cache(
            str(request.user_id) if request.user_id else None,
            tenant_id
        )
        
        self.logger.info(
            f"Granted {request.action} permission on {request.resource_type}:{request.resource_id} "
            f"to user={request.user_id} role={request.role_id}"
        )
        
        return permission
    
    async def grant_temporary_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        expires_at: datetime,
        tenant_id: str,
        granted_by: UUID,
        db: Session
    ) -> TemporaryGrant:
        """
        Grant a temporary permission.
        
        Args:
            user_id: User to grant permission to
            resource: Resource identifier (format: type:id)
            action: Action to grant
            expires_at: Expiration time
            tenant_id: Tenant context
            granted_by: User granting the permission
            db: Database session
            
        Returns:
            TemporaryGrant with details
        """
        # Parse resource
        parts = resource.split(":", 1)
        resource_type = parts[0] if len(parts) > 1 else "dataset"
        resource_id = parts[1] if len(parts) > 1 else parts[0]
        
        # Determine resource level
        resource_level = ResourceLevel.DATASET
        if resource_type == "record":
            resource_level = ResourceLevel.RECORD
        elif resource_type == "field":
            resource_level = ResourceLevel.FIELD
        
        permission = DataPermissionModel(
            tenant_id=tenant_id,
            resource_level=resource_level,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=UUID(user_id),
            action=DataPermissionAction(action),
            granted_by=granted_by,
            expires_at=expires_at,
            is_temporary=True
        )
        
        db.add(permission)
        db.commit()
        db.refresh(permission)
        
        # Invalidate cache
        self._invalidate_user_cache(user_id, tenant_id)
        
        self.logger.info(
            f"Granted temporary {action} permission on {resource} to user {user_id}, "
            f"expires at {expires_at}"
        )
        
        return TemporaryGrant(
            permission_id=permission.id,
            user_id=UUID(user_id),
            resource=resource,
            action=action,
            granted_at=permission.granted_at,
            expires_at=expires_at
        )
    
    async def revoke_permission(
        self,
        user_id: Optional[str],
        role_id: Optional[str],
        resource_type: str,
        resource_id: str,
        action: str,
        tenant_id: str,
        db: Session,
        field_name: Optional[str] = None
    ) -> bool:
        """
        Revoke a permission.
        
        Args:
            user_id: User to revoke from (optional)
            role_id: Role to revoke from (optional)
            resource_type: Resource type
            resource_id: Resource identifier
            action: Action to revoke
            tenant_id: Tenant context
            db: Database session
            field_name: Field name for field-level permissions
            
        Returns:
            True if permission was revoked
        """
        query = db.query(DataPermissionModel).filter(
            and_(
                DataPermissionModel.tenant_id == tenant_id,
                DataPermissionModel.resource_type == resource_type,
                DataPermissionModel.resource_id == resource_id,
                DataPermissionModel.action == DataPermissionAction(action),
                DataPermissionModel.is_active == True
            )
        )
        
        if user_id:
            query = query.filter(DataPermissionModel.user_id == UUID(user_id))
        
        if role_id:
            query = query.filter(DataPermissionModel.role_id == UUID(role_id))
        
        if field_name:
            query = query.filter(DataPermissionModel.field_name == field_name)
        
        permissions = query.all()
        
        if not permissions:
            return False
        
        for perm in permissions:
            perm.is_active = False
            perm.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Invalidate cache
        self._invalidate_user_cache(user_id, tenant_id)
        
        self.logger.info(
            f"Revoked {action} permission on {resource_type}:{resource_id} "
            f"from user={user_id} role={role_id}"
        )
        
        return True
    
    # ========================================================================
    # Permission Queries
    # ========================================================================
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: str,
        db: Session,
        resource_type: Optional[str] = None,
        include_role_permissions: bool = True,
        user_roles: Optional[List[str]] = None
    ) -> List[DataPermissionModel]:
        """Get all permissions for a user."""
        now = datetime.utcnow()
        
        query = db.query(DataPermissionModel).filter(
            and_(
                DataPermissionModel.tenant_id == tenant_id,
                DataPermissionModel.is_active == True,
                or_(
                    DataPermissionModel.expires_at.is_(None),
                    DataPermissionModel.expires_at > now
                )
            )
        )
        
        if resource_type:
            query = query.filter(DataPermissionModel.resource_type == resource_type)
        
        # Filter by user or roles
        user_uuid = UUID(user_id)
        conditions = [DataPermissionModel.user_id == user_uuid]
        
        if include_role_permissions and user_roles:
            role_uuids = [UUID(r) if isinstance(r, str) else r for r in user_roles]
            conditions.append(DataPermissionModel.role_id.in_(role_uuids))
        
        query = query.filter(or_(*conditions))
        
        return query.all()
    
    async def get_resource_permissions(
        self,
        resource_type: str,
        resource_id: str,
        tenant_id: str,
        db: Session
    ) -> List[DataPermissionModel]:
        """Get all permissions for a resource."""
        now = datetime.utcnow()
        
        return db.query(DataPermissionModel).filter(
            and_(
                DataPermissionModel.tenant_id == tenant_id,
                DataPermissionModel.resource_type == resource_type,
                DataPermissionModel.resource_id == resource_id,
                DataPermissionModel.is_active == True,
                or_(
                    DataPermissionModel.expires_at.is_(None),
                    DataPermissionModel.expires_at > now
                )
            )
        ).all()
    
    # ========================================================================
    # Cache Management
    # ========================================================================
    
    def _get_cached(self, key: str) -> Optional[PermissionResult]:
        """Get cached permission result."""
        # Try Redis first
        if self._redis:
            try:
                cached = self._redis.get(f"data_perm:{key}")
                if cached:
                    data = json.loads(cached)
                    return PermissionResult(**data)
            except Exception as e:
                self.logger.warning(f"Redis cache get failed: {e}")
        
        # Fall back to local cache
        return self._local_cache.get(key)
    
    def _set_cached(self, key: str, result: PermissionResult) -> None:
        """Set cached permission result."""
        # Set in Redis
        if self._redis:
            try:
                self._redis.setex(
                    f"data_perm:{key}",
                    self._cache_ttl,
                    result.model_dump_json()
                )
            except Exception as e:
                self.logger.warning(f"Redis cache set failed: {e}")
        
        # Also set in local cache
        self._local_cache.set(key, result)
    
    def _invalidate_user_cache(self, user_id: Optional[str], tenant_id: str) -> None:
        """Invalidate cache for a user."""
        pattern = f"*:{tenant_id}:{user_id}:*" if user_id else f"*:{tenant_id}:*"
        
        # Invalidate Redis
        if self._redis:
            try:
                keys = self._redis.keys(f"data_perm:{pattern}")
                if keys:
                    self._redis.delete(*keys)
            except Exception as e:
                self.logger.warning(f"Redis cache invalidation failed: {e}")
        
        # Invalidate local cache
        self._local_cache.invalidate(pattern)
    
    def invalidate_all_cache(self) -> int:
        """Invalidate all cache entries."""
        count = self._local_cache.invalidate("*")
        
        if self._redis:
            try:
                keys = self._redis.keys("data_perm:*")
                if keys:
                    self._redis.delete(*keys)
                    count += len(keys)
            except Exception as e:
                self.logger.warning(f"Redis cache invalidation failed: {e}")
        
        return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self._local_cache.get_stats()
        stats["redis_available"] = self._redis is not None
        return stats


# Global instance
_data_permission_engine: Optional[DataPermissionEngine] = None


def get_data_permission_engine(redis_client=None) -> DataPermissionEngine:
    """Get or create the global data permission engine instance."""
    global _data_permission_engine
    if _data_permission_engine is None:
        _data_permission_engine = DataPermissionEngine(redis_client=redis_client)
    return _data_permission_engine
