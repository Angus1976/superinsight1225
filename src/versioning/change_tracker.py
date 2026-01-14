"""
Change Tracker.

Tracks all data changes with before/after snapshots:
- Change recording with diff computation
- Change history queries
- Entity timeline generation
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.models.versioning import ChangeRecord, ChangeType

logger = logging.getLogger(__name__)


class ChangeTracker:
    """
    Change Tracker for recording data modifications.
    
    Provides:
    - Automatic change recording with diff computation
    - Change history queries with filtering
    - Entity timeline generation
    """
    
    def __init__(self):
        self.db_manager = db_manager
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.db_manager.get_session()
    
    def _compute_diff(
        self,
        old_data: Optional[Dict[str, Any]],
        new_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute difference between old and new data.
        
        Returns:
            Dictionary with added, removed, and modified fields
        """
        diff = {
            "added": {},
            "removed": {},
            "modified": {}
        }
        
        old_data = old_data or {}
        new_data = new_data or {}
        
        old_keys = set(old_data.keys())
        new_keys = set(new_data.keys())
        
        # Added keys
        for key in new_keys - old_keys:
            diff["added"][key] = new_data[key]
        
        # Removed keys
        for key in old_keys - new_keys:
            diff["removed"][key] = old_data[key]
        
        # Modified keys
        for key in old_keys & new_keys:
            if old_data[key] != new_data[key]:
                diff["modified"][key] = {
                    "old": old_data[key],
                    "new": new_data[key]
                }
        
        return diff
    
    async def track_change(
        self,
        entity_type: str,
        entity_id: str,
        change_type: ChangeType,
        old_data: Optional[Dict[str, Any]],
        new_data: Optional[Dict[str, Any]],
        user_id: str,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChangeRecord:
        """
        Record a data change.
        
        Args:
            entity_type: Type of entity being changed
            entity_id: ID of the entity
            change_type: Type of change (create, update, delete)
            old_data: Data before the change
            new_data: Data after the change
            user_id: User making the change
            tenant_id: Tenant ID for isolation
            metadata: Additional metadata
            
        Returns:
            Created ChangeRecord
        """
        # Compute diff if both old and new data exist
        diff = None
        if old_data is not None and new_data is not None:
            diff = self._compute_diff(old_data, new_data)
        elif change_type == ChangeType.CREATE and new_data:
            diff = {"added": new_data, "removed": {}, "modified": {}}
        elif change_type == ChangeType.DELETE and old_data:
            diff = {"added": {}, "removed": old_data, "modified": {}}
        
        with self.get_session() as session:
            record = ChangeRecord(
                entity_type=entity_type,
                entity_id=entity_id,
                change_type=change_type,
                old_snapshot=old_data,
                new_snapshot=new_data,
                diff=diff,
                user_id=user_id,
                metadata=metadata or {},
                tenant_id=tenant_id,
            )
            
            session.add(record)
            session.commit()
            session.refresh(record)
            
            logger.info(
                f"Tracked {change_type.value} change for {entity_type}/{entity_id}"
            )
            
            return record
    
    def track_change_sync(
        self,
        entity_type: str,
        entity_id: str,
        change_type: ChangeType,
        old_data: Optional[Dict[str, Any]],
        new_data: Optional[Dict[str, Any]],
        user_id: str,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChangeRecord:
        """Synchronous version of track_change."""
        diff = None
        if old_data is not None and new_data is not None:
            diff = self._compute_diff(old_data, new_data)
        elif change_type == ChangeType.CREATE and new_data:
            diff = {"added": new_data, "removed": {}, "modified": {}}
        elif change_type == ChangeType.DELETE and old_data:
            diff = {"added": {}, "removed": old_data, "modified": {}}
        
        with self.get_session() as session:
            record = ChangeRecord(
                entity_type=entity_type,
                entity_id=entity_id,
                change_type=change_type,
                old_snapshot=old_data,
                new_snapshot=new_data,
                diff=diff,
                user_id=user_id,
                metadata=metadata or {},
                tenant_id=tenant_id,
            )
            
            session.add(record)
            session.commit()
            session.refresh(record)
            
            return record
    
    def get_changes(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        change_type: Optional[ChangeType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ChangeRecord]:
        """
        Query change history with filters.
        
        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            user_id: Filter by user
            change_type: Filter by change type
            start_time: Filter by start time
            end_time: Filter by end time
            tenant_id: Tenant ID for isolation
            limit: Maximum records to return
            offset: Offset for pagination
            
        Returns:
            List of ChangeRecord objects
        """
        with self.get_session() as session:
            stmt = select(ChangeRecord)
            
            conditions = []
            
            if entity_type:
                conditions.append(ChangeRecord.entity_type == entity_type)
            if entity_id:
                conditions.append(ChangeRecord.entity_id == entity_id)
            if user_id:
                conditions.append(ChangeRecord.user_id == user_id)
            if change_type:
                conditions.append(ChangeRecord.change_type == change_type)
            if start_time:
                conditions.append(ChangeRecord.created_at >= start_time)
            if end_time:
                conditions.append(ChangeRecord.created_at <= end_time)
            if tenant_id:
                conditions.append(ChangeRecord.tenant_id == tenant_id)
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            stmt = stmt.order_by(ChangeRecord.created_at.desc())
            stmt = stmt.offset(offset).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
    
    def get_entity_timeline(
        self,
        entity_type: str,
        entity_id: str,
        tenant_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get complete change timeline for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            tenant_id: Tenant ID for isolation
            limit: Maximum records to return
            
        Returns:
            List of timeline entries with change details
        """
        changes = self.get_changes(
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=tenant_id,
            limit=limit
        )
        
        timeline = []
        for change in changes:
            entry = {
                "id": str(change.id),
                "timestamp": change.created_at.isoformat() if change.created_at else None,
                "change_type": change.change_type.value if change.change_type else None,
                "user_id": change.user_id,
                "summary": self._generate_change_summary(change),
                "diff": change.diff,
                "metadata": change.metadata,
            }
            timeline.append(entry)
        
        return timeline
    
    def _generate_change_summary(self, change: ChangeRecord) -> str:
        """Generate human-readable summary of a change."""
        if change.change_type == ChangeType.CREATE:
            return f"Created {change.entity_type}"
        elif change.change_type == ChangeType.DELETE:
            return f"Deleted {change.entity_type}"
        elif change.change_type == ChangeType.UPDATE:
            if change.diff:
                added = len(change.diff.get("added", {}))
                removed = len(change.diff.get("removed", {}))
                modified = len(change.diff.get("modified", {}))
                parts = []
                if added:
                    parts.append(f"{added} added")
                if removed:
                    parts.append(f"{removed} removed")
                if modified:
                    parts.append(f"{modified} modified")
                return f"Updated {change.entity_type}: {', '.join(parts)}"
            return f"Updated {change.entity_type}"
        return f"Changed {change.entity_type}"
    
    def get_change_statistics(
        self,
        entity_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get change statistics."""
        with self.get_session() as session:
            conditions = []
            
            if entity_type:
                conditions.append(ChangeRecord.entity_type == entity_type)
            if tenant_id:
                conditions.append(ChangeRecord.tenant_id == tenant_id)
            if start_time:
                conditions.append(ChangeRecord.created_at >= start_time)
            if end_time:
                conditions.append(ChangeRecord.created_at <= end_time)
            
            # Total count
            total_stmt = select(func.count(ChangeRecord.id))
            if conditions:
                total_stmt = total_stmt.where(and_(*conditions))
            total = session.execute(total_stmt).scalar() or 0
            
            # By change type
            type_stmt = select(
                ChangeRecord.change_type,
                func.count(ChangeRecord.id)
            ).group_by(ChangeRecord.change_type)
            if conditions:
                type_stmt = type_stmt.where(and_(*conditions))
            type_results = session.execute(type_stmt).all()
            by_type = {
                t.value if t else "unknown": c 
                for t, c in type_results
            }
            
            # By entity type
            entity_stmt = select(
                ChangeRecord.entity_type,
                func.count(ChangeRecord.id)
            ).group_by(ChangeRecord.entity_type)
            if conditions:
                entity_stmt = entity_stmt.where(and_(*conditions))
            entity_results = session.execute(entity_stmt).all()
            by_entity = {t: c for t, c in entity_results}
            
            return {
                "total_changes": total,
                "by_change_type": by_type,
                "by_entity_type": by_entity,
                "generated_at": datetime.utcnow().isoformat(),
            }


# Global instance
change_tracker = ChangeTracker()
