"""
API Key Service for External API Access Management.

Provides secure API key generation, validation, and lifecycle management
for external applications accessing SuperInsight AI-friendly data.
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.sync.models import APIKeyModel, APIKeyStatus
from src.database.connection import db_manager


logger = logging.getLogger(__name__)


class APIKeyConfig:
    """Configuration for API key creation."""
    
    def __init__(
        self,
        name: str,
        tenant_id: str,
        scopes: Dict[str, bool],
        description: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        rate_limit_per_minute: int = 60,
        rate_limit_per_day: int = 10000,
        created_by: Optional[str] = None
    ):
        self.name = name
        self.tenant_id = tenant_id
        self.scopes = scopes
        self.description = description
        self.expires_in_days = expires_in_days
        self.rate_limit_per_minute = rate_limit_per_minute
        self.rate_limit_per_day = rate_limit_per_day
        self.created_by = created_by


class APIKeyResponse:
    """Response containing API key information."""
    
    def __init__(
        self,
        id: UUID,
        name: str,
        key_prefix: str,
        raw_key: Optional[str] = None,
        scopes: Optional[Dict[str, bool]] = None,
        status: Optional[APIKeyStatus] = None,
        rate_limit_per_minute: Optional[int] = None,
        rate_limit_per_day: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        last_used_at: Optional[datetime] = None,
        total_calls: Optional[int] = None
    ):
        self.id = id
        self.name = name
        self.key_prefix = key_prefix
        self.raw_key = raw_key  # Only populated on creation
        self.scopes = scopes
        self.status = status
        self.rate_limit_per_minute = rate_limit_per_minute
        self.rate_limit_per_day = rate_limit_per_day
        self.expires_at = expires_at
        self.created_at = created_at
        self.last_used_at = last_used_at
        self.total_calls = total_calls
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "id": str(self.id),
            "name": self.name,
            "key_prefix": self.key_prefix
        }
        
        if self.raw_key is not None:
            result["raw_key"] = self.raw_key
        if self.scopes is not None:
            result["scopes"] = self.scopes
        if self.status is not None:
            result["status"] = self.status.value
        if self.rate_limit_per_minute is not None:
            result["rate_limit_per_minute"] = self.rate_limit_per_minute
        if self.rate_limit_per_day is not None:
            result["rate_limit_per_day"] = self.rate_limit_per_day
        if self.expires_at is not None:
            result["expires_at"] = self.expires_at.isoformat()
        if self.created_at is not None:
            result["created_at"] = self.created_at.isoformat()
        if self.last_used_at is not None:
            result["last_used_at"] = self.last_used_at.isoformat()
        if self.total_calls is not None:
            result["total_calls"] = self.total_calls
        
        return result


class APIKeyService:
    """
    Service for managing API keys for external API access.
    
    Features:
    - Secure key generation with SHA-256 hashing
    - Key lifecycle management (active/disabled/revoked)
    - Scope-based permissions
    - Expiration handling
    - Usage tracking
    """
    
    KEY_PREFIX = "sk_"
    KEY_LENGTH = 32  # 32 bytes = 64 hex characters
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize API key service.
        
        Args:
            session: Database session (optional, will create if not provided)
        """
        self._session = session
        self._owns_session = session is None
    
    def _get_session(self) -> Session:
        """Get database session."""
        if self._session:
            return self._session
        # For non-injected sessions, we'll use context manager in each method
        return None
    
    def _generate_key(self) -> tuple[str, str, str]:
        """
        Generate a secure API key.
        
        Returns:
            Tuple of (raw_key, key_prefix, key_hash)
        """
        # Generate random bytes
        random_bytes = secrets.token_bytes(self.KEY_LENGTH)
        random_hex = random_bytes.hex()
        
        # Create full key with prefix
        raw_key = f"{self.KEY_PREFIX}{random_hex}"
        
        # Extract prefix for identification (first 16 chars including prefix)
        key_prefix = raw_key[:16]
        
        # Hash the full key for storage
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        return raw_key, key_prefix, key_hash
    
    def create_key(self, config: APIKeyConfig) -> APIKeyResponse:
        """
        Create a new API key.
        
        Args:
            config: API key configuration
        
        Returns:
            APIKeyResponse with raw_key (only returned once)
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate configuration
        if not config.name or not config.name.strip():
            raise ValueError("API key name is required")
        if not config.tenant_id:
            raise ValueError("Tenant ID is required")
        if not config.scopes:
            raise ValueError("At least one scope is required")
        
        # Generate key
        raw_key, key_prefix, key_hash = self._generate_key()
        
        # Calculate expiration
        expires_at = None
        if config.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=config.expires_in_days)
        
        # Create model
        api_key = APIKeyModel(
            id=uuid4(),
            tenant_id=config.tenant_id,
            name=config.name.strip(),
            description=config.description,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=config.scopes,
            rate_limit_per_minute=config.rate_limit_per_minute,
            rate_limit_per_day=config.rate_limit_per_day,
            status=APIKeyStatus.ACTIVE,
            expires_at=expires_at,
            created_by=config.created_by
        )
        
        if self._session:
            # Use injected session
            session = self._session
            session.add(api_key)
            session.commit()
            session.refresh(api_key)
        else:
            # Use context manager
            with db_manager.get_session() as session:
                session.add(api_key)
                session.commit()
                session.refresh(api_key)
        
        logger.info(
            f"Created API key '{config.name}' for tenant {config.tenant_id}, "
            f"key_id={api_key.id}, prefix={key_prefix}"
        )
        
        # Return response with raw key (only time it's visible)
        return APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            raw_key=raw_key,  # Only returned on creation
            scopes=api_key.scopes,
            status=api_key.status,
            rate_limit_per_minute=api_key.rate_limit_per_minute,
            rate_limit_per_day=api_key.rate_limit_per_day,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
            total_calls=api_key.total_calls
        )
    
    def validate_key(self, raw_key: str) -> Optional[APIKeyModel]:
        """
        Validate an API key and check permissions/expiration.
        
        Args:
            raw_key: The raw API key to validate
        
        Returns:
            APIKeyModel if valid, None otherwise
        """
        if not raw_key or not raw_key.startswith(self.KEY_PREFIX):
            return None
        
        # Hash the provided key
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        def _validate(session: Session) -> Optional[APIKeyModel]:
            # Find key by hash
            stmt = select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
            api_key = session.execute(stmt).scalar_one_or_none()
            
            if not api_key:
                logger.warning(f"API key not found for hash")
                return None
            
            # Check status
            if api_key.status != APIKeyStatus.ACTIVE:
                logger.warning(
                    f"API key {api_key.id} is not active (status={api_key.status.value})"
                )
                return None
            
            # Check expiration
            if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                logger.warning(f"API key {api_key.id} has expired")
                return None
            
            logger.debug(f"API key {api_key.id} validated successfully")
            return api_key
        
        if self._session:
            return _validate(self._session)
        else:
            with db_manager.get_session() as session:
                return _validate(session)
    
    def revoke_key(self, key_id: UUID, tenant_id: str) -> bool:
        """
        Revoke an API key (terminal state).
        
        Args:
            key_id: API key ID
            tenant_id: Tenant ID (for authorization)
        
        Returns:
            True if revoked, False if not found or unauthorized
        """
        def _revoke(session: Session) -> bool:
            try:
                stmt = (
                    select(APIKeyModel)
                    .where(APIKeyModel.id == key_id)
                    .where(APIKeyModel.tenant_id == tenant_id)
                )
                api_key = session.execute(stmt).scalar_one_or_none()
                
                if not api_key:
                    logger.warning(f"API key {key_id} not found for tenant {tenant_id}")
                    return False
                
                # Revoke is terminal - cannot be undone
                api_key.status = APIKeyStatus.REVOKED
                session.commit()
                
                logger.info(f"Revoked API key {key_id} for tenant {tenant_id}")
                return True
            
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to revoke API key {key_id}: {e}")
                return False
        
        if self._session:
            return _revoke(self._session)
        else:
            with db_manager.get_session() as session:
                return _revoke(session)
    
    def enable_key(self, key_id: UUID, tenant_id: str) -> bool:
        """
        Enable a disabled API key.
        
        Args:
            key_id: API key ID
            tenant_id: Tenant ID (for authorization)
        
        Returns:
            True if enabled, False if not found, unauthorized, or revoked
        """
        def _enable(session: Session) -> bool:
            try:
                stmt = (
                    select(APIKeyModel)
                    .where(APIKeyModel.id == key_id)
                    .where(APIKeyModel.tenant_id == tenant_id)
                )
                api_key = session.execute(stmt).scalar_one_or_none()
                
                if not api_key:
                    logger.warning(f"API key {key_id} not found for tenant {tenant_id}")
                    return False
                
                # Cannot enable revoked keys
                if api_key.status == APIKeyStatus.REVOKED:
                    logger.warning(f"Cannot enable revoked API key {key_id}")
                    return False
                
                api_key.status = APIKeyStatus.ACTIVE
                session.commit()
                
                logger.info(f"Enabled API key {key_id} for tenant {tenant_id}")
                return True
            
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to enable API key {key_id}: {e}")
                return False
        
        if self._session:
            return _enable(self._session)
        else:
            with db_manager.get_session() as session:
                return _enable(session)
    
    def disable_key(self, key_id: UUID, tenant_id: str) -> bool:
        """
        Disable an active API key (can be re-enabled).
        
        Args:
            key_id: API key ID
            tenant_id: Tenant ID (for authorization)
        
        Returns:
            True if disabled, False if not found, unauthorized, or revoked
        """
        def _disable(session: Session) -> bool:
            try:
                stmt = (
                    select(APIKeyModel)
                    .where(APIKeyModel.id == key_id)
                    .where(APIKeyModel.tenant_id == tenant_id)
                )
                api_key = session.execute(stmt).scalar_one_or_none()
                
                if not api_key:
                    logger.warning(f"API key {key_id} not found for tenant {tenant_id}")
                    return False
                
                # Cannot disable revoked keys (already terminal)
                if api_key.status == APIKeyStatus.REVOKED:
                    logger.warning(f"Cannot disable revoked API key {key_id}")
                    return False
                
                api_key.status = APIKeyStatus.DISABLED
                session.commit()
                
                logger.info(f"Disabled API key {key_id} for tenant {tenant_id}")
                return True
            
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to disable API key {key_id}: {e}")
                return False
        
        if self._session:
            return _disable(self._session)
        else:
            with db_manager.get_session() as session:
                return _disable(session)
    
    def get_key(self, key_id: UUID, tenant_id: str) -> Optional[APIKeyResponse]:
        """
        Get API key information (without raw key).
        
        Args:
            key_id: API key ID
            tenant_id: Tenant ID (for authorization)
        
        Returns:
            APIKeyResponse without raw_key, or None if not found
        """
        def _get(session: Session) -> Optional[APIKeyResponse]:
            try:
                stmt = (
                    select(APIKeyModel)
                    .where(APIKeyModel.id == key_id)
                    .where(APIKeyModel.tenant_id == tenant_id)
                )
                api_key = session.execute(stmt).scalar_one_or_none()
                
                if not api_key:
                    return None
                
                return APIKeyResponse(
                    id=api_key.id,
                    name=api_key.name,
                    key_prefix=api_key.key_prefix,
                    raw_key=None,  # Never returned after creation
                    scopes=api_key.scopes,
                    status=api_key.status,
                    rate_limit_per_minute=api_key.rate_limit_per_minute,
                    rate_limit_per_day=api_key.rate_limit_per_day,
                    expires_at=api_key.expires_at,
                    created_at=api_key.created_at,
                    last_used_at=api_key.last_used_at,
                    total_calls=api_key.total_calls
                )
            
            except Exception as e:
                logger.error(f"Failed to get API key {key_id}: {e}")
                return None
        
        if self._session:
            return _get(self._session)
        else:
            with db_manager.get_session() as session:
                return _get(session)
    
    def list_keys(
        self,
        tenant_id: str,
        status: Optional[APIKeyStatus] = None
    ) -> List[APIKeyResponse]:
        """
        List API keys for a tenant.
        
        Args:
            tenant_id: Tenant ID
            status: Optional status filter
        
        Returns:
            List of APIKeyResponse (without raw keys)
        """
        def _list(session: Session) -> List[APIKeyResponse]:
            try:
                stmt = select(APIKeyModel).where(APIKeyModel.tenant_id == tenant_id)
                
                if status:
                    stmt = stmt.where(APIKeyModel.status == status)
                
                stmt = stmt.order_by(APIKeyModel.created_at.desc())
                
                api_keys = session.execute(stmt).scalars().all()
                
                return [
                    APIKeyResponse(
                        id=key.id,
                        name=key.name,
                        key_prefix=key.key_prefix,
                        raw_key=None,  # Never returned in list
                        scopes=key.scopes,
                        status=key.status,
                        rate_limit_per_minute=key.rate_limit_per_minute,
                        rate_limit_per_day=key.rate_limit_per_day,
                        expires_at=key.expires_at,
                        created_at=key.created_at,
                        last_used_at=key.last_used_at,
                        total_calls=key.total_calls
                    )
                    for key in api_keys
                ]
            
            except Exception as e:
                logger.error(f"Failed to list API keys for tenant {tenant_id}: {e}")
                return []
        
        if self._session:
            return _list(self._session)
        else:
            with db_manager.get_session() as session:
                return _list(session)
    
    def update_usage(
        self,
        key_id: UUID,
        increment_calls: bool = True
    ) -> bool:
        """
        Update API key usage statistics.
        
        Args:
            key_id: API key ID
            increment_calls: Whether to increment total_calls
        
        Returns:
            True if updated successfully
        """
        def _update(session: Session) -> bool:
            try:
                if increment_calls:
                    # Use SQL expression to increment atomically
                    stmt = (
                        update(APIKeyModel)
                        .where(APIKeyModel.id == key_id)
                        .values(
                            last_used_at=datetime.utcnow(),
                            total_calls=APIKeyModel.total_calls + 1
                        )
                    )
                else:
                    stmt = (
                        update(APIKeyModel)
                        .where(APIKeyModel.id == key_id)
                        .values(last_used_at=datetime.utcnow())
                    )
                
                result = session.execute(stmt)
                session.commit()
                
                return result.rowcount > 0
            
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to update usage for API key {key_id}: {e}")
                return False
        
        if self._session:
            return _update(self._session)
        else:
            with db_manager.get_session() as session:
                return _update(session)
