"""
Version Manager.

Provides comprehensive version control operations:
- Semantic versioning (major.minor.patch)
- Version creation and retrieval
- Version history and rollback
- Tag and branch management
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from src.database.connection import db_manager

logger = logging.getLogger(__name__)


class VersionType(str, Enum):
    """Version type for semantic versioning."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class VersionManager:
    """
    Version Manager for data version control.
    
    Supports:
    - Semantic versioning (major.minor.patch)
    - Version creation with automatic numbering
    - Version history and retrieval
    - Version rollback
    - Tag management
    """
    
    def __init__(self):
        self.db_manager = db_manager
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.db_manager.get_session()
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate SHA-256 checksum of data."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _calculate_size(self, data: Dict[str, Any]) -> int:
        """Calculate size of data in bytes."""
        return len(json.dumps(data, default=str).encode())
    
    def _calculate_next_version(
        self,
        current_version: str,
        version_type: VersionType
    ) -> str:
        """
        Calculate next semantic version.
        
        Args:
            current_version: Current version string (e.g., "1.2.3")
            version_type: Type of version bump
            
        Returns:
            New version string
        """
        try:
            parts = current_version.split('.')
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
        except (ValueError, IndexError):
            major, minor, patch = 0, 0, 0
        
        if version_type == VersionType.MAJOR:
            return f"{major + 1}.0.0"
        elif version_type == VersionType.MINOR:
            return f"{major}.{minor + 1}.0"
        else:  # PATCH
            return f"{major}.{minor}.{patch + 1}"
    
    async def create_version(
        self,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any],
        message: str,
        user_id: str,
        version_type: VersionType = VersionType.PATCH,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new version for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            data: Version data
            message: Version message/description
            user_id: User creating the version
            version_type: Type of version bump
            tenant_id: Tenant ID for isolation
            metadata: Additional metadata
            
        Returns:
            Created version dictionary
        """
        from src.models.versioning import DataVersion, VersionStatus
        from src.models.versioning import VersionType as ModelVersionType
        
        with self.get_session() as session:
            # Get current version
            current = await self._get_current_version(
                session, entity_type, entity_id, tenant_id
            )
            
            # Calculate new version
            current_ver = current.version if current else "0.0.0"
            new_version = self._calculate_next_version(current_ver, version_type)
            version_number = (current.version_number + 1) if current else 1
            
            # Calculate checksum and size
            checksum = self._calculate_checksum(data)
            data_size = self._calculate_size(data)
            
            # Create version record
            version = DataVersion(
                entity_type=entity_type,
                entity_id=entity_id,
                version=new_version,
                version_number=version_number,
                version_type=ModelVersionType.FULL,
                status=VersionStatus.ACTIVE,
                data=data,
                version_data=data,
                message=message,
                checksum=checksum,
                data_size_bytes=data_size,
                version_metadata=metadata or {},
                tenant_id=tenant_id,
                created_by=user_id,
                parent_version_id=current.id if current else None,
            )
            
            session.add(version)
            session.commit()
            session.refresh(version)
            
            logger.info(
                f"Created version {new_version} for {entity_type}/{entity_id}"
            )
            
            return version.to_dict()
    
    async def _get_current_version(
        self,
        session: Session,
        entity_type: str,
        entity_id: str,
        tenant_id: Optional[str] = None
    ):
        """Get the current (latest) version for an entity."""
        from src.models.versioning import DataVersion, VersionStatus
        
        stmt = select(DataVersion).where(
            DataVersion.entity_type == entity_type,
            DataVersion.entity_id == entity_id,
            DataVersion.status == VersionStatus.ACTIVE
        )
        
        if tenant_id:
            stmt = stmt.where(DataVersion.tenant_id == tenant_id)
        
        stmt = stmt.order_by(DataVersion.version_number.desc()).limit(1)
        
        result = session.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_version(
        self,
        entity_type: str,
        entity_id: str,
        version: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a specific version by version string."""
        from src.models.versioning import DataVersion
        
        with self.get_session() as session:
            stmt = select(DataVersion).where(
                DataVersion.entity_type == entity_type,
                DataVersion.entity_id == entity_id,
                DataVersion.version == version
            )
            
            if tenant_id:
                stmt = stmt.where(DataVersion.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            version_obj = result.scalar_one_or_none()
            
            return version_obj.to_dict() if version_obj else None
    
    def get_version_history(
        self,
        entity_type: str,
        entity_id: str,
        tenant_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get version history for an entity."""
        from src.models.versioning import DataVersion, VersionStatus
        
        with self.get_session() as session:
            stmt = select(DataVersion).where(
                DataVersion.entity_type == entity_type,
                DataVersion.entity_id == entity_id,
                DataVersion.status == VersionStatus.ACTIVE
            )
            
            if tenant_id:
                stmt = stmt.where(DataVersion.tenant_id == tenant_id)
            
            stmt = stmt.order_by(DataVersion.version_number.desc()).limit(limit)
            
            result = session.execute(stmt)
            versions = result.scalars().all()
            
            return [v.to_dict() for v in versions]
    
    async def add_tag(
        self,
        version_id: str,
        tag: str,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a tag to a version."""
        from src.models.versioning import DataVersion, DataVersionTag
        
        with self.get_session() as session:
            # Get version
            stmt = select(DataVersion).where(DataVersion.id == UUID(version_id))
            if tenant_id:
                stmt = stmt.where(DataVersion.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            version = result.scalar_one_or_none()
            
            if not version:
                raise ValueError(f"Version {version_id} not found")
            
            # Add tag to version's tags array
            if version.tags is None:
                version.tags = []
            if tag not in version.tags:
                version.tags = version.tags + [tag]
            
            # Also create tag record
            tag_record = DataVersionTag(
                version_id=version.id,
                tag_name=tag,
                tenant_id=tenant_id,
                created_by=user_id,
            )
            session.add(tag_record)
            
            session.commit()
            session.refresh(version)
            
            logger.info(f"Added tag '{tag}' to version {version_id}")
            
            return version.to_dict()
    
    async def rollback(
        self,
        entity_type: str,
        entity_id: str,
        target_version: str,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rollback to a specific version.
        
        Creates a new version with the data from the target version.
        """
        # Get target version data
        target = self.get_version(entity_type, entity_id, target_version, tenant_id)
        
        if not target:
            raise ValueError(f"Target version {target_version} not found")
        
        # Get the actual data from the version
        from src.models.versioning import DataVersion
        
        with self.get_session() as session:
            stmt = select(DataVersion).where(
                DataVersion.entity_type == entity_type,
                DataVersion.entity_id == entity_id,
                DataVersion.version == target_version
            )
            if tenant_id:
                stmt = stmt.where(DataVersion.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            target_obj = result.scalar_one_or_none()
            
            if not target_obj:
                raise ValueError(f"Target version {target_version} not found")
            
            data = target_obj.data or target_obj.version_data or {}
        
        # Create new version with target's data
        return await self.create_version(
            entity_type=entity_type,
            entity_id=entity_id,
            data=data,
            message=f"Rollback to version {target_version}",
            user_id=user_id,
            version_type=VersionType.PATCH,
            tenant_id=tenant_id,
            metadata={"rollback_from": target_version}
        )


# Global instance
version_manager = VersionManager()
