"""
Workspace API for SuperInsight Platform.

Provides workspace management endpoints for multi-tenant support.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from src.database.connection import db_manager, get_db_session
from src.security.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])
security = HTTPBearer(auto_error=False)


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
) -> Optional[UserModel]:
    """Get current user from JWT token."""
    if not credentials:
        return None
    
    try:
        from src.security.controller import SecurityController
        controller = SecurityController()
        payload = controller.verify_token(credentials.credentials)
        if not payload:
            return None
        
        user = controller.get_user_by_id(payload["user_id"], db)
        return user
    except Exception as e:
        logger.warning(f"Failed to get user from token: {e}")
        return None


class WorkspaceResponse(BaseModel):
    """Workspace response model."""
    id: str
    name: str
    description: Optional[str] = None
    tenant_id: str
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WorkspaceMemberResponse(BaseModel):
    """Workspace member response model."""
    user_id: str
    username: str
    role: str
    joined_at: Optional[datetime] = None


@router.get("/my", response_model=List[WorkspaceResponse])
async def get_my_workspaces(
    current_user: Optional[UserModel] = Depends(get_current_user_from_token)
) -> List[WorkspaceResponse]:
    """
    Get workspaces for the current user.
    
    Returns workspaces that the user has access to based on their tenant.
    """
    try:
        tenant_id = current_user.tenant_id if current_user else "default_tenant"
        
        # For now, return a default workspace based on user's tenant
        default_workspace = WorkspaceResponse(
            id=f"ws_{tenant_id}",
            name=f"{tenant_id} Workspace",
            description="Default workspace",
            tenant_id=tenant_id,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return [default_workspace]
        
    except Exception as e:
        logger.error(f"Failed to get workspaces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_from_token)
) -> WorkspaceResponse:
    """Get workspace by ID."""
    try:
        tenant_id = current_user.tenant_id if current_user else "default_tenant"
        return WorkspaceResponse(
            id=workspace_id,
            name=f"Workspace {workspace_id}",
            description="Workspace details",
            tenant_id=tenant_id,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Failed to get workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def get_workspace_members(
    workspace_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_from_token)
) -> List[WorkspaceMemberResponse]:
    """Get members of a workspace."""
    try:
        if current_user:
            return [
                WorkspaceMemberResponse(
                    user_id=str(current_user.id),
                    username=current_user.username,
                    role=current_user.role.value,
                    joined_at=datetime.utcnow()
                )
            ]
        return []
    except Exception as e:
        logger.error(f"Failed to get workspace members: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch")
async def switch_workspace(
    workspace_id: str = Query(..., description="Workspace ID to switch to"),
    current_user: Optional[UserModel] = Depends(get_current_user_from_token)
) -> Dict[str, Any]:
    """Switch to a different workspace."""
    try:
        return {
            "success": True,
            "workspace_id": workspace_id,
            "message": f"Switched to workspace {workspace_id}"
        }
    except Exception as e:
        logger.error(f"Failed to switch workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))
