"""
Version Control Manager.

Provides high-level version control operations:
- Version creation with automatic delta calculation
- Version retrieval and history
- Rollback support
- Branch management
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.database.cache_service import get_cache_service
from src.version.models import (
    DataVersion, DataVersionTag, DataVersionBranch,
    VersionStatus, VersionType
)

logger = logging.getLogger(__name__)


class DeltaCalculator:
    """Calculates differences between version data."""
    
    @staticmethod
    def calculate_delta(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate delta between two data versions.
        
        Returns a delta object with added, removed, and modified fields.
        """
        delta = {
            "added": {},
            "removed": {},
            "modified": {},
        }
        
        old_keys = set(old_data.keys()) if old_data else set()
        new_keys = set(new_data.keys()) if new_data else set()
        
        # Added keys
        for key in new_keys - old_keys:
            delta["added"][key] = new_data[key]

        # Removed keys
        for key in old_keys - new_keys:
            delta["removed"][key] = old_data[key]
        
        # Modified keys
        for key in old_keys & new_keys:
            if old_data[key] != new_data[key]:
                delta["modified"][key] = {
                    "old": old_data[key],
                    "new": new_data[key]
                }
        
        return delta
    
    @staticmethod
    def apply_delta(base_data: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        """Apply delta to base data to reconstruct version."""
        result = dict(base_data) if base_data else {}
        
        # Apply removals
        for key in delta.get("removed", {}):
            result.pop(key, None)
        
        # Apply additions
        for key, value in delta.get("added", {}).items():
            result[key] = value
        
        # Apply modifications
        for key, change in delta.get("modified", {}).items():
            result[key] = change.get("new")
        
        return result


class VersionControlManager:
    """
    High-level version control manager.
    
    Provides comprehensive version management with:
    - Automatic versioning on data changes
    - Delta-based storage optimization
    - Branch and tag support
    - Multi-tenant isolation
    """
    
    def __init__(self):
        self.db_manager = db_manager
        self.cache_service = get_cache_service()
        self.delta_calculator = DeltaCalculator()
    
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
    
    async def create_version(
        self,
        entity_type: str,
        entity_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        workspace_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        comment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        use_delta: bool = True
    ) -> DataVersion:
        """
        Create a new version for an entity.
        
        Args:
            entity_type: Type of entity (task, annotation, dataset, etc.)
            entity_id: ID of the entity
            data: Version data to store
            user_id: User creating the version
            tenant_id: Tenant ID for isolation
            workspace_id: Workspace ID
            branch_id: Branch ID (optional)
            comment: Version comment
            metadata: Additional metadata
            use_delta: Whether to use delta storage
            
        Returns:
            Created DataVersion instance
        """
        with self.get_session() as session:
            # Get latest version for this entity
            latest_version = await self._get_latest_version(
                session, entity_type, entity_id, branch_id, tenant_id
            )
            
            # Calculate version number
            version_number = (latest_version.version_number + 1) if latest_version else 1
            
            # Calculate checksum and size
            checksum = self._calculate_checksum(data)
            data_size = self._calculate_size(data)

            # Determine version type and calculate delta
            version_type = VersionType.FULL
            delta_data = None
            parent_version_id = None
            
            if use_delta and latest_version:
                delta_data = self.delta_calculator.calculate_delta(
                    latest_version.version_data, data
                )
                # Only use delta if it's smaller than full data
                delta_size = self._calculate_size(delta_data)
                if delta_size < data_size * 0.7:  # 30% savings threshold
                    version_type = VersionType.DELTA
                    parent_version_id = latest_version.id
                else:
                    delta_data = None
            
            # Create version record
            new_version = DataVersion(
                entity_type=entity_type,
                entity_id=entity_id,
                version_number=version_number,
                version_type=version_type,
                status=VersionStatus.ACTIVE,
                parent_version_id=parent_version_id,
                branch_id=branch_id,
                version_data=data,
                delta_data=delta_data,
                checksum=checksum,
                data_size_bytes=data_size,
                version_metadata=metadata or {},
                comment=comment,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                created_by=user_id,
            )
            
            session.add(new_version)
            session.commit()
            session.refresh(new_version)
            
            # Invalidate cache
            self._invalidate_cache(entity_type, entity_id, tenant_id)
            
            logger.info(
                f"Created version {version_number} for {entity_type}/{entity_id} "
                f"(type={version_type.value}, size={data_size})"
            )
            
            return new_version

    async def _get_latest_version(
        self,
        session: Session,
        entity_type: str,
        entity_id: UUID,
        branch_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None
    ) -> Optional[DataVersion]:
        """Get the latest version for an entity."""
        stmt = select(DataVersion).where(
            DataVersion.entity_type == entity_type,
            DataVersion.entity_id == entity_id,
            DataVersion.status == VersionStatus.ACTIVE
        )
        
        if branch_id:
            stmt = stmt.where(DataVersion.branch_id == branch_id)
        else:
            stmt = stmt.where(DataVersion.branch_id.is_(None))
        
        if tenant_id:
            stmt = stmt.where(DataVersion.tenant_id == tenant_id)
        
        stmt = stmt.order_by(DataVersion.version_number.desc()).limit(1)
        
        result = session.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_version(
        self,
        version_id: UUID,
        tenant_id: Optional[str] = None
    ) -> Optional[DataVersion]:
        """Get a specific version by ID."""
        with self.get_session() as session:
            stmt = select(DataVersion).where(DataVersion.id == version_id)
            if tenant_id:
                stmt = stmt.where(DataVersion.tenant_id == tenant_id)
            result = session.execute(stmt)
            return result.scalar_one_or_none()
    
    def get_version_by_number(
        self,
        entity_type: str,
        entity_id: UUID,
        version_number: int,
        branch_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None
    ) -> Optional[DataVersion]:
        """Get a specific version by version number."""
        with self.get_session() as session:
            stmt = select(DataVersion).where(
                DataVersion.entity_type == entity_type,
                DataVersion.entity_id == entity_id,
                DataVersion.version_number == version_number
            )
            
            if branch_id:
                stmt = stmt.where(DataVersion.branch_id == branch_id)
            if tenant_id:
                stmt = stmt.where(DataVersion.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            return result.scalar_one_or_none()

    def get_version_history(
        self,
        entity_type: str,
        entity_id: UUID,
        branch_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False
    ) -> List[DataVersion]:
        """Get version history for an entity."""
        with self.get_session() as session:
            stmt = select(DataVersion).where(
                DataVersion.entity_type == entity_type,
                DataVersion.entity_id == entity_id
            )
            
            if not include_archived:
                stmt = stmt.where(DataVersion.status == VersionStatus.ACTIVE)
            
            if branch_id:
                stmt = stmt.where(DataVersion.branch_id == branch_id)
            if tenant_id:
                stmt = stmt.where(DataVersion.tenant_id == tenant_id)
            
            stmt = stmt.order_by(DataVersion.version_number.desc())
            stmt = stmt.offset(offset).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
    
    def get_latest_version(
        self,
        entity_type: str,
        entity_id: UUID,
        branch_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None
    ) -> Optional[DataVersion]:
        """Get the latest version for an entity."""
        with self.get_session() as session:
            return self._get_latest_version_sync(
                session, entity_type, entity_id, branch_id, tenant_id
            )
    
    def _get_latest_version_sync(
        self,
        session: Session,
        entity_type: str,
        entity_id: UUID,
        branch_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None
    ) -> Optional[DataVersion]:
        """Synchronous version of _get_latest_version."""
        stmt = select(DataVersion).where(
            DataVersion.entity_type == entity_type,
            DataVersion.entity_id == entity_id,
            DataVersion.status == VersionStatus.ACTIVE
        )
        
        if branch_id:
            stmt = stmt.where(DataVersion.branch_id == branch_id)
        else:
            stmt = stmt.where(DataVersion.branch_id.is_(None))
        
        if tenant_id:
            stmt = stmt.where(DataVersion.tenant_id == tenant_id)
        
        stmt = stmt.order_by(DataVersion.version_number.desc()).limit(1)
        
        result = session.execute(stmt)
        return result.scalar_one_or_none()

    def reconstruct_version_data(self, version: DataVersion) -> Dict[str, Any]:
        """
        Reconstruct full version data from delta chain.
        
        For delta versions, walks up the parent chain to reconstruct full data.
        """
        if version.version_type == VersionType.FULL or not version.parent_version_id:
            return version.version_data
        
        # Build delta chain
        delta_chain = []
        current = version
        
        with self.get_session() as session:
            while current.version_type == VersionType.DELTA and current.parent_version_id:
                delta_chain.append(current.delta_data)
                stmt = select(DataVersion).where(DataVersion.id == current.parent_version_id)
                result = session.execute(stmt)
                current = result.scalar_one_or_none()
                if not current:
                    break
            
            # Start with base version data
            base_data = current.version_data if current else {}
            
            # Apply deltas in reverse order
            result_data = base_data
            for delta in reversed(delta_chain):
                if delta:
                    result_data = self.delta_calculator.apply_delta(result_data, delta)
            
            return result_data
    
    def create_tag(
        self,
        version_id: UUID,
        tag_name: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> DataVersionTag:
        """Create a tag for a version."""
        with self.get_session() as session:
            tag = DataVersionTag(
                version_id=version_id,
                tag_name=tag_name,
                description=description,
                tenant_id=tenant_id,
                created_by=user_id,
            )
            session.add(tag)
            session.commit()
            session.refresh(tag)
            
            logger.info(f"Created tag '{tag_name}' for version {version_id}")
            return tag

    def get_version_by_tag(
        self,
        tag_name: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None
    ) -> Optional[DataVersion]:
        """Get version by tag name."""
        with self.get_session() as session:
            stmt = select(DataVersion).join(DataVersionTag).where(
                DataVersionTag.tag_name == tag_name
            )
            
            if entity_type:
                stmt = stmt.where(DataVersion.entity_type == entity_type)
            if entity_id:
                stmt = stmt.where(DataVersion.entity_id == entity_id)
            if tenant_id:
                stmt = stmt.where(DataVersionTag.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            return result.scalar_one_or_none()
    
    def create_branch(
        self,
        entity_type: str,
        entity_id: UUID,
        branch_name: str,
        base_version_id: Optional[UUID] = None,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> DataVersionBranch:
        """Create a new branch for an entity."""
        with self.get_session() as session:
            branch = DataVersionBranch(
                name=branch_name,
                description=description,
                entity_type=entity_type,
                entity_id=entity_id,
                base_version_id=base_version_id,
                tenant_id=tenant_id,
                created_by=user_id,
            )
            session.add(branch)
            session.commit()
            session.refresh(branch)
            
            logger.info(f"Created branch '{branch_name}' for {entity_type}/{entity_id}")
            return branch
    
    def get_branches(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: Optional[str] = None
    ) -> List[DataVersionBranch]:
        """Get all branches for an entity."""
        with self.get_session() as session:
            stmt = select(DataVersionBranch).where(
                DataVersionBranch.entity_type == entity_type,
                DataVersionBranch.entity_id == entity_id
            )
            if tenant_id:
                stmt = stmt.where(DataVersionBranch.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            return list(result.scalars().all())

    def archive_version(
        self,
        version_id: UUID,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Archive a version (soft delete)."""
        with self.get_session() as session:
            stmt = select(DataVersion).where(DataVersion.id == version_id)
            if tenant_id:
                stmt = stmt.where(DataVersion.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            version = result.scalar_one_or_none()
            
            if version:
                version.status = VersionStatus.ARCHIVED
                session.commit()
                
                self._invalidate_cache(
                    version.entity_type, version.entity_id, tenant_id
                )
                logger.info(f"Archived version {version_id}")
                return True
            return False
    
    def get_version_count(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: Optional[str] = None
    ) -> int:
        """Get total version count for an entity."""
        with self.get_session() as session:
            stmt = select(func.count(DataVersion.id)).where(
                DataVersion.entity_type == entity_type,
                DataVersion.entity_id == entity_id,
                DataVersion.status == VersionStatus.ACTIVE
            )
            if tenant_id:
                stmt = stmt.where(DataVersion.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            return result.scalar() or 0
    
    def _invalidate_cache(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: Optional[str] = None
    ):
        """Invalidate version cache for an entity."""
        cache_key = f"version:{entity_type}:{entity_id}"
        if tenant_id:
            cache_key = f"{cache_key}:{tenant_id}"
        
        try:
            self.cache_service.delete(cache_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")


# Global instance
version_manager = VersionControlManager()
