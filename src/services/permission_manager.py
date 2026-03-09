"""
Permission Manager Service

Manages permissions and access control for data lifecycle resources.
Supports role-based access control (RBAC) and permission expiration.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models.data_lifecycle import (
    PermissionModel,
    Permission,
    ResourceType,
    Action,
    AuditLogModel,
    OperationType,
    OperationResult
)


class Resource:
    """Resource identifier for permission checks"""
    def __init__(self, type: ResourceType, id: str):
        self.type = type
        self.id = id


class PermissionManager:
    """
    Manages permissions and access control for data lifecycle resources.
    
    Responsibilities:
    - Check user permissions before operations
    - Grant and revoke permissions
    - Support role-based access control (RBAC)
    - Handle permission expiration
    - Track permission grants in audit log
    """
    
    # Predefined roles with their default permissions
    ROLE_PERMISSIONS: Dict[str, Dict[ResourceType, List[Action]]] = {
        'admin': {
            ResourceType.TEMP_DATA: [Action.VIEW, Action.EDIT, Action.DELETE, Action.REVIEW, Action.TRANSFER],
            ResourceType.SAMPLE: [Action.VIEW, Action.EDIT, Action.DELETE, Action.TRANSFER],
            ResourceType.ANNOTATION_TASK: [Action.VIEW, Action.EDIT, Action.DELETE, Action.ANNOTATE],
            ResourceType.ANNOTATED_DATA: [Action.VIEW, Action.EDIT, Action.DELETE, Action.ENHANCE],
            ResourceType.ENHANCED_DATA: [Action.VIEW, Action.EDIT, Action.DELETE, Action.TRANSFER],
            ResourceType.TRIAL: [Action.VIEW, Action.EDIT, Action.DELETE, Action.TRIAL],
        },
        'reviewer': {
            ResourceType.TEMP_DATA: [Action.VIEW, Action.REVIEW],
            ResourceType.SAMPLE: [Action.VIEW],
            ResourceType.ANNOTATION_TASK: [Action.VIEW],
            ResourceType.ANNOTATED_DATA: [Action.VIEW],
            ResourceType.ENHANCED_DATA: [Action.VIEW],
            ResourceType.TRIAL: [Action.VIEW],
        },
        'annotator': {
            ResourceType.TEMP_DATA: [Action.VIEW],
            ResourceType.SAMPLE: [Action.VIEW],
            ResourceType.ANNOTATION_TASK: [Action.VIEW, Action.ANNOTATE],
            ResourceType.ANNOTATED_DATA: [Action.VIEW],
            ResourceType.ENHANCED_DATA: [Action.VIEW],
            ResourceType.TRIAL: [Action.VIEW],
        },
        'viewer': {
            ResourceType.TEMP_DATA: [Action.VIEW],
            ResourceType.SAMPLE: [Action.VIEW],
            ResourceType.ANNOTATION_TASK: [Action.VIEW],
            ResourceType.ANNOTATED_DATA: [Action.VIEW],
            ResourceType.ENHANCED_DATA: [Action.VIEW],
            ResourceType.TRIAL: [Action.VIEW],
        },
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_permission(
        self,
        user_id: str,
        resource: Resource,
        action: Action,
        user_roles: Optional[List[str]] = None
    ) -> bool:
        """
        Check if a user has permission to perform an action on a resource.
        
        Args:
            user_id: User ID to check
            resource: Resource to check permission for
            action: Action to perform
            user_roles: Optional list of user roles for RBAC
        
        Returns:
            True if user has permission, False otherwise
        """
        # Check role-based permissions first
        if user_roles:
            for role in user_roles:
                if self._check_role_permission(role, resource.type, action):
                    return True
        
        # Check explicit permissions
        now = datetime.utcnow()
        permission = self.db.query(PermissionModel).filter(
            and_(
                PermissionModel.user_id == user_id,
                PermissionModel.resource_type == resource.type,
                PermissionModel.resource_id == resource.id,
                or_(
                    PermissionModel.expires_at.is_(None),
                    PermissionModel.expires_at > now
                )
            )
        ).first()
        
        if permission:
            # Check if action is in the granted actions
            actions = [Action(a) for a in permission.actions]
            return action in actions
        
        return False
    
    def grant_permission(
        self,
        user_id: str,
        resource: Resource,
        actions: List[Action],
        granted_by: str,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Permission:
        """
        Grant permissions to a user for a specific resource.
        
        Args:
            user_id: User ID to grant permission to
            resource: Resource to grant permission for
            actions: List of actions to grant
            granted_by: User ID who is granting the permission
            expires_at: Optional expiration date
            metadata: Optional metadata
        
        Returns:
            Created Permission object
        """
        # Check if permission already exists
        existing = self.db.query(PermissionModel).filter(
            and_(
                PermissionModel.user_id == user_id,
                PermissionModel.resource_type == resource.type,
                PermissionModel.resource_id == resource.id
            )
        ).first()
        
        if existing:
            # Update existing permission
            existing.actions = [a.value for a in actions]
            existing.granted_by = granted_by
            existing.granted_at = datetime.utcnow()
            existing.expires_at = expires_at
            existing.metadata_ = metadata or {}
            permission_model = existing
        else:
            # Create new permission
            permission_model = PermissionModel(
                user_id=user_id,
                resource_type=resource.type,
                resource_id=resource.id,
                actions=[a.value for a in actions],
                granted_by=granted_by,
                granted_at=datetime.utcnow(),
                expires_at=expires_at,
                metadata_=metadata or {}
            )
            self.db.add(permission_model)
        
        # Record in audit log
        self._log_permission_change(
            operation_type=OperationType.CREATE if not existing else OperationType.UPDATE,
            user_id=granted_by,
            resource=resource,
            action=Action.EDIT,
            details={
                'target_user_id': user_id,
                'actions': [a.value for a in actions],
                'expires_at': expires_at.isoformat() if expires_at else None,
                'metadata': metadata
            }
        )
        
        self.db.commit()
        self.db.refresh(permission_model)
        
        return Permission(
            id=permission_model.id,
            user_id=permission_model.user_id,
            resource_type=permission_model.resource_type,
            resource_id=permission_model.resource_id,
            actions=[Action(a) for a in permission_model.actions],
            granted_by=permission_model.granted_by,
            granted_at=permission_model.granted_at,
            expires_at=permission_model.expires_at,
            metadata=permission_model.metadata_
        )
    
    def revoke_permission(
        self,
        user_id: str,
        resource: Resource,
        actions: Optional[List[Action]] = None,
        revoked_by: Optional[str] = None
    ) -> bool:
        """
        Revoke permissions from a user for a specific resource.
        
        Args:
            user_id: User ID to revoke permission from
            resource: Resource to revoke permission for
            actions: Optional list of specific actions to revoke (if None, revoke all)
            revoked_by: User ID who is revoking the permission
        
        Returns:
            True if permission was revoked, False if not found
        """
        permission = self.db.query(PermissionModel).filter(
            and_(
                PermissionModel.user_id == user_id,
                PermissionModel.resource_type == resource.type,
                PermissionModel.resource_id == resource.id
            )
        ).first()
        
        if not permission:
            return False
        
        if actions is None:
            # Revoke all permissions - delete the record
            self.db.delete(permission)
            revoked_actions = permission.actions
        else:
            # Revoke specific actions
            current_actions = [Action(a) for a in permission.actions]
            remaining_actions = [a for a in current_actions if a not in actions]
            
            if not remaining_actions:
                # No actions left, delete the record
                self.db.delete(permission)
                revoked_actions = permission.actions
            else:
                # Update with remaining actions
                permission.actions = [a.value for a in remaining_actions]
                revoked_actions = [a.value for a in actions]
        
        # Record in audit log
        if revoked_by:
            self._log_permission_change(
                operation_type=OperationType.DELETE,
                user_id=revoked_by,
                resource=resource,
                action=Action.EDIT,
                details={
                    'target_user_id': user_id,
                    'revoked_actions': revoked_actions
                }
            )
        
        self.db.commit()
        return True
    
    def get_user_permissions(
        self,
        user_id: str,
        include_expired: bool = False
    ) -> List[Permission]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User ID to get permissions for
            include_expired: Whether to include expired permissions
        
        Returns:
            List of Permission objects
        """
        query = self.db.query(PermissionModel).filter(
            PermissionModel.user_id == user_id
        )
        
        if not include_expired:
            now = datetime.utcnow()
            query = query.filter(
                or_(
                    PermissionModel.expires_at.is_(None),
                    PermissionModel.expires_at > now
                )
            )
        
        permissions = query.all()
        
        return [
            Permission(
                id=p.id,
                user_id=p.user_id,
                resource_type=p.resource_type,
                resource_id=p.resource_id,
                actions=[Action(a) for a in p.actions],
                granted_by=p.granted_by,
                granted_at=p.granted_at,
                expires_at=p.expires_at,
                metadata=p.metadata_
            )
            for p in permissions
        ]
    
    def get_resource_permissions(
        self,
        resource: Resource,
        include_expired: bool = False
    ) -> List[Permission]:
        """
        Get all permissions for a specific resource.
        
        Args:
            resource: Resource to get permissions for
            include_expired: Whether to include expired permissions
        
        Returns:
            List of Permission objects
        """
        query = self.db.query(PermissionModel).filter(
            and_(
                PermissionModel.resource_type == resource.type,
                PermissionModel.resource_id == resource.id
            )
        )
        
        if not include_expired:
            now = datetime.utcnow()
            query = query.filter(
                or_(
                    PermissionModel.expires_at.is_(None),
                    PermissionModel.expires_at > now
                )
            )
        
        permissions = query.all()
        
        return [
            Permission(
                id=p.id,
                user_id=p.user_id,
                resource_type=p.resource_type,
                resource_id=p.resource_id,
                actions=[Action(a) for a in p.actions],
                granted_by=p.granted_by,
                granted_at=p.granted_at,
                expires_at=p.expires_at,
                metadata=p.metadata_
            )
            for p in permissions
        ]
    
    def cleanup_expired_permissions(self) -> int:
        """
        Remove expired permissions from the database.
        
        Returns:
            Number of permissions removed
        """
        now = datetime.utcnow()
        expired = self.db.query(PermissionModel).filter(
            and_(
                PermissionModel.expires_at.isnot(None),
                PermissionModel.expires_at <= now
            )
        ).all()
        
        count = len(expired)
        for permission in expired:
            self.db.delete(permission)
        
        self.db.commit()
        return count
    
    def _check_role_permission(
        self,
        role: str,
        resource_type: ResourceType,
        action: Action
    ) -> bool:
        """Check if a role has permission for an action on a resource type"""
        role_perms = self.ROLE_PERMISSIONS.get(role, {})
        allowed_actions = role_perms.get(resource_type, [])
        return action in allowed_actions
    
    def _log_permission_change(
        self,
        operation_type: OperationType,
        user_id: str,
        resource: Resource,
        action: Action,
        details: Dict[str, Any]
    ):
        """Log permission change to audit log"""
        audit_log = AuditLogModel(
            operation_type=operation_type,
            user_id=user_id,
            resource_type=resource.type,
            resource_id=resource.id,
            action=action,
            result=OperationResult.SUCCESS,
            duration=0,
            details=details,
            timestamp=datetime.utcnow()
        )
        self.db.add(audit_log)
