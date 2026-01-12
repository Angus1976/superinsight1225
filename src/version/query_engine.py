"""
Version Query Engine.

Provides efficient version querying and comparison:
- Time-point queries
- Version comparison
- Diff calculation
- Search and filtering
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from dataclasses import dataclass, field

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.database.cache_service import get_cache_service, get_query_cache
from src.version.models import DataVersion, DataVersionTag, VersionStatus

logger = logging.getLogger(__name__)


@dataclass
class VersionComparison:
    """Result of comparing two versions."""
    version1: DataVersion
    version2: DataVersion
    differences: Dict[str, Any]
    similarity_score: float
    added_fields: List[str] = field(default_factory=list)
    removed_fields: List[str] = field(default_factory=list)
    modified_fields: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version1": self.version1.to_dict() if self.version1 else None,
            "version2": self.version2.to_dict() if self.version2 else None,
            "differences": self.differences,
            "similarity_score": self.similarity_score,
            "added_fields": self.added_fields,
            "removed_fields": self.removed_fields,
            "modified_fields": self.modified_fields,
        }


class VersionQueryEngine:
    """
    High-performance version query engine.
    
    Provides:
    - Time-point queries (get version at specific time)
    - Version comparison and diff
    - Search across versions
    - Caching for frequently accessed versions
    """
    
    def __init__(self):
        self.db_manager = db_manager
        self.cache_service = get_cache_service()
        self.query_cache = get_query_cache()
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.db_manager.get_session()
    
    def query_version_at_time(
        self,
        entity_type: str,
        entity_id: UUID,
        timestamp: datetime,
        tenant_id: Optional[str] = None
    ) -> Optional[DataVersion]:
        """
        Get the version that was active at a specific point in time.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            timestamp: Point in time to query
            tenant_id: Tenant ID for isolation
            
        Returns:
            Version that was active at the specified time
        """
        # Check cache first
        cache_key = f"version_at:{entity_type}:{entity_id}:{timestamp.isoformat()}"
        if tenant_id:
            cache_key = f"{cache_key}:{tenant_id}"
        
        cached = self.query_cache.get_query_result(cache_key)
        if cached is not None:
            return cached
        
        with self.get_session() as session:
            stmt = select(DataVersion).where(
                DataVersion.entity_type == entity_type,
                DataVersion.entity_id == entity_id,
                DataVersion.created_at <= timestamp,
                DataVersion.status == VersionStatus.ACTIVE
            )
            
            if tenant_id:
                stmt = stmt.where(DataVersion.tenant_id == tenant_id)
            
            stmt = stmt.order_by(DataVersion.created_at.desc()).limit(1)
            
            result = session.execute(stmt)
            version = result.scalar_one_or_none()
            
            # Cache for 1 hour
            if version:
                self.query_cache.set_query_result(cache_key, version, ttl=3600)
            
            return version

    def compare_versions(
        self,
        version1_id: UUID,
        version2_id: UUID,
        tenant_id: Optional[str] = None
    ) -> Optional[VersionComparison]:
        """
        Compare two versions and calculate differences.
        
        Args:
            version1_id: First version ID
            version2_id: Second version ID
            tenant_id: Tenant ID for isolation
            
        Returns:
            VersionComparison with detailed differences
        """
        with self.get_session() as session:
            # Get both versions
            stmt1 = select(DataVersion).where(DataVersion.id == version1_id)
            stmt2 = select(DataVersion).where(DataVersion.id == version2_id)
            
            if tenant_id:
                stmt1 = stmt1.where(DataVersion.tenant_id == tenant_id)
                stmt2 = stmt2.where(DataVersion.tenant_id == tenant_id)
            
            version1 = session.execute(stmt1).scalar_one_or_none()
            version2 = session.execute(stmt2).scalar_one_or_none()
            
            if not version1 or not version2:
                return None
            
            # Calculate differences
            differences = self._calculate_differences(
                version1.version_data, version2.version_data
            )
            
            # Calculate similarity score
            similarity = self._calculate_similarity(
                version1.version_data, version2.version_data
            )
            
            return VersionComparison(
                version1=version1,
                version2=version2,
                differences=differences,
                similarity_score=similarity,
                added_fields=list(differences.get("added", {}).keys()),
                removed_fields=list(differences.get("removed", {}).keys()),
                modified_fields=list(differences.get("modified", {}).keys()),
            )
    
    def _calculate_differences(
        self,
        data1: Dict[str, Any],
        data2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate detailed differences between two data sets."""
        differences = {
            "added": {},
            "removed": {},
            "modified": {},
        }
        
        keys1 = set(data1.keys()) if data1 else set()
        keys2 = set(data2.keys()) if data2 else set()
        
        # Added in data2
        for key in keys2 - keys1:
            differences["added"][key] = data2[key]
        
        # Removed from data1
        for key in keys1 - keys2:
            differences["removed"][key] = data1[key]
        
        # Modified
        for key in keys1 & keys2:
            if data1[key] != data2[key]:
                differences["modified"][key] = {
                    "old": data1[key],
                    "new": data2[key]
                }
        
        return differences

    def _calculate_similarity(
        self,
        data1: Dict[str, Any],
        data2: Dict[str, Any]
    ) -> float:
        """Calculate similarity score between two data sets (0.0 to 1.0)."""
        if not data1 and not data2:
            return 1.0
        if not data1 or not data2:
            return 0.0
        
        keys1 = set(data1.keys())
        keys2 = set(data2.keys())
        
        all_keys = keys1 | keys2
        if not all_keys:
            return 1.0
        
        matching = 0
        for key in all_keys:
            if key in keys1 and key in keys2:
                if data1[key] == data2[key]:
                    matching += 1
                else:
                    matching += 0.5  # Partial match for same key
        
        return matching / len(all_keys)
    
    def search_versions(
        self,
        entity_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        created_by: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        comment_contains: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DataVersion]:
        """
        Search versions with various filters.
        
        Args:
            entity_type: Filter by entity type
            tenant_id: Filter by tenant
            created_by: Filter by creator
            start_date: Filter by creation date (from)
            end_date: Filter by creation date (to)
            comment_contains: Search in comments
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of matching versions
        """
        with self.get_session() as session:
            stmt = select(DataVersion).where(
                DataVersion.status == VersionStatus.ACTIVE
            )
            
            if entity_type:
                stmt = stmt.where(DataVersion.entity_type == entity_type)
            if tenant_id:
                stmt = stmt.where(DataVersion.tenant_id == tenant_id)
            if created_by:
                stmt = stmt.where(DataVersion.created_by == created_by)
            if start_date:
                stmt = stmt.where(DataVersion.created_at >= start_date)
            if end_date:
                stmt = stmt.where(DataVersion.created_at <= end_date)
            if comment_contains:
                stmt = stmt.where(
                    DataVersion.comment.ilike(f"%{comment_contains}%")
                )
            
            stmt = stmt.order_by(DataVersion.created_at.desc())
            stmt = stmt.offset(offset).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())

    def get_version_statistics(
        self,
        entity_type: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get version statistics."""
        with self.get_session() as session:
            # Base query
            base_filter = [DataVersion.status == VersionStatus.ACTIVE]
            if entity_type:
                base_filter.append(DataVersion.entity_type == entity_type)
            if tenant_id:
                base_filter.append(DataVersion.tenant_id == tenant_id)
            
            # Total versions
            total_stmt = select(func.count(DataVersion.id)).where(*base_filter)
            total_count = session.execute(total_stmt).scalar() or 0
            
            # Total size
            size_stmt = select(func.sum(DataVersion.data_size_bytes)).where(*base_filter)
            total_size = session.execute(size_stmt).scalar() or 0
            
            # Versions by type
            type_stmt = select(
                DataVersion.version_type,
                func.count(DataVersion.id)
            ).where(*base_filter).group_by(DataVersion.version_type)
            type_results = session.execute(type_stmt).all()
            versions_by_type = {
                str(t.value) if t else "unknown": c 
                for t, c in type_results
            }
            
            # Versions by entity type
            entity_stmt = select(
                DataVersion.entity_type,
                func.count(DataVersion.id)
            ).where(*base_filter).group_by(DataVersion.entity_type)
            entity_results = session.execute(entity_stmt).all()
            versions_by_entity = {e: c for e, c in entity_results}
            
            # Recent activity (last 24 hours)
            from datetime import timedelta
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_stmt = select(func.count(DataVersion.id)).where(
                *base_filter,
                DataVersion.created_at >= recent_cutoff
            )
            recent_count = session.execute(recent_stmt).scalar() or 0
            
            return {
                "total_versions": total_count,
                "total_size_bytes": total_size,
                "versions_by_type": versions_by_type,
                "versions_by_entity_type": versions_by_entity,
                "recent_versions_24h": recent_count,
                "generated_at": datetime.utcnow().isoformat(),
            }
    
    def get_entity_version_summary(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get version summary for a specific entity."""
        with self.get_session() as session:
            base_filter = [
                DataVersion.entity_type == entity_type,
                DataVersion.entity_id == entity_id,
                DataVersion.status == VersionStatus.ACTIVE
            ]
            if tenant_id:
                base_filter.append(DataVersion.tenant_id == tenant_id)
            
            # Count and size
            stats_stmt = select(
                func.count(DataVersion.id),
                func.sum(DataVersion.data_size_bytes),
                func.min(DataVersion.created_at),
                func.max(DataVersion.created_at)
            ).where(*base_filter)
            
            result = session.execute(stats_stmt).one()
            count, total_size, first_created, last_created = result
            
            # Latest version
            latest_stmt = select(DataVersion).where(*base_filter).order_by(
                DataVersion.version_number.desc()
            ).limit(1)
            latest = session.execute(latest_stmt).scalar_one_or_none()
            
            return {
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "version_count": count or 0,
                "total_size_bytes": total_size or 0,
                "first_version_at": first_created.isoformat() if first_created else None,
                "latest_version_at": last_created.isoformat() if last_created else None,
                "latest_version_number": latest.version_number if latest else None,
                "latest_version_id": str(latest.id) if latest else None,
            }


# Global instance
version_query_engine = VersionQueryEngine()
