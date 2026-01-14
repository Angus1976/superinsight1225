"""
Cross Tenant Collaborator for Multi-Tenant Workspace module.

This module provides cross-tenant collaboration features including:
- Share link creation and management
- Token generation and validation
- Whitelist management
- Access logging and auditing
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.multi_tenant.workspace.models import (
    ShareLinkModel,
    TenantWhitelistModel,
    CrossTenantAccessLogModel,
    TenantAuditLogModel,
    SharePermission,
)

logger = logging.getLogger(__name__)


class CrossTenantError(Exception):
    """Base exception for cross-tenant errors."""
    pass


class ShareNotFoundError(CrossTenantError):
    """Exception raised when share is not found."""
    pass


class ShareExpiredError(CrossTenantError):
    """Exception raised when share has expired."""
    pass


class ShareRevokedError(CrossTenantError):
    """Exception raised when share has been revoked."""
    pass


class TenantNotWhitelistedError(CrossTenantError):
    """Exception raised when tenant is not in whitelist."""
    pass


class InvalidTokenError(CrossTenantError):
    """Exception raised when token is invalid."""
    pass


class CrossTenantCollaborator:
    """
    Cross Tenant Collaborator for managing cross-tenant resource sharing.
    
    Provides methods for:
    - Creating and managing share links
    - Token generation and validation
    - Whitelist management
    - Access logging
    """
    
    # Default token length
    TOKEN_LENGTH = 32
    # Default share expiration
    DEFAULT_EXPIRATION_DAYS = 7
    
    def __init__(
        self,
        session: Session,
        require_whitelist: bool = True
    ):
        """
        Initialize CrossTenantCollaborator.
        
        Args:
            session: SQLAlchemy database session
            require_whitelist: Whether to require whitelist for access
        """
        self.session = session
        self.require_whitelist = require_whitelist
    
    def create_share(
        self,
        owner_tenant_id: str,
        resource_id: str,
        resource_type: str,
        permission: SharePermission = SharePermission.READ_ONLY,
        expires_in: Optional[timedelta] = None,
        allowed_tenant_ids: Optional[List[str]] = None,
        max_uses: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> ShareLinkModel:
        """
        Create a share link for a resource.
        
        Args:
            owner_tenant_id: Tenant ID owning the resource
            resource_id: Resource ID to share
            resource_type: Type of resource
            permission: Permission level for the share
            expires_in: Time until expiration (default: 7 days)
            allowed_tenant_ids: Optional list of allowed tenant IDs
            max_uses: Optional maximum number of uses
            created_by: Optional user ID who created the share
            
        Returns:
            Created ShareLinkModel
        """
        if expires_in is None:
            expires_in = timedelta(days=self.DEFAULT_EXPIRATION_DAYS)
        
        token = self._generate_token()
        expires_at = datetime.utcnow() + expires_in
        
        share = ShareLinkModel(
            id=uuid4(),
            resource_id=resource_id,
            resource_type=resource_type,
            owner_tenant_id=owner_tenant_id,
            permission=permission,
            token=token,
            expires_at=expires_at,
            allowed_tenant_ids=allowed_tenant_ids,
            max_uses=max_uses,
            use_count=0,
            revoked=False,
        )
        
        self.session.add(share)
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=owner_tenant_id,
            action="share_created",
            resource_type="share_link",
            resource_id=str(share.id),
            details={
                "resource_id": resource_id,
                "resource_type": resource_type,
                "permission": permission.value,
                "expires_at": expires_at.isoformat(),
            }
        )
        
        logger.info(f"Created share link for {resource_type}/{resource_id} by tenant {owner_tenant_id}")
        return share
    
    def access_shared_resource(
        self,
        token: str,
        accessor_tenant_id: str,
        accessor_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Access a shared resource using a token.
        
        Args:
            token: Share token
            accessor_tenant_id: Tenant ID attempting access
            accessor_user_id: Optional user ID
            
        Returns:
            Dictionary with share info and permission
            
        Raises:
            ShareNotFoundError: If share not found
            ShareExpiredError: If share has expired
            ShareRevokedError: If share has been revoked
            TenantNotWhitelistedError: If tenant not allowed
        """
        share = self.get_share_by_token(token)
        
        if not share:
            raise ShareNotFoundError("Share link not found")
        
        # Check if revoked
        if share.revoked:
            self._log_cross_tenant_access(
                accessor_tenant_id=accessor_tenant_id,
                owner_tenant_id=share.owner_tenant_id,
                resource_id=share.resource_id,
                resource_type=share.resource_type,
                action="access_revoked_share",
                success=False
            )
            raise ShareRevokedError("Share link has been revoked")
        
        # Check if expired
        if share.expires_at < datetime.utcnow():
            self._log_cross_tenant_access(
                accessor_tenant_id=accessor_tenant_id,
                owner_tenant_id=share.owner_tenant_id,
                resource_id=share.resource_id,
                resource_type=share.resource_type,
                action="access_expired_share",
                success=False
            )
            raise ShareExpiredError("Share link has expired")
        
        # Check max uses
        if share.max_uses is not None and share.use_count >= share.max_uses:
            self._log_cross_tenant_access(
                accessor_tenant_id=accessor_tenant_id,
                owner_tenant_id=share.owner_tenant_id,
                resource_id=share.resource_id,
                resource_type=share.resource_type,
                action="access_max_uses_exceeded",
                success=False
            )
            raise ShareExpiredError("Share link has reached maximum uses")
        
        # Check allowed tenants (if specified on share)
        if share.allowed_tenant_ids:
            if accessor_tenant_id not in share.allowed_tenant_ids:
                self._log_cross_tenant_access(
                    accessor_tenant_id=accessor_tenant_id,
                    owner_tenant_id=share.owner_tenant_id,
                    resource_id=share.resource_id,
                    resource_type=share.resource_type,
                    action="access_tenant_not_allowed",
                    success=False
                )
                raise TenantNotWhitelistedError("Tenant not allowed to access this share")
        
        # Check whitelist (if required)
        if self.require_whitelist:
            if not self.is_tenant_whitelisted(share.owner_tenant_id, accessor_tenant_id):
                self._log_cross_tenant_access(
                    accessor_tenant_id=accessor_tenant_id,
                    owner_tenant_id=share.owner_tenant_id,
                    resource_id=share.resource_id,
                    resource_type=share.resource_type,
                    action="access_not_whitelisted",
                    success=False
                )
                raise TenantNotWhitelistedError("Tenant not in whitelist")
        
        # Increment use count
        share.use_count += 1
        self.session.commit()
        
        # Log successful access
        self._log_cross_tenant_access(
            accessor_tenant_id=accessor_tenant_id,
            owner_tenant_id=share.owner_tenant_id,
            resource_id=share.resource_id,
            resource_type=share.resource_type,
            action="access_shared_resource",
            success=True
        )
        
        logger.info(f"Tenant {accessor_tenant_id} accessed shared resource {share.resource_id}")
        
        return {
            "share_id": str(share.id),
            "resource_id": share.resource_id,
            "resource_type": share.resource_type,
            "permission": share.permission.value,
            "owner_tenant_id": share.owner_tenant_id,
        }
    
    def get_share_by_token(self, token: str) -> Optional[ShareLinkModel]:
        """
        Get a share by its token.
        
        Args:
            token: Share token
            
        Returns:
            ShareLinkModel if found, None otherwise
        """
        return self.session.query(ShareLinkModel).filter(
            ShareLinkModel.token == token
        ).first()
    
    def get_share_by_id(self, share_id: UUID) -> Optional[ShareLinkModel]:
        """
        Get a share by its ID.
        
        Args:
            share_id: Share ID
            
        Returns:
            ShareLinkModel if found, None otherwise
        """
        return self.session.query(ShareLinkModel).filter(
            ShareLinkModel.id == share_id
        ).first()
    
    def revoke_share(
        self,
        share_id: str,
        owner_tenant_id: Optional[str] = None,
        revoked_by: Optional[str] = None
    ) -> bool:
        """
        Revoke a share link.
        
        Args:
            share_id: Share ID to revoke
            owner_tenant_id: Optional tenant ID for ownership verification
            revoked_by: Optional user ID who revoked
            
        Returns:
            True if revoked, False if not found or not owned
            
        Raises:
            ShareNotFoundError: If share not found
        """
        try:
            share_uuid = UUID(share_id) if isinstance(share_id, str) else share_id
        except ValueError:
            return False
            
        share = self.get_share_by_id(share_uuid)
        
        if not share:
            return False
        
        # Verify ownership if tenant_id provided
        if owner_tenant_id and share.owner_tenant_id != owner_tenant_id:
            return False
        
        share.revoked = True
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=share.owner_tenant_id,
            action="share_revoked",
            resource_type="share_link",
            resource_id=str(share_id),
            details={
                "resource_id": share.resource_id,
                "resource_type": share.resource_type,
                "revoked_by": revoked_by,
            }
        )
        
        logger.info(f"Revoked share link {share_id}")
        return True
    
    def list_shares(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        include_expired: bool = False,
        include_revoked: bool = False
    ) -> List[ShareLinkModel]:
        """
        List all shares created by a tenant with pagination.
        
        Args:
            tenant_id: Tenant ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_expired: Include expired shares
            include_revoked: Include revoked shares
            
        Returns:
            List of ShareLinkModel instances
        """
        query = self.session.query(ShareLinkModel).filter(
            ShareLinkModel.owner_tenant_id == tenant_id
        )
        
        if not include_expired:
            query = query.filter(ShareLinkModel.expires_at > datetime.utcnow())
        
        if not include_revoked:
            query = query.filter(ShareLinkModel.revoked == False)
        
        return query.order_by(ShareLinkModel.created_at.desc()).offset(skip).limit(limit).all()
    
    def set_whitelist(
        self,
        owner_tenant_id: str,
        allowed_tenant_ids: List[str]
    ) -> List[TenantWhitelistModel]:
        """
        Set the whitelist for a tenant.
        
        This replaces any existing whitelist entries.
        
        Args:
            owner_tenant_id: Tenant ID setting the whitelist
            allowed_tenant_ids: List of allowed tenant IDs
            
        Returns:
            List of created TenantWhitelistModel entries
        """
        # Remove existing whitelist entries
        self.session.query(TenantWhitelistModel).filter(
            TenantWhitelistModel.owner_tenant_id == owner_tenant_id
        ).delete()
        
        # Create new entries
        entries = []
        for allowed_id in allowed_tenant_ids:
            entry = TenantWhitelistModel(
                id=uuid4(),
                owner_tenant_id=owner_tenant_id,
                allowed_tenant_id=allowed_id,
            )
            self.session.add(entry)
            entries.append(entry)
        
        self.session.commit()
        
        # Log audit
        self._log_audit(
            tenant_id=owner_tenant_id,
            action="whitelist_updated",
            resource_type="whitelist",
            resource_id=owner_tenant_id,
            details={
                "allowed_tenants": allowed_tenant_ids,
                "count": len(allowed_tenant_ids),
            }
        )
        
        logger.info(f"Updated whitelist for tenant {owner_tenant_id}: {len(allowed_tenant_ids)} entries")
        return entries
    
    def add_to_whitelist(
        self,
        owner_tenant_id: str,
        allowed_tenant_id: str
    ) -> TenantWhitelistModel:
        """
        Add a tenant to the whitelist.
        
        Args:
            owner_tenant_id: Tenant ID owning the whitelist
            allowed_tenant_id: Tenant ID to add
            
        Returns:
            Created TenantWhitelistModel
        """
        # Check if already exists
        existing = self.session.query(TenantWhitelistModel).filter(
            and_(
                TenantWhitelistModel.owner_tenant_id == owner_tenant_id,
                TenantWhitelistModel.allowed_tenant_id == allowed_tenant_id
            )
        ).first()
        
        if existing:
            return existing
        
        entry = TenantWhitelistModel(
            id=uuid4(),
            owner_tenant_id=owner_tenant_id,
            allowed_tenant_id=allowed_tenant_id,
        )
        self.session.add(entry)
        self.session.commit()
        
        logger.info(f"Added tenant {allowed_tenant_id} to whitelist of {owner_tenant_id}")
        return entry
    
    def remove_from_whitelist(
        self,
        owner_tenant_id: str,
        allowed_tenant_id: str
    ) -> bool:
        """
        Remove a tenant from the whitelist.
        
        Args:
            owner_tenant_id: Tenant ID owning the whitelist
            allowed_tenant_id: Tenant ID to remove
            
        Returns:
            True if removed, False if not found
        """
        result = self.session.query(TenantWhitelistModel).filter(
            and_(
                TenantWhitelistModel.owner_tenant_id == owner_tenant_id,
                TenantWhitelistModel.allowed_tenant_id == allowed_tenant_id
            )
        ).delete()
        
        self.session.commit()
        
        if result > 0:
            logger.info(f"Removed tenant {allowed_tenant_id} from whitelist of {owner_tenant_id}")
            return True
        return False
    
    def is_tenant_whitelisted(
        self,
        owner_tenant_id: str,
        accessor_tenant_id: str
    ) -> bool:
        """
        Check if a tenant is in the whitelist.
        
        Args:
            owner_tenant_id: Tenant ID owning the whitelist
            accessor_tenant_id: Tenant ID to check
            
        Returns:
            True if whitelisted, False otherwise
        """
        # Same tenant is always allowed
        if owner_tenant_id == accessor_tenant_id:
            return True
        
        entry = self.session.query(TenantWhitelistModel).filter(
            and_(
                TenantWhitelistModel.owner_tenant_id == owner_tenant_id,
                TenantWhitelistModel.allowed_tenant_id == accessor_tenant_id
            )
        ).first()
        
        return entry is not None
    
    def get_whitelist(self, owner_tenant_id: str) -> List[str]:
        """
        Get the whitelist for a tenant.
        
        Args:
            owner_tenant_id: Tenant ID
            
        Returns:
            List of allowed tenant IDs
        """
        entries = self.session.query(TenantWhitelistModel).filter(
            TenantWhitelistModel.owner_tenant_id == owner_tenant_id
        ).all()
        
        return [e.allowed_tenant_id for e in entries]
    
    def get_shares_by_tenant(
        self,
        tenant_id: str,
        include_expired: bool = False,
        include_revoked: bool = False
    ) -> List[ShareLinkModel]:
        """
        Get all shares created by a tenant.
        
        Args:
            tenant_id: Tenant ID
            include_expired: Include expired shares
            include_revoked: Include revoked shares
            
        Returns:
            List of ShareLinkModel instances
        """
        query = self.session.query(ShareLinkModel).filter(
            ShareLinkModel.owner_tenant_id == tenant_id
        )
        
        if not include_expired:
            query = query.filter(ShareLinkModel.expires_at > datetime.utcnow())
        
        if not include_revoked:
            query = query.filter(ShareLinkModel.revoked == False)
        
        return query.all()
    
    def _generate_token(self) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(self.TOKEN_LENGTH)
    
    def _log_cross_tenant_access(
        self,
        accessor_tenant_id: str,
        owner_tenant_id: str,
        resource_id: str,
        resource_type: str,
        action: str,
        success: bool
    ) -> None:
        """Log a cross-tenant access attempt."""
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
        except Exception as e:
            logger.warning(f"Failed to log cross-tenant access: {e}")
    
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
