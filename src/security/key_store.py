"""
Key Store for SuperInsight Platform.

Manages encryption keys with secure storage and rotation capabilities.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import uuid4
import secrets
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload

from src.models.security import EncryptionKeyModel


@dataclass
class EncryptionKey:
    """Encryption key data structure."""
    id: str
    key_bytes: bytes
    algorithm: str
    status: str  # active, rotating, retired
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "algorithm": self.algorithm,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


class KeyStore:
    """
    Secure key storage and management system.
    
    Handles encryption key generation, storage, rotation, and lifecycle management.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self._key_cache: Dict[str, EncryptionKey] = {}
        self._cache_ttl = timedelta(hours=1)
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def generate_key(
        self,
        algorithm: str = "AES-256",
        expires_in_days: Optional[int] = None
    ) -> EncryptionKey:
        """
        Generate a new encryption key.
        
        Args:
            algorithm: Encryption algorithm (default: AES-256)
            expires_in_days: Key expiration in days (optional)
            
        Returns:
            Generated EncryptionKey
        """
        key_id = str(uuid4())
        
        # Generate key bytes based on algorithm
        if algorithm == "AES-256":
            key_bytes = secrets.token_bytes(32)  # 256 bits
        elif algorithm == "AES-128":
            key_bytes = secrets.token_bytes(16)  # 128 bits
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create key object
        key = EncryptionKey(
            id=key_id,
            key_bytes=key_bytes,
            algorithm=algorithm,
            status="active",
            created_at=datetime.utcnow(),
            expires_at=expires_at
        )
        
        # Store in database
        await self._store_key(key)
        
        # Cache the key
        self._key_cache[key_id] = key
        self._cache_timestamps[key_id] = datetime.utcnow()
        
        self.logger.info(f"Generated new encryption key: {key_id} ({algorithm})")
        
        return key
    
    async def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        """
        Retrieve encryption key by ID.
        
        Args:
            key_id: Key identifier
            
        Returns:
            EncryptionKey if found, None otherwise
        """
        # Check cache first
        if key_id in self._key_cache:
            cache_time = self._cache_timestamps.get(key_id)
            if cache_time and datetime.utcnow() - cache_time < self._cache_ttl:
                return self._key_cache[key_id]
        
        # Load from database
        stmt = select(EncryptionKeyModel).where(EncryptionKeyModel.id == key_id)
        result = await self.db.execute(stmt)
        db_key = result.scalar_one_or_none()
        
        if not db_key:
            return None
        
        # Convert to EncryptionKey object
        key = EncryptionKey(
            id=str(db_key.id),
            key_bytes=db_key.key_data,
            algorithm=db_key.algorithm,
            status=db_key.status,
            created_at=db_key.created_at,
            expires_at=db_key.expires_at
        )
        
        # Update cache
        self._key_cache[key_id] = key
        self._cache_timestamps[key_id] = datetime.utcnow()
        
        return key
    
    async def get_active_key(self, algorithm: str = "AES-256") -> Optional[EncryptionKey]:
        """
        Get the current active key for an algorithm.
        
        Args:
            algorithm: Encryption algorithm
            
        Returns:
            Active EncryptionKey if found, None otherwise
        """
        stmt = select(EncryptionKeyModel).where(
            and_(
                EncryptionKeyModel.algorithm == algorithm,
                EncryptionKeyModel.status == "active"
            )
        ).order_by(desc(EncryptionKeyModel.created_at)).limit(1)
        
        result = await self.db.execute(stmt)
        db_key = result.scalar_one_or_none()
        
        if not db_key:
            return None
        
        return EncryptionKey(
            id=str(db_key.id),
            key_bytes=db_key.key_data,
            algorithm=db_key.algorithm,
            status=db_key.status,
            created_at=db_key.created_at,
            expires_at=db_key.expires_at
        )
    
    async def list_keys(
        self,
        algorithm: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[EncryptionKey]:
        """
        List encryption keys with optional filtering.
        
        Args:
            algorithm: Filter by algorithm (optional)
            status: Filter by status (optional)
            limit: Maximum number of keys to return
            
        Returns:
            List of EncryptionKey objects
        """
        stmt = select(EncryptionKeyModel)
        
        conditions = []
        if algorithm:
            conditions.append(EncryptionKeyModel.algorithm == algorithm)
        if status:
            conditions.append(EncryptionKeyModel.status == status)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(desc(EncryptionKeyModel.created_at)).limit(limit)
        
        result = await self.db.execute(stmt)
        db_keys = list(result.scalars().all())
        
        keys = []
        for db_key in db_keys:
            key = EncryptionKey(
                id=str(db_key.id),
                key_bytes=db_key.key_data,
                algorithm=db_key.algorithm,
                status=db_key.status,
                created_at=db_key.created_at,
                expires_at=db_key.expires_at
            )
            keys.append(key)
        
        return keys
    
    async def mark_for_rotation(self, key_id: str) -> bool:
        """
        Mark key for rotation.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if marked successfully, False otherwise
        """
        stmt = select(EncryptionKeyModel).where(EncryptionKeyModel.id == key_id)
        result = await self.db.execute(stmt)
        db_key = result.scalar_one_or_none()
        
        if not db_key:
            return False
        
        db_key.status = "rotating"
        db_key.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        # Remove from cache
        if key_id in self._key_cache:
            del self._key_cache[key_id]
            del self._cache_timestamps[key_id]
        
        self.logger.info(f"Marked key for rotation: {key_id}")
        
        return True
    
    async def retire_key(self, key_id: str) -> bool:
        """
        Retire an encryption key.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if retired successfully, False otherwise
        """
        stmt = select(EncryptionKeyModel).where(EncryptionKeyModel.id == key_id)
        result = await self.db.execute(stmt)
        db_key = result.scalar_one_or_none()
        
        if not db_key:
            return False
        
        db_key.status = "retired"
        db_key.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        # Remove from cache
        if key_id in self._key_cache:
            del self._key_cache[key_id]
            del self._cache_timestamps[key_id]
        
        self.logger.info(f"Retired key: {key_id}")
        
        return True
    
    async def destroy_key(self, key_id: str) -> bool:
        """
        Permanently destroy an encryption key.
        
        WARNING: This operation is irreversible and will make any data
        encrypted with this key unrecoverable.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if destroyed successfully, False otherwise
        """
        stmt = select(EncryptionKeyModel).where(EncryptionKeyModel.id == key_id)
        result = await self.db.execute(stmt)
        db_key = result.scalar_one_or_none()
        
        if not db_key:
            return False
        
        # Only allow destruction of retired keys
        if db_key.status != "retired":
            raise ValueError("Only retired keys can be destroyed")
        
        # Delete from database
        await self.db.delete(db_key)
        await self.db.commit()
        
        # Remove from cache
        if key_id in self._key_cache:
            del self._key_cache[key_id]
            del self._cache_timestamps[key_id]
        
        self.logger.warning(f"Destroyed key: {key_id}")
        
        return True
    
    async def cleanup_expired_keys(self) -> int:
        """
        Clean up expired keys by marking them as retired.
        
        Returns:
            Number of keys cleaned up
        """
        now = datetime.utcnow()
        
        # Find expired active keys
        stmt = select(EncryptionKeyModel).where(
            and_(
                EncryptionKeyModel.status == "active",
                EncryptionKeyModel.expires_at.isnot(None),
                EncryptionKeyModel.expires_at <= now
            )
        )
        
        result = await self.db.execute(stmt)
        expired_keys = list(result.scalars().all())
        
        # Mark as retired
        count = 0
        for key in expired_keys:
            key.status = "retired"
            key.updated_at = now
            count += 1
        
        if count > 0:
            await self.db.commit()
            self.logger.info(f"Cleaned up {count} expired keys")
        
        return count
    
    async def _store_key(self, key: EncryptionKey) -> None:
        """Store encryption key in database."""
        db_key = EncryptionKeyModel(
            id=key.id,
            algorithm=key.algorithm,
            key_data=key.key_bytes,
            status=key.status,
            created_at=key.created_at,
            expires_at=key.expires_at
        )
        
        self.db.add(db_key)
        await self.db.commit()
    
    def clear_cache(self) -> None:
        """Clear the key cache."""
        self._key_cache.clear()
        self._cache_timestamps.clear()
        self.logger.info("Key cache cleared")
    
    async def get_key_statistics(self) -> Dict[str, Any]:
        """
        Get key store statistics.
        
        Returns:
            Dictionary with key statistics
        """
        # Count keys by status
        status_counts = {}
        for status in ["active", "rotating", "retired"]:
            stmt = select(func.count(EncryptionKeyModel.id)).where(
                EncryptionKeyModel.status == status
            )
            result = await self.db.execute(stmt)
            status_counts[status] = result.scalar()
        
        # Count keys by algorithm
        algorithm_counts = {}
        stmt = select(
            EncryptionKeyModel.algorithm,
            func.count(EncryptionKeyModel.id).label('count')
        ).group_by(EncryptionKeyModel.algorithm)
        
        result = await self.db.execute(stmt)
        for row in result:
            algorithm_counts[row.algorithm] = row.count
        
        # Find oldest and newest keys
        oldest_stmt = select(EncryptionKeyModel).order_by(EncryptionKeyModel.created_at).limit(1)
        newest_stmt = select(EncryptionKeyModel).order_by(desc(EncryptionKeyModel.created_at)).limit(1)
        
        oldest_result = await self.db.execute(oldest_stmt)
        newest_result = await self.db.execute(newest_stmt)
        
        oldest_key = oldest_result.scalar_one_or_none()
        newest_key = newest_result.scalar_one_or_none()
        
        return {
            "total_keys": sum(status_counts.values()),
            "by_status": status_counts,
            "by_algorithm": algorithm_counts,
            "oldest_key": oldest_key.created_at.isoformat() if oldest_key else None,
            "newest_key": newest_key.created_at.isoformat() if newest_key else None,
            "cache_size": len(self._key_cache)
        }