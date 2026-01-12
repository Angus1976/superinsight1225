"""
Multi-tenant API middleware for tenant context extraction and validation.

This module provides FastAPI middleware for handling multi-tenant requests,
extracting tenant and workspace context, and enforcing permissions.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.database.rls_policies import set_tenant_context, clear_tenant_context
from src.multi_tenant.services import PermissionService, TenantManager, WorkspaceManager
from src.security.jwt_handler import decode_jwt_token

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware for extracting and validating tenant context from requests.
    
    This middleware:
    1. Extracts tenant and workspace context from request headers, subdomain, or JWT
    2. Validates user permissions for the requested tenant/workspace
    3. Sets database session context for RLS policies
    4. Adds context information to request state
    """
    
    def __init__(self, app, bypass_paths: Optional[list] = None):
        super().__init__(app)
        self.bypass_paths = bypass_paths or [
            "/docs", "/redoc", "/openapi.json", "/health",
            "/auth/login", "/auth/register", "/auth/refresh"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and add tenant context."""
        
        # Skip middleware for bypass paths
        if any(request.url.path.startswith(path) for path in self.bypass_paths):
            return await call_next(request)
        
        try:
            # Get database session
            session = next(get_db_session())
            
            # Extract tenant and workspace context
            tenant_id, workspace_id, user_id = await self._extract_context(request, session)
            
            # Validate permissions if context is available
            if tenant_id and user_id:
                await self._validate_permissions(user_id, tenant_id, workspace_id, session)
            
            # Set database context for RLS
            if tenant_id:
                set_tenant_context(
                    session, 
                    tenant_id, 
                    workspace_id=str(workspace_id) if workspace_id else None
                )
            
            # Add context to request state
            request.state.tenant_id = tenant_id
            request.state.workspace_id = workspace_id
            request.state.user_id = user_id
            request.state.db_session = session
            
            # Process the request
            response = await call_next(request)
            
            # Clean up database context
            if tenant_id:
                clear_tenant_context(session)
            
            session.close()
            return response
            
        except HTTPException:
            session.close()
            raise
        except Exception as e:
            session.close()
            logger.error(f"Tenant context middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error in tenant context processing"}
            )
    
    async def _extract_context(
        self, 
        request: Request, 
        session: Session
    ) -> Tuple[Optional[str], Optional[UUID], Optional[UUID]]:
        """
        Extract tenant ID, workspace ID, and user ID from request.
        
        Priority order:
        1. X-Tenant-ID and X-Workspace-ID headers
        2. Subdomain extraction
        3. JWT token claims
        4. Default tenant for authenticated user
        
        Returns:
            Tuple of (tenant_id, workspace_id, user_id)
        """
        tenant_id = None
        workspace_id = None
        user_id = None
        
        # Extract user ID from JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = decode_jwt_token(token)
                user_id = UUID(payload.get("sub"))
            except Exception as e:
                logger.warning(f"Invalid JWT token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token"
                )
        
        # Method 1: Extract from headers
        tenant_id = request.headers.get("X-Tenant-ID")
        workspace_id_str = request.headers.get("X-Workspace-ID")
        if workspace_id_str:
            try:
                workspace_id = UUID(workspace_id_str)
            except ValueError:
                logger.warning(f"Invalid workspace ID format: {workspace_id_str}")
        
        # Method 2: Extract from subdomain
        if not tenant_id:
            host = request.headers.get("Host", "")
            if "." in host:
                subdomain = host.split(".")[0]
                if subdomain and subdomain != "www" and subdomain != "api":
                    tenant_id = subdomain
        
        # Method 3: Extract from JWT claims
        if not tenant_id and auth_header:
            try:
                payload = decode_jwt_token(token)
                tenant_id = payload.get("tenant_id")
                workspace_id_str = payload.get("workspace_id")
                if workspace_id_str:
                    workspace_id = UUID(workspace_id_str)
            except Exception:
                pass  # Already handled above
        
        # Method 4: Use default tenant for user
        if not tenant_id and user_id:
            permission_service = PermissionService(session)
            user_context = permission_service.get_user_context(user_id)
            tenant_id = user_context.get("default_tenant")
        
        return tenant_id, workspace_id, user_id
    
    async def _validate_permissions(
        self,
        user_id: UUID,
        tenant_id: str,
        workspace_id: Optional[UUID],
        session: Session
    ) -> None:
        """
        Validate user permissions for the requested tenant and workspace.
        
        Args:
            user_id: User ID from JWT token
            tenant_id: Requested tenant ID
            workspace_id: Requested workspace ID (optional)
            session: Database session
            
        Raises:
            HTTPException: If user doesn't have permission
        """
        permission_service = PermissionService(session)
        
        # Check tenant permission
        if not permission_service.has_tenant_permission(user_id, tenant_id):
            logger.warning(f"User {user_id} denied access to tenant {tenant_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to tenant: {tenant_id}"
            )
        
        # Check workspace permission if specified
        if workspace_id:
            if not permission_service.can_access_workspace(user_id, workspace_id):
                logger.warning(f"User {user_id} denied access to workspace {workspace_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied to workspace: {workspace_id}"
                )


class TenantAwareSession:
    """
    Database session wrapper that automatically applies tenant context.
    
    This class wraps SQLAlchemy sessions to automatically set tenant context
    for RLS policies and provide tenant-aware query methods.
    """
    
    def __init__(self, session: Session, tenant_id: str, workspace_id: Optional[UUID] = None):
        self.session = session
        self.tenant_id = tenant_id
        self.workspace_id = workspace_id
        self._context_set = False
    
    def __enter__(self):
        """Set tenant context when entering context manager."""
        self.set_context()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clear tenant context when exiting context manager."""
        self.clear_context()
    
    def set_context(self):
        """Set the tenant context for this session."""
        if not self._context_set:
            set_tenant_context(
                self.session,
                self.tenant_id,
                workspace_id=str(self.workspace_id) if self.workspace_id else None
            )
            self._context_set = True
    
    def clear_context(self):
        """Clear the tenant context for this session."""
        if self._context_set:
            clear_tenant_context(self.session)
            self._context_set = False
    
    def query(self, *args, **kwargs):
        """Proxy query method with automatic context setting."""
        self.set_context()
        return self.session.query(*args, **kwargs)
    
    def add(self, *args, **kwargs):
        """Proxy add method."""
        return self.session.add(*args, **kwargs)
    
    def commit(self, *args, **kwargs):
        """Proxy commit method."""
        return self.session.commit(*args, **kwargs)
    
    def rollback(self, *args, **kwargs):
        """Proxy rollback method."""
        return self.session.rollback(*args, **kwargs)
    
    def close(self, *args, **kwargs):
        """Proxy close method with context cleanup."""
        self.clear_context()
        return self.session.close(*args, **kwargs)


def get_tenant_context(request: Request) -> Dict[str, Any]:
    """
    Get tenant context from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary with tenant context information
    """
    return {
        "tenant_id": getattr(request.state, "tenant_id", None),
        "workspace_id": getattr(request.state, "workspace_id", None),
        "user_id": getattr(request.state, "user_id", None)
    }


def get_tenant_aware_session(request: Request) -> TenantAwareSession:
    """
    Get a tenant-aware database session from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        TenantAwareSession instance
    """
    session = getattr(request.state, "db_session", None)
    if not session:
        session = next(get_db_session())
    
    tenant_id = getattr(request.state, "tenant_id", None)
    workspace_id = getattr(request.state, "workspace_id", None)
    
    return TenantAwareSession(session, tenant_id, workspace_id)


def require_tenant_permission(required_role: str = "member"):
    """
    Decorator to require specific tenant permission for an endpoint.
    
    Args:
        required_role: Minimum required tenant role
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            context = get_tenant_context(request)
            user_id = context.get("user_id")
            tenant_id = context.get("tenant_id")
            
            if not user_id or not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            session = getattr(request.state, "db_session")
            permission_service = PermissionService(session)
            
            from src.multi_tenant.services import TenantRole
            role_map = {
                "viewer": TenantRole.VIEWER,
                "member": TenantRole.MEMBER,
                "admin": TenantRole.ADMIN,
                "owner": TenantRole.OWNER
            }
            
            required_role_enum = role_map.get(required_role.lower(), TenantRole.MEMBER)
            
            if not permission_service.has_tenant_permission(user_id, tenant_id, required_role_enum):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient tenant permissions. Required: {required_role}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_workspace_permission(required_role: str = "viewer"):
    """
    Decorator to require specific workspace permission for an endpoint.
    
    Args:
        required_role: Minimum required workspace role
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            context = get_tenant_context(request)
            user_id = context.get("user_id")
            workspace_id = context.get("workspace_id")
            
            if not user_id or not workspace_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication and workspace context required"
                )
            
            session = getattr(request.state, "db_session")
            permission_service = PermissionService(session)
            
            from src.multi_tenant.services import WorkspaceRole
            role_map = {
                "viewer": WorkspaceRole.VIEWER,
                "annotator": WorkspaceRole.ANNOTATOR,
                "reviewer": WorkspaceRole.REVIEWER,
                "admin": WorkspaceRole.ADMIN
            }
            
            required_role_enum = role_map.get(required_role.lower(), WorkspaceRole.VIEWER)
            
            if not permission_service.has_workspace_permission(user_id, workspace_id, required_role_enum):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient workspace permissions. Required: {required_role}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator