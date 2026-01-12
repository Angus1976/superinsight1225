"""
Admin Management API endpoints
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from src.database.connection import get_db
from src.security.auth import get_current_user
from src.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class Tenant(BaseModel):
    id: str
    name: str
    code: str
    description: str
    status: str = Field(..., description="Status: active, inactive, suspended")
    plan: str = Field(..., description="Plan: basic, professional, enterprise")
    user_count: int
    workspace_count: int
    storage_used: int
    storage_limit: int
    api_calls_used: int
    api_calls_limit: int
    created_at: str
    last_active_at: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)


class AdminUser(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    avatar: Optional[str] = None
    status: str = Field(..., description="Status: active, inactive, locked, pending")
    roles: List[str]
    tenant_id: str
    tenant_name: str
    last_login_at: Optional[str] = None
    created_at: str
    is_email_verified: bool
    login_count: int
    permissions: List[str] = Field(default_factory=list)


class SystemConfig(BaseModel):
    general: Dict[str, Any] = Field(default_factory=dict)
    database: Dict[str, Any] = Field(default_factory=dict)
    cache: Dict[str, Any] = Field(default_factory=dict)
    storage: Dict[str, Any] = Field(default_factory=dict)
    security: Dict[str, Any] = Field(default_factory=dict)
    email: Dict[str, Any] = Field(default_factory=dict)


class SystemStatus(BaseModel):
    database: Dict[str, Any] = Field(default_factory=dict)
    cache: Dict[str, Any] = Field(default_factory=dict)
    storage: Dict[str, Any] = Field(default_factory=dict)
    system: Dict[str, Any] = Field(default_factory=dict)


class CreateTenantRequest(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    plan: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    storage_limit: int
    api_calls_limit: int
    status: str = "active"


class CreateUserRequest(BaseModel):
    username: str
    email: str
    full_name: str
    tenant_id: str
    roles: List[str]
    password: Optional[str] = None
    status: str = "active"
    is_email_verified: bool = False


@router.get("/tenants", response_model=List[Tenant])
async def get_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all tenants"""
    # Mock data
    tenants = [
        {
            "id": "tenant1",
            "name": "示例企业",
            "code": "example_corp",
            "description": "示例企业租户",
            "status": "active",
            "plan": "enterprise",
            "user_count": 25,
            "workspace_count": 5,
            "storage_used": 5368709120,  # 5GB
            "storage_limit": 107374182400,  # 100GB
            "api_calls_used": 15000,
            "api_calls_limit": 100000,
            "created_at": "2025-01-15T10:00:00Z",
            "last_active_at": "2025-01-20T10:00:00Z",
            "settings": {
                "max_users": 50,
                "max_workspaces": 10,
                "features": ["advanced_analytics", "custom_models"]
            }
        },
        {
            "id": "tenant2",
            "name": "科技公司",
            "code": "tech_company",
            "description": "科技公司租户",
            "status": "active",
            "plan": "professional",
            "user_count": 12,
            "workspace_count": 3,
            "storage_used": 2147483648,  # 2GB
            "storage_limit": 53687091200,  # 50GB
            "api_calls_used": 8500,
            "api_calls_limit": 50000,
            "created_at": "2025-01-16T10:00:00Z",
            "last_active_at": "2025-01-20T09:30:00Z",
            "settings": {
                "max_users": 25,
                "max_workspaces": 5,
                "features": ["basic_analytics"]
            }
        }
    ]
    return tenants


@router.post("/tenants", response_model=Tenant)
async def create_tenant(
    request: CreateTenantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new tenant"""
    # Mock implementation
    tenant = {
        "id": f"tenant_{len(request.name)}",
        "name": request.name,
        "code": request.code,
        "description": request.description or "",
        "status": request.status,
        "plan": request.plan,
        "user_count": 0,
        "workspace_count": 0,
        "storage_used": 0,
        "storage_limit": request.storage_limit,
        "api_calls_used": 0,
        "api_calls_limit": request.api_calls_limit,
        "created_at": datetime.now().isoformat(),
        "settings": request.settings
    }
    return tenant


@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    request: CreateTenantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a tenant"""
    return {"message": f"Tenant {tenant_id} updated successfully"}


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a tenant"""
    return {"message": f"Tenant {tenant_id} deleted successfully"}


@router.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Suspend a tenant"""
    return {"message": f"Tenant {tenant_id} suspended"}


@router.post("/tenants/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate a tenant"""
    return {"message": f"Tenant {tenant_id} activated"}


@router.get("/tenants/list")
async def get_tenants_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get simplified tenant list"""
    # Mock data
    tenants = [
        {"id": "tenant1", "name": "示例企业"},
        {"id": "tenant2", "name": "科技公司"}
    ]
    return tenants


@router.get("/users", response_model=List[AdminUser])
async def get_users(
    tenant: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users"""
    # Mock data
    users = [
        {
            "id": "user1",
            "username": "admin",
            "email": "admin@example.com",
            "full_name": "系统管理员",
            "status": "active",
            "roles": ["admin"],
            "tenant_id": "tenant1",
            "tenant_name": "示例企业",
            "last_login_at": "2025-01-20T10:30:00Z",
            "created_at": "2025-01-15T10:00:00Z",
            "is_email_verified": True,
            "login_count": 45,
            "permissions": ["user:create", "user:read", "user:update", "user:delete"]
        },
        {
            "id": "user2",
            "username": "john.doe",
            "email": "john.doe@example.com",
            "full_name": "约翰·多伊",
            "status": "active",
            "roles": ["business_expert"],
            "tenant_id": "tenant1",
            "tenant_name": "示例企业",
            "last_login_at": "2025-01-20T09:45:00Z",
            "created_at": "2025-01-16T10:00:00Z",
            "is_email_verified": True,
            "login_count": 23,
            "permissions": ["task:read", "annotation:create", "annotation:update"]
        },
        {
            "id": "user3",
            "username": "jane.smith",
            "email": "jane.smith@example.com",
            "full_name": "简·史密斯",
            "status": "active",
            "roles": ["technical_expert"],
            "tenant_id": "tenant2",
            "tenant_name": "科技公司",
            "last_login_at": "2025-01-19T16:20:00Z",
            "created_at": "2025-01-17T10:00:00Z",
            "is_email_verified": True,
            "login_count": 18,
            "permissions": ["task:create", "task:read", "quality:review"]
        }
    ]
    return users


@router.post("/users", response_model=AdminUser)
async def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new user"""
    # Mock implementation
    user = {
        "id": f"user_{len(request.username)}",
        "username": request.username,
        "email": request.email,
        "full_name": request.full_name,
        "status": request.status,
        "roles": request.roles,
        "tenant_id": request.tenant_id,
        "tenant_name": "Mock Tenant",
        "created_at": datetime.now().isoformat(),
        "is_email_verified": request.is_email_verified,
        "login_count": 0,
        "permissions": []
    }
    return user


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a user"""
    return {"message": f"User {user_id} updated successfully"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a user"""
    return {"message": f"User {user_id} deleted successfully"}


@router.post("/users/{user_id}/lock")
async def lock_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lock a user"""
    return {"message": f"User {user_id} locked"}


@router.post("/users/{user_id}/unlock")
async def unlock_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Unlock a user"""
    return {"message": f"User {user_id} unlocked"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reset user password"""
    return {"message": f"Password reset email sent to user {user_id}"}


@router.get("/system/config", response_model=SystemConfig)
async def get_system_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get system configuration"""
    # Mock configuration
    config = {
        "general": {
            "site_name": "SuperInsight AI Platform",
            "site_description": "AI数据治理与标注平台",
            "admin_email": "admin@example.com",
            "timezone": "Asia/Shanghai",
            "language": "zh-CN",
            "maintenance_mode": False
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "superinsight",
            "max_connections": 100,
            "connection_timeout": 30,
            "query_timeout": 60
        },
        "cache": {
            "enabled": True,
            "type": "redis",
            "host": "localhost",
            "port": 6379,
            "ttl": 3600
        },
        "storage": {
            "type": "local",
            "path": "/data/uploads",
            "max_file_size": 104857600,  # 100MB
            "allowed_types": ["jpg", "png", "pdf", "csv", "json"]
        },
        "security": {
            "session_timeout": 30,
            "password_min_length": 8,
            "password_require_special_chars": True,
            "max_login_attempts": 5,
            "lockout_duration": 15
        },
        "email": {
            "enabled": True,
            "provider": "smtp",
            "host": "smtp.example.com",
            "port": 587,
            "username": "noreply@example.com",
            "encryption": "tls"
        }
    }
    return config


@router.put("/system/config")
async def update_system_config(
    config: SystemConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update system configuration"""
    return {"message": "System configuration updated successfully"}


@router.get("/system/status", response_model=SystemStatus)
async def get_system_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get system status"""
    # Mock status
    status = {
        "database": {
            "status": "healthy",
            "connections": 15,
            "max_connections": 100,
            "response_time": 25
        },
        "cache": {
            "status": "healthy",
            "memory_usage": 134217728,  # 128MB
            "hit_rate": 0.85
        },
        "storage": {
            "status": "healthy",
            "total_space": 1073741824000,  # 1TB
            "used_space": 107374182400,   # 100GB
            "free_space": 966367641600    # 900GB
        },
        "system": {
            "cpu_usage": 25.5,
            "memory_usage": 45.2,
            "disk_usage": 10.0,
            "uptime": 86400  # 1 day
        }
    }
    return status


@router.post("/system/test/{test_type}")
async def test_system_component(
    test_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test system component"""
    # Mock test results
    test_results = {
        "database": {"success": True, "message": "Database connection successful"},
        "cache": {"success": True, "message": "Cache connection successful"},
        "email": {"success": True, "message": "Email configuration valid"}
    }
    
    if test_type not in test_results:
        raise HTTPException(status_code=400, detail="Invalid test type")
    
    return test_results[test_type]