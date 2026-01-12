"""
Security Management API endpoints
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from src.database.connection import get_db
from src.security.auth import get_current_user
from src.models.user import User

router = APIRouter(prefix="/api/v1/security", tags=["security"])


class AuditLog(BaseModel):
    id: str
    timestamp: str
    user_id: str
    user_name: str
    action: str
    resource: str
    resource_id: str
    method: str
    endpoint: str
    ip_address: str
    user_agent: str
    status: str = Field(..., description="Status: success, failed, warning")
    details: Optional[Dict[str, Any]] = None
    risk_level: str = Field(..., description="Risk level: low, medium, high, critical")


class Permission(BaseModel):
    id: str
    name: str
    code: str
    description: str
    resource: str
    action: str
    enabled: bool
    created_at: str


class Role(BaseModel):
    id: str
    name: str
    code: str
    description: str
    permissions: List[str]
    user_count: int
    enabled: bool
    created_at: str


class UserPermission(BaseModel):
    user_id: str
    user_name: str
    email: str
    roles: List[str]
    direct_permissions: List[str]
    effective_permissions: List[str]
    last_login: Optional[str] = None


class CreatePermissionRequest(BaseModel):
    name: str
    code: str
    resource: str
    action: str
    description: Optional[str] = None
    enabled: bool = True


class CreateRoleRequest(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    enabled: bool = True


@router.get("/audit", response_model=Dict[str, Any])
async def get_audit_logs(
    start_date: str = Query(...),
    end_date: str = Query(...),
    action: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get security audit logs"""
    # Mock data
    logs = [
        {
            "id": "log1",
            "timestamp": "2025-01-20T10:30:00Z",
            "user_id": "user1",
            "user_name": "admin",
            "action": "login",
            "resource": "auth",
            "resource_id": "session1",
            "method": "POST",
            "endpoint": "/auth/login",
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "status": "success",
            "details": {"login_method": "password"},
            "risk_level": "low"
        },
        {
            "id": "log2",
            "timestamp": "2025-01-20T09:45:00Z",
            "user_id": "user2",
            "user_name": "john.doe",
            "action": "create",
            "resource": "task",
            "resource_id": "task123",
            "method": "POST",
            "endpoint": "/api/v1/tasks",
            "ip_address": "192.168.1.101",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "status": "success",
            "details": {"task_name": "Customer Review Classification"},
            "risk_level": "low"
        },
        {
            "id": "log3",
            "timestamp": "2025-01-20T08:15:00Z",
            "user_id": "unknown",
            "user_name": "unknown",
            "action": "login",
            "resource": "auth",
            "resource_id": "failed_session",
            "method": "POST",
            "endpoint": "/auth/login",
            "ip_address": "45.33.32.156",
            "user_agent": "curl/7.64.1",
            "status": "failed",
            "details": {"error": "Invalid credentials", "attempt": 3},
            "risk_level": "high"
        }
    ]
    
    return {
        "logs": logs,
        "total": len(logs)
    }


@router.get("/audit/export")
async def export_audit_logs(
    start_date: str = Query(...),
    end_date: str = Query(...),
    action: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export audit logs"""
    # Mock implementation
    return {"message": "Export functionality not implemented yet"}


@router.get("/permissions", response_model=List[Permission])
async def get_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all permissions"""
    # Mock data
    permissions = [
        {
            "id": "perm1",
            "name": "创建用户",
            "code": "user:create",
            "description": "创建新用户的权限",
            "resource": "user",
            "action": "create",
            "enabled": True,
            "created_at": "2025-01-15T10:00:00Z"
        },
        {
            "id": "perm2",
            "name": "查看任务",
            "code": "task:read",
            "description": "查看任务的权限",
            "resource": "task",
            "action": "read",
            "enabled": True,
            "created_at": "2025-01-15T10:00:00Z"
        },
        {
            "id": "perm3",
            "name": "删除标注",
            "code": "annotation:delete",
            "description": "删除标注的权限",
            "resource": "annotation",
            "action": "delete",
            "enabled": True,
            "created_at": "2025-01-15T10:00:00Z"
        }
    ]
    return permissions


@router.post("/permissions", response_model=Permission)
async def create_permission(
    request: CreatePermissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new permission"""
    # Mock implementation
    permission = {
        "id": f"perm_{len(request.name)}",
        "name": request.name,
        "code": request.code,
        "description": request.description or "",
        "resource": request.resource,
        "action": request.action,
        "enabled": request.enabled,
        "created_at": datetime.now().isoformat()
    }
    return permission


@router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a permission"""
    return {"message": f"Permission {permission_id} deleted successfully"}


@router.get("/roles", response_model=List[Role])
async def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all roles"""
    # Mock data
    roles = [
        {
            "id": "role1",
            "name": "管理员",
            "code": "admin",
            "description": "系统管理员角色",
            "permissions": ["user:create", "user:read", "user:update", "user:delete"],
            "user_count": 2,
            "enabled": True,
            "created_at": "2025-01-15T10:00:00Z"
        },
        {
            "id": "role2",
            "name": "标注员",
            "code": "annotator",
            "description": "数据标注员角色",
            "permissions": ["task:read", "annotation:create", "annotation:update"],
            "user_count": 15,
            "enabled": True,
            "created_at": "2025-01-15T10:00:00Z"
        },
        {
            "id": "role3",
            "name": "审核员",
            "code": "reviewer",
            "description": "质量审核员角色",
            "permissions": ["task:read", "annotation:read", "quality:review"],
            "user_count": 5,
            "enabled": True,
            "created_at": "2025-01-15T10:00:00Z"
        }
    ]
    return roles


@router.post("/roles", response_model=Role)
async def create_role(
    request: CreateRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new role"""
    # Mock implementation
    role = {
        "id": f"role_{len(request.name)}",
        "name": request.name,
        "code": request.code,
        "description": request.description or "",
        "permissions": request.permissions,
        "user_count": 0,
        "enabled": request.enabled,
        "created_at": datetime.now().isoformat()
    }
    return role


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a role"""
    return {"message": f"Role {role_id} deleted successfully"}


@router.get("/user-permissions", response_model=List[UserPermission])
async def get_user_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user permissions"""
    # Mock data
    user_permissions = [
        {
            "user_id": "user1",
            "user_name": "admin",
            "email": "admin@example.com",
            "roles": ["管理员"],
            "direct_permissions": [],
            "effective_permissions": ["user:create", "user:read", "user:update", "user:delete"],
            "last_login": "2025-01-20T10:30:00Z"
        },
        {
            "user_id": "user2",
            "user_name": "john.doe",
            "email": "john.doe@example.com",
            "roles": ["标注员"],
            "direct_permissions": ["quality:review"],
            "effective_permissions": ["task:read", "annotation:create", "annotation:update", "quality:review"],
            "last_login": "2025-01-20T09:45:00Z"
        }
    ]
    return user_permissions


@router.get("/permission-tree")
async def get_permission_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get permission tree for role configuration"""
    # Mock tree structure
    tree = [
        {
            "title": "用户管理",
            "key": "user",
            "children": [
                {"title": "创建用户", "key": "user:create"},
                {"title": "查看用户", "key": "user:read"},
                {"title": "更新用户", "key": "user:update"},
                {"title": "删除用户", "key": "user:delete"}
            ]
        },
        {
            "title": "任务管理",
            "key": "task",
            "children": [
                {"title": "创建任务", "key": "task:create"},
                {"title": "查看任务", "key": "task:read"},
                {"title": "更新任务", "key": "task:update"},
                {"title": "删除任务", "key": "task:delete"}
            ]
        },
        {
            "title": "标注管理",
            "key": "annotation",
            "children": [
                {"title": "创建标注", "key": "annotation:create"},
                {"title": "查看标注", "key": "annotation:read"},
                {"title": "更新标注", "key": "annotation:update"},
                {"title": "删除标注", "key": "annotation:delete"}
            ]
        }
    ]
    return tree