"""
RBAC API Router for SuperInsight Platform.

Provides REST API endpoints for Role-Based Access Control management.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from src.security.rbac_engine import RBACEngine, Permission
from src.security.permission_manager import PermissionManager, AccessContext, AccessDecision


router = APIRouter(prefix="/api/v1/rbac", tags=["RBAC"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class PermissionSchema(BaseModel):
    """Permission schema."""
    resource: str = Field(..., description="Resource pattern (e.g., 'projects/*')")
    action: str = Field(..., description="Action (e.g., 'read', 'write', '*')")


class CreateRoleRequest(BaseModel):
    """Create role request."""
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: Optional[str] = Field(None, max_length=500, description="Role description")
    permissions: List[PermissionSchema] = Field(default_factory=list, description="Role permissions")
    parent_role_id: Optional[str] = Field(None, description="Parent role ID for inheritance")


class UpdateRoleRequest(BaseModel):
    """Update role request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Role name")
    description: Optional[str] = Field(None, max_length=500, description="Role description")
    permissions: Optional[List[PermissionSchema]] = Field(None, description="Role permissions")
    parent_role_id: Optional[str] = Field(None, description="Parent role ID")


class RoleResponse(BaseModel):
    """Role response."""
    id: str
    name: str
    description: Optional[str]
    permissions: List[PermissionSchema]
    parent_role_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


class AssignRoleRequest(BaseModel):
    """Assign role request."""
    role_id: str = Field(..., description="Role ID to assign")
    expires_at: Optional[datetime] = Field(None, description="Role assignment expiration")


class UserRoleResponse(BaseModel):
    """User role assignment response."""
    id: str
    user_id: str
    role_id: str
    role_name: str
    granted_by: Optional[str]
    granted_at: datetime
    expires_at: Optional[datetime]


class CheckPermissionRequest(BaseModel):
    """Check permission request."""
    user_id: str = Field(..., description="User ID to check")
    resource: str = Field(..., description="Resource to access")
    action: str = Field(..., description="Action to perform")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    attributes: Optional[dict] = Field(None, description="Additional context attributes")


class PermissionCheckResponse(BaseModel):
    """Permission check response."""
    allowed: bool
    reason: Optional[str]
    checked_at: datetime


class BulkPermissionCheckRequest(BaseModel):
    """Bulk permission check request."""
    user_id: str
    checks: List[dict]  # List of {resource, action} pairs


class BulkPermissionCheckResponse(BaseModel):
    """Bulk permission check response."""
    results: List[PermissionCheckResponse]


# ============================================================================
# Dependency Injection (placeholder - would be properly configured in app)
# ============================================================================

async def get_rbac_engine() -> RBACEngine:
    """Get RBAC engine instance."""
    # In production, this would be properly injected
    from src.database.connection import get_db_session
    from src.database.redis_client import get_redis_client
    
    db = await get_db_session()
    cache = await get_redis_client()
    return RBACEngine(db, cache)


async def get_permission_manager() -> PermissionManager:
    """Get permission manager instance."""
    from src.database.connection import get_db_session
    from src.database.redis_client import get_redis_client
    from src.security.audit_logger import AuditLogger
    
    db = await get_db_session()
    cache = await get_redis_client()
    rbac_engine = RBACEngine(db, cache)
    audit_logger = AuditLogger(db)
    return PermissionManager(db, rbac_engine, audit_logger)


# ============================================================================
# Role Management Endpoints
# ============================================================================

@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: CreateRoleRequest,
    rbac_engine: RBACEngine = Depends(get_rbac_engine)
):
    """
    Create a new role.
    
    Creates a role with the specified permissions. Optionally inherits
    permissions from a parent role.
    """
    try:
        # Convert permissions to Permission objects
        permissions = [
            Permission(resource=p.resource, action=p.action)
            for p in request.permissions
        ]
        
        role = await rbac_engine.create_role(
            name=request.name,
            description=request.description,
            permissions=permissions,
            parent_role_id=request.parent_role_id
        )
        
        return RoleResponse(
            id=str(role.id),
            name=role.name,
            description=role.description,
            permissions=[
                PermissionSchema(resource=p.resource, action=p.action)
                for p in role.permissions
            ],
            parent_role_id=str(role.parent_role_id) if role.parent_role_id else None,
            created_at=role.created_at,
            updated_at=role.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    skip: int = Query(0, ge=0, description="Number of roles to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum roles to return"),
    search: Optional[str] = Query(None, description="Search by role name"),
    rbac_engine: RBACEngine = Depends(get_rbac_engine)
):
    """
    List all roles.
    
    Returns a paginated list of roles with optional search filtering.
    """
    try:
        roles = await rbac_engine.list_roles(skip=skip, limit=limit, search=search)
        
        return [
            RoleResponse(
                id=str(role.id),
                name=role.name,
                description=role.description,
                permissions=[
                    PermissionSchema(resource=p.resource, action=p.action)
                    for p in role.permissions
                ],
                parent_role_id=str(role.parent_role_id) if role.parent_role_id else None,
                created_at=role.created_at,
                updated_at=role.updated_at
            )
            for role in roles
        ]
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    rbac_engine: RBACEngine = Depends(get_rbac_engine)
):
    """
    Get a specific role by ID.
    """
    try:
        role = await rbac_engine.get_role(role_id)
        
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        
        return RoleResponse(
            id=str(role.id),
            name=role.name,
            description=role.description,
            permissions=[
                PermissionSchema(resource=p.resource, action=p.action)
                for p in role.permissions
            ],
            parent_role_id=str(role.parent_role_id) if role.parent_role_id else None,
            created_at=role.created_at,
            updated_at=role.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    request: UpdateRoleRequest,
    rbac_engine: RBACEngine = Depends(get_rbac_engine)
):
    """
    Update an existing role.
    """
    try:
        # Convert permissions if provided
        permissions = None
        if request.permissions is not None:
            permissions = [
                Permission(resource=p.resource, action=p.action)
                for p in request.permissions
            ]
        
        role = await rbac_engine.update_role(
            role_id=role_id,
            name=request.name,
            description=request.description,
            permissions=permissions,
            parent_role_id=request.parent_role_id
        )
        
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        
        return RoleResponse(
            id=str(role.id),
            name=role.name,
            description=role.description,
            permissions=[
                PermissionSchema(resource=p.resource, action=p.action)
                for p in role.permissions
            ],
            parent_role_id=str(role.parent_role_id) if role.parent_role_id else None,
            created_at=role.created_at,
            updated_at=role.updated_at
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    rbac_engine: RBACEngine = Depends(get_rbac_engine)
):
    """
    Delete a role.
    
    Note: This will also remove all user assignments for this role.
    """
    try:
        success = await rbac_engine.delete_role(role_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# User Role Assignment Endpoints
# ============================================================================

@router.post("/users/{user_id}/roles", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED)
async def assign_role_to_user(
    user_id: str,
    request: AssignRoleRequest,
    rbac_engine: RBACEngine = Depends(get_rbac_engine)
):
    """
    Assign a role to a user.
    """
    try:
        assignment = await rbac_engine.assign_role(
            user_id=user_id,
            role_id=request.role_id,
            expires_at=request.expires_at
        )
        
        # Get role name for response
        role = await rbac_engine.get_role(request.role_id)
        role_name = role.name if role else "Unknown"
        
        return UserRoleResponse(
            id=str(assignment.id),
            user_id=user_id,
            role_id=request.role_id,
            role_name=role_name,
            granted_by=str(assignment.granted_by) if assignment.granted_by else None,
            granted_at=assignment.granted_at,
            expires_at=assignment.expires_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/users/{user_id}/roles", response_model=List[UserRoleResponse])
async def get_user_roles(
    user_id: str,
    rbac_engine: RBACEngine = Depends(get_rbac_engine)
):
    """
    Get all roles assigned to a user.
    """
    try:
        assignments = await rbac_engine.get_user_roles(user_id)
        
        responses = []
        for assignment in assignments:
            role = await rbac_engine.get_role(str(assignment.role_id))
            role_name = role.name if role else "Unknown"
            
            responses.append(UserRoleResponse(
                id=str(assignment.id),
                user_id=user_id,
                role_id=str(assignment.role_id),
                role_name=role_name,
                granted_by=str(assignment.granted_by) if assignment.granted_by else None,
                granted_at=assignment.granted_at,
                expires_at=assignment.expires_at
            ))
        
        return responses
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_role_from_user(
    user_id: str,
    role_id: str,
    rbac_engine: RBACEngine = Depends(get_rbac_engine)
):
    """
    Revoke a role from a user.
    """
    try:
        success = await rbac_engine.revoke_role(user_id=user_id, role_id=role_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role assignment not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Permission Check Endpoints
# ============================================================================

@router.post("/check", response_model=PermissionCheckResponse)
async def check_permission(
    request: CheckPermissionRequest,
    permission_manager: PermissionManager = Depends(get_permission_manager)
):
    """
    Check if a user has permission to perform an action on a resource.
    
    This endpoint checks both RBAC permissions and dynamic policies.
    """
    try:
        # Build access context
        context = None
        if request.ip_address or request.attributes:
            context = AccessContext(
                ip_address=request.ip_address or "0.0.0.0",
                attributes=request.attributes or {}
            )
        
        decision = await permission_manager.check_access(
            user_id=request.user_id,
            resource=request.resource,
            action=request.action,
            context=context
        )
        
        return PermissionCheckResponse(
            allowed=decision.allowed,
            reason=decision.reason,
            checked_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/check/bulk", response_model=BulkPermissionCheckResponse)
async def check_permissions_bulk(
    request: BulkPermissionCheckRequest,
    permission_manager: PermissionManager = Depends(get_permission_manager)
):
    """
    Check multiple permissions at once.
    """
    try:
        results = []
        
        for check in request.checks:
            decision = await permission_manager.check_access(
                user_id=request.user_id,
                resource=check.get("resource", ""),
                action=check.get("action", "")
            )
            
            results.append(PermissionCheckResponse(
                allowed=decision.allowed,
                reason=decision.reason,
                checked_at=datetime.utcnow()
            ))
        
        return BulkPermissionCheckResponse(results=results)
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    rbac_engine: RBACEngine = Depends(get_rbac_engine)
):
    """
    Get all effective permissions for a user.
    
    Returns all permissions from all assigned roles, including inherited permissions.
    """
    try:
        permissions = await rbac_engine.get_user_permissions(user_id)
        
        return {
            "user_id": user_id,
            "permissions": [
                {"resource": p.resource, "action": p.action}
                for p in permissions
            ],
            "total_count": len(permissions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))