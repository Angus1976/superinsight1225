"""
Label Studio Workspace API for SuperInsight Platform.

Provides REST API endpoints for Label Studio Enterprise Workspace management:
- Workspace CRUD operations
- Member management
- Project association
- Permission-based access control

All endpoints require authentication and respect workspace-level permissions.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.models import UserModel
from src.label_studio.workspace_service import (
    WorkspaceService,
    WorkspaceNotFoundError,
    WorkspaceAlreadyExistsError,
    MemberNotFoundError,
    MemberAlreadyExistsError,
    CannotRemoveOwnerError,
    WorkspaceHasProjectsError,
    get_workspace_service,
)
from src.label_studio.rbac_service import (
    RBACService,
    Permission as RBACPermission,
    PermissionDeniedError,
    NotAMemberError,
    get_rbac_service,
)
from src.label_studio.workspace_models import (
    WorkspaceMemberRole,
    WorkspaceProjectModel,
)
from src.label_studio.metadata_codec import (
    encode_metadata,
    decode_metadata,
    has_metadata,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ls-workspaces", tags=["Label Studio Workspaces"])
security = HTTPBearer(auto_error=False)


# ============================================================================
# Authentication Dependency
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
) -> UserModel:
    """
    Get current authenticated user from JWT token.

    Raises:
        HTTPException 401: If not authenticated
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        from src.security.controller import SecurityController
        controller = SecurityController()
        payload = controller.verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

        user = controller.get_user_by_id(payload["user_id"], db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


# ============================================================================
# Pydantic Models - Request
# ============================================================================

class WorkspaceCreateRequest(BaseModel):
    """Request model for creating a workspace."""
    name: str = Field(..., min_length=1, max_length=255, description="Workspace name")
    description: Optional[str] = Field(None, max_length=2000, description="Workspace description")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Workspace settings")


class WorkspaceUpdateRequest(BaseModel):
    """Request model for updating a workspace."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class MemberAddRequest(BaseModel):
    """Request model for adding a member."""
    user_id: UUID = Field(..., description="User ID to add")
    role: str = Field(
        default="annotator",
        description="Member role: owner, admin, manager, reviewer, annotator"
    )


class MemberUpdateRequest(BaseModel):
    """Request model for updating member role."""
    role: str = Field(..., description="New role: owner, admin, manager, reviewer, annotator")


class ProjectAssociateRequest(BaseModel):
    """Request model for associating a project with workspace."""
    label_studio_project_id: str = Field(..., description="Label Studio project ID")
    superinsight_project_id: Optional[str] = Field(None, description="Optional SuperInsight project ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Pydantic Models - Response
# ============================================================================

class WorkspaceResponse(BaseModel):
    """Workspace response model."""
    id: str
    name: str
    description: Optional[str] = None
    owner_id: str
    settings: Dict[str, Any] = {}
    is_active: bool = True
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    member_count: int = 0
    project_count: int = 0

    class Config:
        from_attributes = True


class WorkspaceListResponse(BaseModel):
    """Workspace list response model."""
    items: List[WorkspaceResponse]
    total: int


class MemberResponse(BaseModel):
    """Member response model."""
    id: str
    workspace_id: str
    user_id: str
    role: str
    is_active: bool = True
    joined_at: Optional[datetime] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


class MemberListResponse(BaseModel):
    """Member list response model."""
    items: List[MemberResponse]
    total: int


class WorkspaceProjectResponse(BaseModel):
    """Workspace project association response model."""
    id: str
    workspace_id: str
    label_studio_project_id: str
    superinsight_project_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    project_title: Optional[str] = None
    project_description: Optional[str] = None

    class Config:
        from_attributes = True


class WorkspaceProjectListResponse(BaseModel):
    """Workspace project list response model."""
    items: List[WorkspaceProjectResponse]
    total: int


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_role(role_str: str) -> WorkspaceMemberRole:
    """Parse role string to WorkspaceMemberRole enum."""
    try:
        return WorkspaceMemberRole(role_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {role_str}. Valid roles: owner, admin, manager, reviewer, annotator"
        )


def _check_workspace_permission(
    rbac: RBACService,
    user_id: UUID,
    workspace_id: UUID,
    permission: RBACPermission,
) -> None:
    """Check if user has permission, raise 403 if not."""
    try:
        rbac.require_permission(user_id, workspace_id, permission)
    except NotAMemberError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace"
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission.value}"
        )


# ============================================================================
# Workspace CRUD Endpoints
# ============================================================================

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkspaceResponse:
    """
    Create a new Label Studio workspace.

    The current user becomes the owner of the workspace.
    """
    try:
        service = get_workspace_service(db)
        workspace = service.create_workspace(
            name=request.name,
            owner_id=current_user.id,
            description=request.description,
            settings=request.settings,
        )

        info = service.get_workspace_info(workspace.id)

        return WorkspaceResponse(
            id=str(workspace.id),
            name=workspace.name,
            description=workspace.description,
            owner_id=str(workspace.owner_id),
            settings=workspace.settings,
            is_active=workspace.is_active,
            is_deleted=workspace.is_deleted,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            member_count=info.member_count if info else 1,
            project_count=info.project_count if info else 0,
        )

    except WorkspaceAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workspace"
        )


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    include_inactive: bool = Query(False, description="Include inactive workspaces"),
) -> WorkspaceListResponse:
    """
    List all workspaces the current user has access to.
    """
    try:
        service = get_workspace_service(db)
        workspaces = service.list_user_workspaces(
            user_id=current_user.id,
            include_inactive=include_inactive,
        )

        items = []
        for ws in workspaces:
            info = service.get_workspace_info(ws.id)
            items.append(WorkspaceResponse(
                id=str(ws.id),
                name=ws.name,
                description=ws.description,
                owner_id=str(ws.owner_id),
                settings=ws.settings,
                is_active=ws.is_active,
                is_deleted=ws.is_deleted,
                created_at=ws.created_at,
                updated_at=ws.updated_at,
                member_count=info.member_count if info else 0,
                project_count=info.project_count if info else 0,
            ))

        return WorkspaceListResponse(items=items, total=len(items))

    except Exception as e:
        logger.error(f"Failed to list workspaces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workspaces"
        )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkspaceResponse:
    """
    Get workspace details by ID.

    Requires WORKSPACE_VIEW permission.
    """
    try:
        service = get_workspace_service(db)
        rbac = get_rbac_service(db)

        # Check permission
        _check_workspace_permission(rbac, current_user.id, workspace_id, RBACPermission.WORKSPACE_VIEW)

        workspace = service.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )

        info = service.get_workspace_info(workspace_id)

        return WorkspaceResponse(
            id=str(workspace.id),
            name=workspace.name,
            description=workspace.description,
            owner_id=str(workspace.owner_id),
            settings=workspace.settings,
            is_active=workspace.is_active,
            is_deleted=workspace.is_deleted,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            member_count=info.member_count if info else 0,
            project_count=info.project_count if info else 0,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace"
        )


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    request: WorkspaceUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkspaceResponse:
    """
    Update workspace details.

    Requires WORKSPACE_EDIT permission.
    """
    try:
        service = get_workspace_service(db)
        rbac = get_rbac_service(db)

        # Check permission
        _check_workspace_permission(rbac, current_user.id, workspace_id, RBACPermission.WORKSPACE_EDIT)

        # Build update data
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.settings is not None:
            update_data["settings"] = request.settings
        if request.is_active is not None:
            update_data["is_active"] = request.is_active

        workspace = service.update_workspace(workspace_id, update_data)
        info = service.get_workspace_info(workspace_id)

        return WorkspaceResponse(
            id=str(workspace.id),
            name=workspace.name,
            description=workspace.description,
            owner_id=str(workspace.owner_id),
            settings=workspace.settings,
            is_active=workspace.is_active,
            is_deleted=workspace.is_deleted,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            member_count=info.member_count if info else 0,
            project_count=info.project_count if info else 0,
        )

    except WorkspaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    except WorkspaceAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workspace"
        )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    hard_delete: bool = Query(False, description="Permanently delete workspace"),
) -> None:
    """
    Delete a workspace (soft delete by default).

    Requires WORKSPACE_DELETE permission (only Owner has this).
    """
    try:
        service = get_workspace_service(db)
        rbac = get_rbac_service(db)

        # Check permission - only owner can delete
        _check_workspace_permission(rbac, current_user.id, workspace_id, RBACPermission.WORKSPACE_DELETE)

        service.delete_workspace(workspace_id, hard_delete=hard_delete)

    except WorkspaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    except WorkspaceHasProjectsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workspace"
        )


# ============================================================================
# Member Management Endpoints
# ============================================================================

@router.post("/{workspace_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    workspace_id: UUID,
    request: MemberAddRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> MemberResponse:
    """
    Add a member to the workspace.

    Requires WORKSPACE_MANAGE_MEMBERS permission (Owner or Admin).
    """
    try:
        service = get_workspace_service(db)
        rbac = get_rbac_service(db)

        # Check permission
        _check_workspace_permission(rbac, current_user.id, workspace_id, RBACPermission.WORKSPACE_MANAGE_MEMBERS)

        # Check if current user can assign this role
        role = _parse_role(request.role)
        current_role = rbac._get_user_role(workspace_id, current_user.id)
        if not rbac.can_manage_role(current_role, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You cannot assign the {role.value} role"
            )

        member = service.add_member(workspace_id, request.user_id, role)

        return MemberResponse(
            id=str(member.id),
            workspace_id=str(member.workspace_id),
            user_id=str(member.user_id),
            role=member.role.value,
            is_active=member.is_active,
            joined_at=member.joined_at,
        )

    except MemberAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except WorkspaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add member"
        )


@router.get("/{workspace_id}/members", response_model=MemberListResponse)
async def list_members(
    workspace_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    include_inactive: bool = Query(False, description="Include inactive members"),
) -> MemberListResponse:
    """
    List all members of a workspace.

    Requires WORKSPACE_VIEW permission.
    """
    try:
        service = get_workspace_service(db)
        rbac = get_rbac_service(db)

        # Check permission
        _check_workspace_permission(rbac, current_user.id, workspace_id, RBACPermission.WORKSPACE_VIEW)

        members = service.list_members(workspace_id, include_inactive=include_inactive)

        items = [
            MemberResponse(
                id=str(m.id),
                workspace_id=str(m.workspace_id),
                user_id=str(m.user_id),
                role=m.role.value,
                is_active=m.is_active,
                joined_at=m.joined_at,
                user_email=m.user_email,
                user_name=m.user_name,
            )
            for m in members
        ]

        return MemberListResponse(items=items, total=len(items))

    except WorkspaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list members"
        )


@router.put("/{workspace_id}/members/{user_id}", response_model=MemberResponse)
async def update_member_role(
    workspace_id: UUID,
    user_id: UUID,
    request: MemberUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> MemberResponse:
    """
    Update a member's role.

    Requires WORKSPACE_MANAGE_MEMBERS permission.
    Only Owner can change Admin roles.
    """
    try:
        service = get_workspace_service(db)
        rbac = get_rbac_service(db)

        # Check permission
        _check_workspace_permission(rbac, current_user.id, workspace_id, RBACPermission.WORKSPACE_MANAGE_MEMBERS)

        # Check if current user can assign this role
        new_role = _parse_role(request.role)
        current_role = rbac._get_user_role(workspace_id, current_user.id)
        target_role = rbac._get_user_role(workspace_id, user_id)

        if not rbac.can_manage_role(current_role, target_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You cannot modify a {target_role.value}"
            )
        if not rbac.can_manage_role(current_role, new_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You cannot assign the {new_role.value} role"
            )

        member = service.update_member_role(workspace_id, user_id, new_role)

        return MemberResponse(
            id=str(member.id),
            workspace_id=str(member.workspace_id),
            user_id=str(member.user_id),
            role=member.role.value,
            is_active=member.is_active,
            joined_at=member.joined_at,
        )

    except MemberNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    except CannotRemoveOwnerError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update member role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role"
        )


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    """
    Remove a member from the workspace.

    Requires WORKSPACE_MANAGE_MEMBERS permission.
    Cannot remove the last owner.
    """
    try:
        service = get_workspace_service(db)
        rbac = get_rbac_service(db)

        # Check permission
        _check_workspace_permission(rbac, current_user.id, workspace_id, RBACPermission.WORKSPACE_MANAGE_MEMBERS)

        # Check if current user can remove this member
        current_role = rbac._get_user_role(workspace_id, current_user.id)
        target_role = rbac._get_user_role(workspace_id, user_id)

        if target_role and not rbac.can_manage_role(current_role, target_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You cannot remove a {target_role.value}"
            )

        service.remove_member(workspace_id, user_id)

    except MemberNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    except CannotRemoveOwnerError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )


# ============================================================================
# User Permissions Endpoint
# ============================================================================

@router.get("/{workspace_id}/permissions")
async def get_my_permissions(
    workspace_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Get current user's permissions in the workspace.
    """
    try:
        rbac = get_rbac_service(db)
        service = get_workspace_service(db)

        role = service.get_member_role(workspace_id, current_user.id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this workspace"
            )

        permissions = rbac.get_user_permissions_list(current_user.id, workspace_id)

        return {
            "workspace_id": str(workspace_id),
            "user_id": str(current_user.id),
            "role": role.value,
            "permissions": permissions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permissions"
        )


# ============================================================================
# Project Association Endpoints
# ============================================================================

@router.post("/{workspace_id}/projects", response_model=WorkspaceProjectResponse, status_code=status.HTTP_201_CREATED)
async def associate_project(
    workspace_id: UUID,
    request: ProjectAssociateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkspaceProjectResponse:
    """
    Associate a Label Studio project with a workspace.

    This creates a link between the workspace and the Label Studio project,
    allowing workspace-based filtering and permission management.

    Requires PROJECT_CREATE permission.
    """
    try:
        service = get_workspace_service(db)
        rbac = get_rbac_service(db)

        # Check permission
        _check_workspace_permission(rbac, current_user.id, workspace_id, RBACPermission.PROJECT_CREATE)

        # Check if workspace exists
        workspace = service.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )

        # Check if project is already associated with this workspace
        existing = db.query(WorkspaceProjectModel).filter(
            WorkspaceProjectModel.workspace_id == workspace_id,
            WorkspaceProjectModel.label_studio_project_id == request.label_studio_project_id,
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project is already associated with this workspace"
            )

        # Check if project is associated with another workspace
        existing_other = db.query(WorkspaceProjectModel).filter(
            WorkspaceProjectModel.label_studio_project_id == request.label_studio_project_id,
        ).first()

        if existing_other:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project is already associated with another workspace"
            )

        # Prepare metadata with workspace info
        metadata = request.metadata or {}
        metadata.update({
            "workspace_id": str(workspace_id),
            "workspace_name": workspace.name,
            "associated_by": str(current_user.id),
            "associated_at": datetime.utcnow().isoformat(),
        })

        # Create association
        from uuid import uuid4
        project_assoc = WorkspaceProjectModel(
            id=uuid4(),
            workspace_id=workspace_id,
            label_studio_project_id=request.label_studio_project_id,
            superinsight_project_id=UUID(request.superinsight_project_id) if request.superinsight_project_id else None,
            metadata=metadata,
        )

        db.add(project_assoc)
        db.commit()
        db.refresh(project_assoc)

        logger.info(
            f"Associated project {request.label_studio_project_id} with workspace {workspace_id}"
        )

        return WorkspaceProjectResponse(
            id=str(project_assoc.id),
            workspace_id=str(project_assoc.workspace_id),
            label_studio_project_id=project_assoc.label_studio_project_id,
            superinsight_project_id=str(project_assoc.superinsight_project_id) if project_assoc.superinsight_project_id else None,
            metadata=project_assoc.metadata,
            created_at=project_assoc.created_at,
            updated_at=project_assoc.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to associate project: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to associate project"
        )


@router.get("/{workspace_id}/projects", response_model=WorkspaceProjectListResponse)
async def list_workspace_projects(
    workspace_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkspaceProjectListResponse:
    """
    List all projects associated with a workspace.

    Requires PROJECT_VIEW permission.
    """
    try:
        service = get_workspace_service(db)
        rbac = get_rbac_service(db)

        # Check permission
        _check_workspace_permission(rbac, current_user.id, workspace_id, RBACPermission.PROJECT_VIEW)

        # Check if workspace exists
        workspace = service.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )

        # Get associated projects
        projects = db.query(WorkspaceProjectModel).filter(
            WorkspaceProjectModel.workspace_id == workspace_id
        ).all()

        items = []
        for proj in projects:
            items.append(WorkspaceProjectResponse(
                id=str(proj.id),
                workspace_id=str(proj.workspace_id),
                label_studio_project_id=proj.label_studio_project_id,
                superinsight_project_id=str(proj.superinsight_project_id) if proj.superinsight_project_id else None,
                metadata=proj.metadata or {},
                created_at=proj.created_at,
                updated_at=proj.updated_at,
            ))

        return WorkspaceProjectListResponse(items=items, total=len(items))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list workspace projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list workspace projects"
        )


@router.get("/{workspace_id}/projects/{project_id}", response_model=WorkspaceProjectResponse)
async def get_workspace_project(
    workspace_id: UUID,
    project_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> WorkspaceProjectResponse:
    """
    Get a specific project association.

    Requires PROJECT_VIEW permission.
    """
    try:
        rbac = get_rbac_service(db)

        # Check permission
        _check_workspace_permission(rbac, current_user.id, workspace_id, RBACPermission.PROJECT_VIEW)

        # Get project association
        project_assoc = db.query(WorkspaceProjectModel).filter(
            WorkspaceProjectModel.workspace_id == workspace_id,
            WorkspaceProjectModel.label_studio_project_id == project_id,
        ).first()

        if not project_assoc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found in workspace"
            )

        return WorkspaceProjectResponse(
            id=str(project_assoc.id),
            workspace_id=str(project_assoc.workspace_id),
            label_studio_project_id=project_assoc.label_studio_project_id,
            superinsight_project_id=str(project_assoc.superinsight_project_id) if project_assoc.superinsight_project_id else None,
            metadata=project_assoc.metadata or {},
            created_at=project_assoc.created_at,
            updated_at=project_assoc.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workspace project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workspace project"
        )


@router.delete("/{workspace_id}/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_association(
    workspace_id: UUID,
    project_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    """
    Remove a project association from the workspace.

    This removes the link between the workspace and the project,
    but does not delete the Label Studio project itself.

    Requires PROJECT_DELETE permission.
    """
    try:
        rbac = get_rbac_service(db)

        # Check permission
        _check_workspace_permission(rbac, current_user.id, workspace_id, RBACPermission.PROJECT_DELETE)

        # Get project association
        project_assoc = db.query(WorkspaceProjectModel).filter(
            WorkspaceProjectModel.workspace_id == workspace_id,
            WorkspaceProjectModel.label_studio_project_id == project_id,
        ).first()

        if not project_assoc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found in workspace"
            )

        # Delete association
        db.delete(project_assoc)
        db.commit()

        logger.info(
            f"Removed project {project_id} association from workspace {workspace_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove project association: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove project association"
        )
