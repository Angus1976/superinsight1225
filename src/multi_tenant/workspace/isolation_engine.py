"""
Isolation Engine for Multi-Tenant Workspace module.

This module provides comprehensive tenant data isolation including:
- Tenant filtering for database queries
- Tenant access verification
- Data encryption/decryption per tenant
- Cross-tenant access logging
- Tenant filter middleware
"""

import logging
import secrets
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable, TypeVar
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, BinaryExpression
from sqlalchemy.sql import Select
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from src.multi_tenant.workspace.models import (
    ExtendedWorkspaceModel,
    CrossTenantAccessLogModel,
    TenantAuditLogModel,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class IsolationError(Exception):
    """Base exception for isolation errors."""
    pass


class TenantAccessDeniedError(IsolationError):
    """Exception raised when tenant access is denied."""
    pass


class CrossTenantAccessDeniedError(IsolationError):
    """Exception raised when cross-tenant access is denied."""
    pass


class EncryptionError(IsolationError):
    """Exception raised for encryption/decryption errors."""
    pass


class IsolationEngine:
    """
    Isolation Engine for ensuring tenant data isolation.
    
    Provides methods for:
    - Getting tenant filter conditions for queries
    - Verifying tenant access
    - Encrypting/decrypting tenant-specific data
    - Logging cross-tenant access attempts
    """
    
    # Salt for key derivation (in production, this should be per-tenant)
    DEFAULT_SALT = b'superinsight_tenant_isolation_salt'
    
    def __init__(
        self,
        session: Session,
        master_key: Optional[str] = None,
        audit_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None
    ):
        """
        Initialize IsolationEngine.
        
        Args:
            session: SQLAlchemy database session
            master_key: Master encryption key (if None, a default is used)
            audit_callback: Optional callback for audit logging
        """
        self.session = session
        self.master_key = master_key or "default_master_key_change_in_production"
        self.audit_callback = audit_callback
        self._encryption_keys: Dict[str, bytes] = {}
    
    def get_tenant_filter(
        self,
        tenant_id: str,
        model_class: Any = None
    ) -> BinaryExpression:
        """
        Get a SQLAlchemy filter condition for tenant isolation.
        
        Args:
            tenant_id: Tenant ID to filter by
            model_class: Optional model class (defaults to ExtendedTenantModel)
            
        Returns:
            SQLAlchemy BinaryExpression for filtering
        """
        if model_class is None:
            model_class = ExtendedWorkspaceModel
        
        # Assume the model has a tenant_id column
        if hasattr(model_class, 'tenant_id'):
            return model_class.tenant_id == tenant_id
        elif hasattr(model_class, 'id'):
            # For tenant model itself
            return model_class.id == tenant_id
        else:
            raise IsolationError(f"Model {model_class} does not have tenant_id column")
    
    def apply_tenant_filter(
        self,
        query: Select,
        tenant_id: str,
        model_class: Any = None
    ) -> Select:
        """
        Apply tenant filter to a SQLAlchemy query.
        
        Args:
            query: SQLAlchemy Select query
            tenant_id: Tenant ID to filter by
            model_class: Optional model class
            
        Returns:
            Filtered query
        """
        filter_condition = self.get_tenant_filter(tenant_id, model_class)
        return query.where(filter_condition)
    
    def verify_tenant_access(
        self,
        user_id: str,
        user_tenant_id: str,
        target_tenant_id: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> bool:
        """
        Verify if a user has access to a tenant's resources.
        
        Args:
            user_id: User ID attempting access
            user_tenant_id: User's tenant ID
            target_tenant_id: Target tenant ID
            resource_id: Optional resource ID being accessed
            resource_type: Optional resource type
            
        Returns:
            True if access is allowed, False otherwise
        """
        # Same tenant - always allowed
        if user_tenant_id == target_tenant_id:
            return True
        
        # Cross-tenant access - log and deny by default
        self._log_cross_tenant_access(
            accessor_tenant_id=user_tenant_id,
            owner_tenant_id=target_tenant_id,
            resource_id=resource_id or "unknown",
            resource_type=resource_type or "unknown",
            action="access_attempt",
            success=False,
            user_id=user_id
        )
        
        return False
    
    def check_cross_tenant_access(
        self,
        source_tenant_id: str,
        target_tenant_id: str,
        resource_id: str,
        resource_type: str,
        required_permission: str = "read"
    ) -> bool:
        """
        Check if cross-tenant access is allowed.
        
        This checks for explicit sharing or whitelist permissions.
        
        Args:
            source_tenant_id: Tenant requesting access
            target_tenant_id: Tenant owning the resource
            resource_id: Resource being accessed
            resource_type: Type of resource
            required_permission: Required permission level
            
        Returns:
            True if access is allowed
        """
        # Same tenant - always allowed
        if source_tenant_id == target_tenant_id:
            return True
        
        # Check whitelist (would need to import CrossTenantCollaborator)
        # For now, deny cross-tenant access by default
        return False
    
    def encrypt_tenant_data(
        self,
        tenant_id: str,
        data: bytes
    ) -> bytes:
        """
        Encrypt data using tenant-specific key.
        
        Args:
            tenant_id: Tenant ID for key derivation
            data: Data to encrypt
            
        Returns:
            Encrypted data
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            key = self._get_tenant_encryption_key(tenant_id)
            fernet = Fernet(key)
            return fernet.encrypt(data)
        except Exception as e:
            logger.error(f"Encryption failed for tenant {tenant_id}: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}")
    
    def decrypt_tenant_data(
        self,
        tenant_id: str,
        encrypted_data: bytes
    ) -> bytes:
        """
        Decrypt data using tenant-specific key.
        
        Args:
            tenant_id: Tenant ID for key derivation
            encrypted_data: Data to decrypt
            
        Returns:
            Decrypted data
            
        Raises:
            EncryptionError: If decryption fails
        """
        try:
            key = self._get_tenant_encryption_key(tenant_id)
            fernet = Fernet(key)
            return fernet.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"Decryption failed for tenant {tenant_id}: {e}")
            raise EncryptionError(f"Failed to decrypt data: {e}")
    
    def _get_tenant_encryption_key(self, tenant_id: str) -> bytes:
        """
        Get or derive encryption key for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Fernet-compatible encryption key
        """
        if tenant_id in self._encryption_keys:
            return self._encryption_keys[tenant_id]
        
        # Derive key from master key and tenant ID
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.DEFAULT_SALT + tenant_id.encode(),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(self.master_key.encode())
        )
        
        self._encryption_keys[tenant_id] = key
        return key
    
    def _log_cross_tenant_access(
        self,
        accessor_tenant_id: str,
        owner_tenant_id: str,
        resource_id: str,
        resource_type: str,
        action: str,
        success: bool,
        user_id: Optional[str] = None
    ) -> None:
        """
        Log a cross-tenant access attempt.
        
        Args:
            accessor_tenant_id: Tenant attempting access
            owner_tenant_id: Tenant owning the resource
            resource_id: Resource being accessed
            resource_type: Type of resource
            action: Action being performed
            success: Whether access was granted
            user_id: Optional user ID
        """
        try:
            log_entry = CrossTenantAccessLogModel(
                id=uuid4(),
                accessor_tenant_id=accessor_tenant_id,
                owner_tenant_id=owner_tenant_id,
                resource_id=resource_id,
                resource_type=resource_type,
                action=action,
                success=success,
            )
            self.session.add(log_entry)
            self.session.flush()
            
            # Also call audit callback if provided
            if self.audit_callback:
                self.audit_callback(
                    "cross_tenant_access",
                    accessor_tenant_id,
                    {
                        "owner_tenant_id": owner_tenant_id,
                        "resource_id": resource_id,
                        "resource_type": resource_type,
                        "action": action,
                        "success": success,
                        "user_id": user_id,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to log cross-tenant access: {e}")
    
    def get_cross_tenant_access_logs(
        self,
        tenant_id: str,
        as_owner: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[CrossTenantAccessLogModel]:
        """
        Get cross-tenant access logs for a tenant.
        
        Args:
            tenant_id: Tenant ID
            as_owner: If True, get logs where tenant is owner; else accessor
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of access log entries
        """
        if as_owner:
            query = self.session.query(CrossTenantAccessLogModel).filter(
                CrossTenantAccessLogModel.owner_tenant_id == tenant_id
            )
        else:
            query = self.session.query(CrossTenantAccessLogModel).filter(
                CrossTenantAccessLogModel.accessor_tenant_id == tenant_id
            )
        
        return query.order_by(
            CrossTenantAccessLogModel.created_at.desc()
        ).offset(offset).limit(limit).all()
    
    def log_audit(
        self,
        tenant_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None
    ) -> None:
        """
        Log an audit entry for tenant operations.
        
        Args:
            tenant_id: Tenant ID
            action: Action performed
            resource_type: Type of resource
            resource_id: Optional resource ID
            details: Optional additional details
            user_id: Optional user ID
        """
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


class TenantContext:
    """
    Context manager for tenant-scoped operations.
    
    Ensures all database operations within the context
    are filtered by tenant ID.
    """
    
    def __init__(
        self,
        isolation_engine: IsolationEngine,
        tenant_id: str,
        user_id: Optional[str] = None
    ):
        """
        Initialize TenantContext.
        
        Args:
            isolation_engine: IsolationEngine instance
            tenant_id: Tenant ID for this context
            user_id: Optional user ID
        """
        self.isolation_engine = isolation_engine
        self.tenant_id = tenant_id
        self.user_id = user_id
    
    def __enter__(self):
        """Enter the tenant context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the tenant context."""
        pass
    
    def filter_query(self, query: Select, model_class: Any = None) -> Select:
        """
        Apply tenant filter to a query.
        
        Args:
            query: SQLAlchemy query
            model_class: Optional model class
            
        Returns:
            Filtered query
        """
        return self.isolation_engine.apply_tenant_filter(
            query, self.tenant_id, model_class
        )
    
    def verify_access(
        self,
        target_tenant_id: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> bool:
        """
        Verify access to a resource.
        
        Args:
            target_tenant_id: Target tenant ID
            resource_id: Optional resource ID
            resource_type: Optional resource type
            
        Returns:
            True if access is allowed
        """
        return self.isolation_engine.verify_tenant_access(
            user_id=self.user_id or "unknown",
            user_tenant_id=self.tenant_id,
            target_tenant_id=target_tenant_id,
            resource_id=resource_id,
            resource_type=resource_type
        )


class TenantFilterMiddleware:
    """
    Middleware for automatic tenant filtering.
    
    This middleware can be used with FastAPI to automatically
    inject tenant context into requests.
    """
    
    def __init__(
        self,
        isolation_engine: IsolationEngine,
        tenant_header: str = "X-Tenant-ID",
        skip_paths: Optional[List[str]] = None
    ):
        """
        Initialize TenantFilterMiddleware.
        
        Args:
            isolation_engine: IsolationEngine instance
            tenant_header: Header name for tenant ID
            skip_paths: Paths to skip tenant filtering
        """
        self.isolation_engine = isolation_engine
        self.tenant_header = tenant_header
        self.skip_paths = skip_paths or ["/health", "/docs", "/openapi.json"]
    
    async def __call__(self, request, call_next):
        """
        Process request with tenant filtering.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Skip certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        # Get tenant ID from header or token
        tenant_id = request.headers.get(self.tenant_header)
        
        if not tenant_id:
            # Try to get from authenticated user
            if hasattr(request.state, 'user') and hasattr(request.state.user, 'tenant_id'):
                tenant_id = request.state.user.tenant_id
        
        if not tenant_id:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=401,
                detail="Tenant not identified"
            )
        
        # Set tenant context on request
        request.state.tenant_id = tenant_id
        request.state.tenant_context = TenantContext(
            self.isolation_engine,
            tenant_id,
            getattr(request.state, 'user_id', None)
        )
        
        # Create filter function for convenience
        request.state.tenant_filter = lambda q, m=None: self.isolation_engine.apply_tenant_filter(
            q, tenant_id, m
        )
        
        response = await call_next(request)
        return response
