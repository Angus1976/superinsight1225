"""
Member Manager for Multi-Tenant Workspace module.

This module provides comprehensive member management including:
- Member invitation and addition
- Role management with hierarchy
- Permission revocation on member removal
- Custom role creation
- Batch operations
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.multi_tenant.workspace.models import (
    ExtendedWorkspaceModel,
    WorkspaceMemberModel,
    CustomRoleModel,
    InvitationModel,
    MemberRole,
    TenantAuditLogModel,
)
from src.multi_tenant.workspace.schemas import (
    MemberAddRequest,
    CustomRoleConfig,
    InvitationConfig,
    WorkspaceMemberResponse,
    InvitationResponse,
)

logger = logging.getLogger(__name__)


class MemberOperationError(Exception):
    """Exception raised for member operation errors."""
    pass


class MemberNotFoundError(MemberOperationError):
    """Exception raised when member is not found."""
    pass


class MemberAlreadyExistsError(MemberOperationError):
    """Exception raised when member already exists."""
    pass


class InvitationNotFoundError(MemberOperationError):
    """Exception raised when invitation is not found."""
    pass


class InvitationExpiredError(MemberOperationError):
    """Exception raised when invitation has expired."""
    pass


class RoleNotFoundError(MemberOperationError):
    """Exception raised when role is not found."""
    pass


class PermissionDeniedError(MemberOperationError):
    """Exception raised when permission is denied."""
    pass


# Role hierarchy: higher index = more permissions
ROLE_HIERARCHY = {
    MemberRole.GUEST: 0,
    MemberRole.MEMBER: 1,
    MemberRole.ADMIN: 2,
    MemberRole.OWNER: 3,
}


class MemberManager:
    """
    Member Manager for managing workspace members and roles.
    
    Provides methods for:
    - Inviting and adding members
    - Managing member roles
    - Creating custom roles
    - Batch member operations
    - Permission revocation on removal
    """
    
    def __init__(self, session: Session, permission_checker: Optional[Any] = None):
        """
        Initialize MemberManager.
        
        Args:
            session: SQLAlchemy database session
            permission_checker: Optional permission checker for access control
        """
        self.session = session
        self.permission_checker = permission_checker
    
    def invite_member(
        self,
        workspace_id: UUID,
        config: InvitationConfig,
        invited_by: UUID
    ) -> InvitationModel:
        """
        Invite a member to a workspace via email.
        
        Args:
            workspace_id: Workspace ID
            config: Invitation configuration
            invited_by: User ID of the inviter
            
        Returns:
            Created InvitationModel instance
        """
        # Verify workspace exists
        workspace = self._get_workspace_or_raise(workspace_id)
        
        # Check if invitation already exists
        existing = self.session.query(InvitationModel).filter(
            and_(
                InvitationModel.workspace_id == workspace_id,
                InvitationModel.email == config.email,
                InvitationModel.accepted_at.is_(None),
                InvitationModel.expires_at > datetime.utcnow()
            )
        ).first()
        
        if existing:
            # Return existing invitation
            return existing
        
        # Generate invitation token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=config.expires_in_days)
        
        invitation = InvitationModel(
            id=uuid4(),
            workspace_id=workspace_id,
            email=config.email,
            role=config.role,
            token=token,
            message=config.message,
            invited_by=invited_by,
            expires_at=expires_at,
        )
        
        self.session.add(invitation)
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="member_invited",
            resource_type="invitation",
            resource_id=str(invitation.id),
            details={
                "workspace_id": str(workspace_id),
                "email": config.email,
                "role": config.role.value,
            }
        )
        
        logger.info(f"Created invitation for {config.email} to workspace {workspace_id}")
        return invitation
    
    def accept_invitation(
        self,
        token: str,
        user_id: UUID
    ) -> WorkspaceMemberModel:
        """
        Accept an invitation and add user as member.
        
        Args:
            token: Invitation token
            user_id: User ID accepting the invitation
            
        Returns:
            Created WorkspaceMemberModel
            
        Raises:
            InvitationNotFoundError: If invitation not found
            InvitationExpiredError: If invitation has expired
        """
        invitation = self.session.query(InvitationModel).filter(
            InvitationModel.token == token
        ).first()
        
        if not invitation:
            raise InvitationNotFoundError("Invitation not found")
        
        if invitation.expires_at < datetime.utcnow():
            raise InvitationExpiredError("Invitation has expired")
        
        if invitation.accepted_at:
            raise MemberOperationError("Invitation already accepted")
        
        # Add member
        member = self.add_member(
            workspace_id=invitation.workspace_id,
            user_id=user_id,
            role=invitation.role
        )
        
        # Mark invitation as accepted
        invitation.accepted_at = datetime.utcnow()
        self.session.commit()
        
        return member
    
    def add_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: MemberRole = MemberRole.MEMBER,
        custom_role_id: Optional[UUID] = None
    ) -> WorkspaceMemberModel:
        """
        Add a member to a workspace.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID to add
            role: Role to assign
            custom_role_id: Optional custom role ID
            
        Returns:
            Created WorkspaceMemberModel
            
        Raises:
            MemberAlreadyExistsError: If member already exists
        """
        # Verify workspace exists
        workspace = self._get_workspace_or_raise(workspace_id)
        
        # Check if member already exists
        existing = self.session.query(WorkspaceMemberModel).filter(
            and_(
                WorkspaceMemberModel.workspace_id == workspace_id,
                WorkspaceMemberModel.user_id == user_id
            )
        ).first()
        
        if existing:
            raise MemberAlreadyExistsError(
                f"User {user_id} is already a member of workspace {workspace_id}"
            )
        
        # Verify custom role if specified
        if custom_role_id:
            custom_role = self.session.query(CustomRoleModel).filter(
                and_(
                    CustomRoleModel.id == custom_role_id,
                    CustomRoleModel.workspace_id == workspace_id
                )
            ).first()
            if not custom_role:
                raise RoleNotFoundError(f"Custom role {custom_role_id} not found")
        
        member = WorkspaceMemberModel(
            id=uuid4(),
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            custom_role_id=custom_role_id,
        )
        
        self.session.add(member)
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="member_added",
            resource_type="member",
            resource_id=str(member.id),
            details={
                "workspace_id": str(workspace_id),
                "user_id": str(user_id),
                "role": role.value,
            }
        )
        
        logger.info(f"Added member {user_id} to workspace {workspace_id} with role {role}")
        return member
    
    def remove_member(
        self,
        workspace_id: UUID,
        user_id: UUID
    ) -> None:
        """
        Remove a member from a workspace.
        
        This also revokes all permissions for the member.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID to remove
            
        Raises:
            MemberNotFoundError: If member not found
        """
        member = self.session.query(WorkspaceMemberModel).filter(
            and_(
                WorkspaceMemberModel.workspace_id == workspace_id,
                WorkspaceMemberModel.user_id == user_id
            )
        ).first()
        
        if not member:
            raise MemberNotFoundError(
                f"Member {user_id} not found in workspace {workspace_id}"
            )
        
        workspace = self._get_workspace_or_raise(workspace_id)
        
        # Revoke all permissions
        self._revoke_all_permissions(workspace_id, user_id)
        
        # Delete member
        self.session.delete(member)
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="member_removed",
            resource_type="member",
            resource_id=str(user_id),
            details={
                "workspace_id": str(workspace_id),
                "user_id": str(user_id),
            }
        )
        
        logger.info(f"Removed member {user_id} from workspace {workspace_id}")
    
    def update_role(
        self,
        workspace_id: UUID,
        user_id: UUID,
        new_role: MemberRole,
        custom_role_id: Optional[UUID] = None
    ) -> WorkspaceMemberModel:
        """
        Update a member's role.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID to update
            new_role: New role to assign
            custom_role_id: Optional custom role ID
            
        Returns:
            Updated WorkspaceMemberModel
            
        Raises:
            MemberNotFoundError: If member not found
        """
        member = self.session.query(WorkspaceMemberModel).filter(
            and_(
                WorkspaceMemberModel.workspace_id == workspace_id,
                WorkspaceMemberModel.user_id == user_id
            )
        ).first()
        
        if not member:
            raise MemberNotFoundError(
                f"Member {user_id} not found in workspace {workspace_id}"
            )
        
        workspace = self._get_workspace_or_raise(workspace_id)
        old_role = member.role
        
        # Verify custom role if specified
        if custom_role_id:
            custom_role = self.session.query(CustomRoleModel).filter(
                and_(
                    CustomRoleModel.id == custom_role_id,
                    CustomRoleModel.workspace_id == workspace_id
                )
            ).first()
            if not custom_role:
                raise RoleNotFoundError(f"Custom role {custom_role_id} not found")
        
        member.role = new_role
        member.custom_role_id = custom_role_id
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="member_role_updated",
            resource_type="member",
            resource_id=str(user_id),
            details={
                "workspace_id": str(workspace_id),
                "user_id": str(user_id),
                "old_role": old_role.value,
                "new_role": new_role.value,
            }
        )
        
        logger.info(f"Updated role for {user_id} in workspace {workspace_id}: {old_role} -> {new_role}")
        return member
    
    def create_custom_role(
        self,
        workspace_id: UUID,
        config: CustomRoleConfig
    ) -> CustomRoleModel:
        """
        Create a custom role for a workspace.
        
        Args:
            workspace_id: Workspace ID
            config: Custom role configuration
            
        Returns:
            Created CustomRoleModel
        """
        workspace = self._get_workspace_or_raise(workspace_id)
        
        # Check for duplicate name
        existing = self.session.query(CustomRoleModel).filter(
            and_(
                CustomRoleModel.workspace_id == workspace_id,
                CustomRoleModel.name == config.name
            )
        ).first()
        
        if existing:
            raise MemberOperationError(f"Custom role '{config.name}' already exists")
        
        custom_role = CustomRoleModel(
            id=uuid4(),
            workspace_id=workspace_id,
            name=config.name,
            description=config.description,
            permissions=config.permissions,
        )
        
        self.session.add(custom_role)
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="custom_role_created",
            resource_type="custom_role",
            resource_id=str(custom_role.id),
            details={
                "workspace_id": str(workspace_id),
                "name": config.name,
                "permissions": config.permissions,
            }
        )
        
        logger.info(f"Created custom role '{config.name}' in workspace {workspace_id}")
        return custom_role
    
    def delete_custom_role(self, role_id: UUID) -> None:
        """
        Delete a custom role.
        
        Args:
            role_id: Custom role ID to delete
            
        Raises:
            RoleNotFoundError: If role not found
        """
        role = self.session.query(CustomRoleModel).filter(
            CustomRoleModel.id == role_id
        ).first()
        
        if not role:
            raise RoleNotFoundError(f"Custom role {role_id} not found")
        
        workspace = self._get_workspace_or_raise(role.workspace_id)
        
        # Remove custom role from members
        self.session.query(WorkspaceMemberModel).filter(
            WorkspaceMemberModel.custom_role_id == role_id
        ).update({"custom_role_id": None})
        
        self.session.delete(role)
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="custom_role_deleted",
            resource_type="custom_role",
            resource_id=str(role_id),
            details={"name": role.name}
        )
        
        logger.info(f"Deleted custom role {role_id}")
    
    def batch_add_members(
        self,
        workspace_id: UUID,
        members: List[MemberAddRequest]
    ) -> List[WorkspaceMemberModel]:
        """
        Add multiple members to a workspace.
        
        Args:
            workspace_id: Workspace ID
            members: List of member add requests
            
        Returns:
            List of created WorkspaceMemberModel instances
        """
        workspace = self._get_workspace_or_raise(workspace_id)
        added_members = []
        
        for member_req in members:
            try:
                member = self.add_member(
                    workspace_id=workspace_id,
                    user_id=member_req.user_id,
                    role=member_req.role,
                    custom_role_id=member_req.custom_role_id
                )
                added_members.append(member)
            except MemberAlreadyExistsError:
                # Skip existing members
                logger.warning(f"Member {member_req.user_id} already exists, skipping")
                continue
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="members_batch_added",
            resource_type="member",
            resource_id=str(workspace_id),
            details={
                "workspace_id": str(workspace_id),
                "count": len(added_members),
            }
        )
        
        logger.info(f"Batch added {len(added_members)} members to workspace {workspace_id}")
        return added_members
    
    def batch_remove_members(
        self,
        workspace_id: UUID,
        user_ids: List[UUID]
    ) -> int:
        """
        Remove multiple members from a workspace.
        
        Args:
            workspace_id: Workspace ID
            user_ids: List of user IDs to remove
            
        Returns:
            Number of members removed
        """
        workspace = self._get_workspace_or_raise(workspace_id)
        removed_count = 0
        
        for user_id in user_ids:
            try:
                self.remove_member(workspace_id, user_id)
                removed_count += 1
            except MemberNotFoundError:
                # Skip non-existent members
                logger.warning(f"Member {user_id} not found, skipping")
                continue
        
        # Log audit
        self._log_audit(
            tenant_id=workspace.tenant_id,
            action="members_batch_removed",
            resource_type="member",
            resource_id=str(workspace_id),
            details={
                "workspace_id": str(workspace_id),
                "count": removed_count,
            }
        )
        
        logger.info(f"Batch removed {removed_count} members from workspace {workspace_id}")
        return removed_count
    
    def get_member(
        self,
        workspace_id: UUID,
        user_id: UUID
    ) -> Optional[WorkspaceMemberModel]:
        """
        Get a member by workspace and user ID.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID
            
        Returns:
            WorkspaceMemberModel if found, None otherwise
        """
        return self.session.query(WorkspaceMemberModel).filter(
            and_(
                WorkspaceMemberModel.workspace_id == workspace_id,
                WorkspaceMemberModel.user_id == user_id
            )
        ).first()
    
    def get_members(
        self,
        workspace_id: UUID,
        role: Optional[MemberRole] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[WorkspaceMemberModel]:
        """
        Get members of a workspace.
        
        Args:
            workspace_id: Workspace ID
            role: Optional role filter
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of WorkspaceMemberModel instances
        """
        query = self.session.query(WorkspaceMemberModel).filter(
            WorkspaceMemberModel.workspace_id == workspace_id
        )
        
        if role:
            query = query.filter(WorkspaceMemberModel.role == role)
        
        return query.offset(offset).limit(limit).all()
    
    def get_custom_roles(
        self,
        workspace_id: UUID
    ) -> List[CustomRoleModel]:
        """
        Get custom roles for a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            List of CustomRoleModel instances
        """
        return self.session.query(CustomRoleModel).filter(
            CustomRoleModel.workspace_id == workspace_id
        ).all()
    
    def has_permission(
        self,
        workspace_id: UUID,
        user_id: UUID,
        required_role: MemberRole
    ) -> bool:
        """
        Check if a user has at least the required role.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID
            required_role: Minimum required role
            
        Returns:
            True if user has sufficient permissions
        """
        member = self.get_member(workspace_id, user_id)
        if not member:
            return False
        
        user_level = ROLE_HIERARCHY.get(member.role, 0)
        required_level = ROLE_HIERARCHY.get(required_role, 0)
        
        return user_level >= required_level
    
    def _get_workspace_or_raise(self, workspace_id: UUID) -> ExtendedWorkspaceModel:
        """Get workspace or raise exception."""
        workspace = self.session.query(ExtendedWorkspaceModel).filter(
            ExtendedWorkspaceModel.id == workspace_id
        ).first()
        
        if not workspace:
            from src.multi_tenant.workspace.workspace_manager import WorkspaceNotFoundError
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} not found")
        
        return workspace
    
    def _revoke_all_permissions(self, workspace_id: UUID, user_id: UUID) -> None:
        """
        Revoke all permissions for a user in a workspace.
        
        This is called when a member is removed.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID
        """
        # If permission checker is available, use it
        if self.permission_checker:
            try:
                self.permission_checker.revoke_all_permissions(workspace_id, user_id)
            except Exception as e:
                logger.warning(f"Failed to revoke permissions via checker: {e}")
        
        # Log the revocation
        logger.info(f"Revoked all permissions for user {user_id} in workspace {workspace_id}")
    
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
