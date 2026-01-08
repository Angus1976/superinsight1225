"""
Tenant Authentication and Authorization Middleware

Implements tenant-aware request processing and data isolation.
"""

import logging
from typing import Optional, Dict, Any, Callable
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import jwt
from datetime import datetime
import json

from src.config.settings import settings
from src.security.models import UserModel, AuditLogModel, AuditAction
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()


class TenantContext:
    """Thread-local tenant context for request processing."""
    
    def __init__(self):
        self.tenant_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.user_role: Optional[str] = None
        self.permissions: Dict[str, Any] = {}
        self.request_id: Optional[str] = None
    
    def clear(self):
        """Clear the current context."""
        self.tenant_id = None
        self.user_id = None
        self.user_role = None
        self.permissions = {}
        self.request_id = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.user_id is not None and self.tenant_id is not None
    
    def has_permission(self, resource: str, action: str) -> bool:
        """Check if user has specific permission."""
        if not self.is_authenticated():
            return False
        
        # Admin users have all permissions
        if self.user_role == "admin":
            return True
        
        # Check specific permissions
        resource_perms = self.permissions.get(resource, {})
        return action in resource_perms.get("actions", [])


# Global tenant context instance
tenant_context = TenantContext()


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware for tenant authentication and request processing."""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health", "/docs", "/openapi.json", "/redoc",
            "/auth/login", "/auth/register", "/auth/refresh"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tenant context."""
        
        # Clear previous context
        tenant_context.clear()
        
        # Skip middleware for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        try:
            # Extract and validate tenant information
            await self._extract_tenant_context(request)
            
            # Add tenant context to request state
            request.state.tenant_context = tenant_context
            
            # Process the request
            response = await call_next(request)
            
            # Log the request for audit
            await self._log_request(request, response)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        finally:
            # Clear context after request
            tenant_context.clear()
    
    def _extract_tenant_from_token(self, token: str) -> Dict[str, Any]:
        """Extract tenant information from JWT token."""
        try:
            payload = jwt.decode(
                token, 
                settings.security.secret_key, 
                algorithms=["HS256"]
            )
            
            return {
                'tenant_id': payload.get("tenant_id"),
                'user_id': payload.get("user_id"),
                'role': payload.get("role"),
                'permissions': payload.get("permissions", {})
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    async def _extract_tenant_context(self, request: Request):
        """Extract tenant context from request."""
        
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        # Extract JWT token
        token = auth_header.split(" ")[1]
        
        try:
            # Decode JWT token
            payload = jwt.decode(
                token, 
                settings.security.secret_key, 
                algorithms=["HS256"]
            )
            
            # Extract tenant and user information
            tenant_context.tenant_id = payload.get("tenant_id")
            tenant_context.user_id = payload.get("user_id")
            tenant_context.user_role = payload.get("role")
            tenant_context.permissions = payload.get("permissions", {})
            
            # Validate required fields
            if not tenant_context.tenant_id or not tenant_context.user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing tenant or user information"
                )
            
            # Verify user exists and is active
            await self._verify_user_active(tenant_context.user_id, tenant_context.tenant_id)
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def _verify_user_active(self, user_id: str, tenant_id: str):
        """Verify user is active and belongs to tenant."""
        
        with get_db_session() as session:
            user = session.query(UserModel).filter(
                UserModel.id == user_id,
                UserModel.tenant_id == tenant_id,
                UserModel.is_active == True
            ).first()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
    
    async def _log_request(self, request: Request, response: Response):
        """Log request for audit purposes."""
        
        if not tenant_context.is_authenticated():
            return
        
        try:
            # Determine action based on HTTP method and path
            action = self._determine_audit_action(request.method, request.url.path)
            
            # Extract resource information
            resource_type = self._extract_resource_type(request.url.path)
            resource_id = self._extract_resource_id(request.url.path)
            
            # Create audit log entry
            with get_db_session() as session:
                audit_log = AuditLogModel(
                    user_id=tenant_context.user_id,
                    tenant_id=tenant_context.tenant_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("User-Agent"),
                    details={
                        "method": request.method,
                        "path": str(request.url.path),
                        "status_code": response.status_code,
                        "query_params": dict(request.query_params)
                    }
                )
                session.add(audit_log)
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")
    
    def _determine_audit_action(self, method: str, path: str) -> AuditAction:
        """Determine audit action from HTTP method and path."""
        
        if method == "GET":
            return AuditAction.READ
        elif method == "POST":
            return AuditAction.CREATE
        elif method in ["PUT", "PATCH"]:
            return AuditAction.UPDATE
        elif method == "DELETE":
            return AuditAction.DELETE
        else:
            return AuditAction.READ
    
    def _extract_resource_type(self, path: str) -> str:
        """Extract resource type from URL path."""
        
        # Remove leading slash and split path
        parts = path.lstrip("/").split("/")
        
        if len(parts) > 0:
            return parts[0]  # First part is usually the resource type
        
        return "unknown"
    
    def _extract_resource_id(self, path: str) -> Optional[str]:
        """Extract resource ID from URL path."""
        
        # Look for UUID-like patterns in path
        import re
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        matches = re.findall(uuid_pattern, path, re.IGNORECASE)
        
        if matches:
            return matches[0]
        
        return None


class TenantPermissionChecker:
    """Dependency for checking tenant-specific permissions."""
    
    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action
    
    def __call__(self, request: Request) -> bool:
        """Check if current user has required permission."""
        
        context = getattr(request.state, 'tenant_context', None)
        if not context or not context.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if not context.has_permission(self.resource, self.action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {self.action} on {self.resource}"
            )
        
        return True


def get_current_tenant() -> str:
    """Get current tenant ID from context."""
    if not tenant_context.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No tenant context available"
        )
    return tenant_context.tenant_id


def get_current_user() -> str:
    """Get current user ID from context."""
    if not tenant_context.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No user context available"
        )
    return tenant_context.user_id


def get_tenant_context() -> TenantContext:
    """Get full tenant context."""
    return tenant_context


def require_permission(resource: str, action: str):
    """Decorator for requiring specific permissions."""
    return Depends(TenantPermissionChecker(resource, action))


class TenantSessionManager:
    """Manages tenant-specific user sessions."""
    
    def __init__(self):
        self.sessions = {}  # In production, this would use Redis or database
    
    def create_session(self, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Create a new session for a user in a tenant."""
        import uuid
        
        session_id = str(uuid.uuid4())
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'tenant_id': tenant_id,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat()
        }
        
        self.sessions[session_id] = session_data
        return session_data
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by session ID."""
        return self.sessions.get(session_id)
    
    def validate_session(self, session_id: str, tenant_id: str) -> bool:
        """Validate that session belongs to the specified tenant."""
        session = self.get_session(session_id)
        if not session:
            return False
        
        return session['tenant_id'] == tenant_id
    
    def invalidate_session(self, session_id: str):
        """Invalidate a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]


# Common permission dependencies
require_read_documents = require_permission("documents", "read")
require_write_documents = require_permission("documents", "write")
require_read_tasks = require_permission("tasks", "read")
require_write_tasks = require_permission("tasks", "write")
require_admin_access = require_permission("admin", "all")


class TenantQueryFilter:
    """Helper for adding tenant filters to database queries."""
    
    @staticmethod
    def filter_by_tenant(query, model_class, tenant_id: Optional[str] = None):
        """Add tenant filter to SQLAlchemy query."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        # Check if model has tenant_id attribute
        if hasattr(model_class, 'tenant_id'):
            return query.filter(model_class.tenant_id == tenant_id)
        
        return query
    
    @staticmethod
    def ensure_tenant_access(obj, tenant_id: Optional[str] = None):
        """Ensure object belongs to current tenant."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        if hasattr(obj, 'tenant_id') and obj.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: resource belongs to different tenant"
            )
    
    @staticmethod
    def set_tenant_id(obj, tenant_id: Optional[str] = None):
        """Set tenant_id on object before saving."""
        
        if tenant_id is None:
            tenant_id = get_current_tenant()
        
        if hasattr(obj, 'tenant_id'):
            obj.tenant_id = tenant_id


# Convenience functions for common operations
def get_tenant_filtered_query(session, model_class, tenant_id: Optional[str] = None):
    """Get a tenant-filtered query for a model."""
    query = session.query(model_class)
    return TenantQueryFilter.filter_by_tenant(query, model_class, tenant_id)


def create_tenant_object(session, model_class, **kwargs):
    """Create an object with tenant_id automatically set."""
    obj = model_class(**kwargs)
    TenantQueryFilter.set_tenant_id(obj)
    session.add(obj)
    return obj