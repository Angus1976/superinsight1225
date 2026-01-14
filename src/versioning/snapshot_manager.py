"""
Snapshot Manager.

Manages data snapshots:
- Full and incremental snapshots
- Scheduled snapshot creation
- Snapshot restoration
- Retention policy enforcement
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from dataclasses import dataclass

from sqlalchemy import select, func, and_, delete
from sqlalchemy.orm import Session
from croniter import croniter

from src.database.connection import db_manager
from src.models.versioning import Snapshot, SnapshotSchedule, SnapshotType

logger = logging.getLogger(__name__)


@dataclass
class RestoreResult:
    """Result of snapshot restoration."""
    snapshot_id: str
    entity_type: str
    entity_id: str
    restored_at: datetime
    restored_by: Optional[str]
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "restored_at": self.restored_at.isoformat(),
            "restored_by": self.restored_by,
        }


@dataclass
class RetentionPolicy:
    """Snapshot retention policy."""
    max_age_days: int = 90
    max_count: int = 100
    keep_tagged: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_age_days": self.max_age_days,
            "max_count": self.max_count,
            "keep_tagged": self.keep_tagged,
        }


class SnapshotManager:
    """
    Snapshot Manager for data backup and recovery.
    
    Provides:
    - Full and incremental snapshot creation
    - Scheduled automatic snapshots
    - Snapshot restoration
    - Retention policy management
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
    
    def _compute_incremental(
        self,
        base_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute incremental diff from base to new data."""
        diff = {
            "added": {},
            "removed": {},
            "modified": {}
        }
        
        base_keys = set(base_data.keys()) if base_data else set()
        new_keys = set(new_data.keys()) if new_data else set()
        
        for key in new_keys - base_keys:
            diff["added"][key] = new_data[key]
        
        for key in base_keys - new_keys:
            diff["removed"][key] = base_data[key]
        
        for key in base_keys & new_keys:
            if base_data[key] != new_data[key]:
                diff["modified"][key] = {
                    "old": base_data[key],
                    "new": new_data[key]
                }
        
        return diff
    
    async def create_snapshot(
        self,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any],
        snapshot_type: SnapshotType = SnapshotType.FULL,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> Snapshot:
        """
        Create a snapshot of entity data.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            data: Data to snapshot
            snapshot_type: Full or incremental
            user_id: User creating snapshot
            tenant_id: Tenant ID for isolation
            metadata: Additional metadata
            expires_at: Expiration time
            
        Returns:
            Created Snapshot
        """
        with self.get_session() as session:
            snapshot_data = data
            parent_snapshot_id = None
            
            if snapshot_type == SnapshotType.INCREMENTAL:
                # Get latest snapshot for incremental
                latest = self._get_latest_snapshot(
                    session, entity_type, entity_id, tenant_id
                )
                if latest and latest.data:
                    snapshot_data = self._compute_incremental(latest.data, data)
                    parent_snapshot_id = latest.id
                else:
                    # No base snapshot, create full instead
                    snapshot_type = SnapshotType.FULL
            
            # Generate storage key
            storage_key = f"snapshots/{entity_type}/{entity_id}/{uuid4()}"
            
            # Calculate checksum and size
            checksum = self._calculate_checksum(snapshot_data)
            size_bytes = self._calculate_size(snapshot_data)
            
            snapshot = Snapshot(
                entity_type=entity_type,
                entity_id=entity_id,
                snapshot_type=snapshot_type,
                storage_key=storage_key,
                data=snapshot_data,
                size_bytes=size_bytes,
                checksum=checksum,
                parent_snapshot_id=parent_snapshot_id,
                metadata=metadata or {},
                tenant_id=tenant_id,
                created_by=user_id,
                expires_at=expires_at,
            )
            
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
            
            logger.info(
                f"Created {snapshot_type.value} snapshot for {entity_type}/{entity_id}"
            )
            
            return snapshot
    
    def create_snapshot_sync(
        self,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any],
        snapshot_type: SnapshotType = SnapshotType.FULL,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> Snapshot:
        """Synchronous version of create_snapshot."""
        with self.get_session() as session:
            snapshot_data = data
            parent_snapshot_id = None
            
            if snapshot_type == SnapshotType.INCREMENTAL:
                latest = self._get_latest_snapshot(
                    session, entity_type, entity_id, tenant_id
                )
                if latest and latest.data:
                    snapshot_data = self._compute_incremental(latest.data, data)
                    parent_snapshot_id = latest.id
                else:
                    snapshot_type = SnapshotType.FULL
            
            storage_key = f"snapshots/{entity_type}/{entity_id}/{uuid4()}"
            checksum = self._calculate_checksum(snapshot_data)
            size_bytes = self._calculate_size(snapshot_data)
            
            snapshot = Snapshot(
                entity_type=entity_type,
                entity_id=entity_id,
                snapshot_type=snapshot_type,
                storage_key=storage_key,
                data=snapshot_data,
                size_bytes=size_bytes,
                checksum=checksum,
                parent_snapshot_id=parent_snapshot_id,
                metadata=metadata or {},
                tenant_id=tenant_id,
                created_by=user_id,
                expires_at=expires_at,
            )
            
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
            
            return snapshot
    
    def _get_latest_snapshot(
        self,
        session: Session,
        entity_type: str,
        entity_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Snapshot]:
        """Get the latest snapshot for an entity."""
        stmt = select(Snapshot).where(
            Snapshot.entity_type == entity_type,
            Snapshot.entity_id == entity_id
        )
        
        if tenant_id:
            stmt = stmt.where(Snapshot.tenant_id == tenant_id)
        
        stmt = stmt.order_by(Snapshot.created_at.desc()).limit(1)
        
        result = session.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_snapshot(
        self,
        snapshot_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Snapshot]:
        """Get a snapshot by ID."""
        with self.get_session() as session:
            stmt = select(Snapshot).where(Snapshot.id == UUID(snapshot_id))
            
            if tenant_id:
                stmt = stmt.where(Snapshot.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            return result.scalar_one_or_none()
    
    def get_latest_snapshot(
        self,
        entity_type: str,
        entity_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Snapshot]:
        """Get the latest snapshot for an entity."""
        with self.get_session() as session:
            return self._get_latest_snapshot(
                session, entity_type, entity_id, tenant_id
            )
    
    def list_snapshots(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Snapshot]:
        """List snapshots with optional filters."""
        with self.get_session() as session:
            stmt = select(Snapshot)
            
            conditions = []
            if entity_type:
                conditions.append(Snapshot.entity_type == entity_type)
            if entity_id:
                conditions.append(Snapshot.entity_id == entity_id)
            if tenant_id:
                conditions.append(Snapshot.tenant_id == tenant_id)
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            stmt = stmt.order_by(Snapshot.created_at.desc())
            stmt = stmt.offset(offset).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
    
    def _rebuild_full_data(
        self,
        session: Session,
        snapshot: Snapshot
    ) -> Dict[str, Any]:
        """Rebuild full data from incremental snapshot chain."""
        if snapshot.snapshot_type == SnapshotType.FULL:
            return snapshot.data or {}
        
        # Build chain of incremental snapshots
        chain = [snapshot]
        current = snapshot
        
        while current.parent_snapshot_id:
            stmt = select(Snapshot).where(
                Snapshot.id == current.parent_snapshot_id
            )
            result = session.execute(stmt)
            parent = result.scalar_one_or_none()
            
            if not parent:
                break
            
            chain.append(parent)
            current = parent
            
            if parent.snapshot_type == SnapshotType.FULL:
                break
        
        # Start with base (last in chain)
        chain.reverse()
        base_data = chain[0].data or {}
        
        # Apply incremental changes
        for snap in chain[1:]:
            if snap.data:
                diff = snap.data
                # Apply additions
                for key, value in diff.get("added", {}).items():
                    base_data[key] = value
                # Apply removals
                for key in diff.get("removed", {}):
                    base_data.pop(key, None)
                # Apply modifications
                for key, change in diff.get("modified", {}).items():
                    base_data[key] = change.get("new")
        
        return base_data
    
    async def restore_from_snapshot(
        self,
        snapshot_id: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> RestoreResult:
        """
        Restore data from a snapshot.
        
        Args:
            snapshot_id: ID of snapshot to restore
            user_id: User performing restore
            tenant_id: Tenant ID for isolation
            
        Returns:
            RestoreResult with restored data
        """
        with self.get_session() as session:
            snapshot = self.get_snapshot(snapshot_id, tenant_id)
            
            if not snapshot:
                raise ValueError(f"Snapshot {snapshot_id} not found")
            
            # Rebuild full data if incremental
            data = self._rebuild_full_data(session, snapshot)
            
            logger.info(
                f"Restored snapshot {snapshot_id} for "
                f"{snapshot.entity_type}/{snapshot.entity_id}"
            )
            
            return RestoreResult(
                snapshot_id=str(snapshot.id),
                entity_type=snapshot.entity_type,
                entity_id=snapshot.entity_id,
                restored_at=datetime.utcnow(),
                restored_by=user_id,
                data=data
            )
    
    def restore_from_snapshot_sync(
        self,
        snapshot_id: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> RestoreResult:
        """Synchronous version of restore_from_snapshot."""
        with self.get_session() as session:
            snapshot = self.get_snapshot(snapshot_id, tenant_id)
            
            if not snapshot:
                raise ValueError(f"Snapshot {snapshot_id} not found")
            
            data = self._rebuild_full_data(session, snapshot)
            
            return RestoreResult(
                snapshot_id=str(snapshot.id),
                entity_type=snapshot.entity_type,
                entity_id=snapshot.entity_id,
                restored_at=datetime.utcnow(),
                restored_by=user_id,
                data=data
            )
    
    def delete_snapshot(
        self,
        snapshot_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Delete a snapshot."""
        with self.get_session() as session:
            stmt = select(Snapshot).where(Snapshot.id == UUID(snapshot_id))
            
            if tenant_id:
                stmt = stmt.where(Snapshot.tenant_id == tenant_id)
            
            result = session.execute(stmt)
            snapshot = result.scalar_one_or_none()
            
            if snapshot:
                session.delete(snapshot)
                session.commit()
                logger.info(f"Deleted snapshot {snapshot_id}")
                return True
            
            return False
    
    async def create_scheduled_snapshot(
        self,
        entity_type: str,
        entity_id: str,
        schedule: str,  # cron expression
        snapshot_type: SnapshotType = SnapshotType.FULL,
        retention_days: int = 90,
        max_snapshots: int = 100,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> SnapshotSchedule:
        """
        Create a scheduled snapshot configuration.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            schedule: Cron expression for schedule
            snapshot_type: Type of snapshots to create
            retention_days: Days to retain snapshots
            max_snapshots: Maximum snapshots to keep
            user_id: User creating schedule
            tenant_id: Tenant ID for isolation
            
        Returns:
            Created SnapshotSchedule
        """
        with self.get_session() as session:
            # Calculate next run time
            cron = croniter(schedule, datetime.utcnow())
            next_run = cron.get_next(datetime)
            
            schedule_obj = SnapshotSchedule(
                entity_type=entity_type,
                entity_id=entity_id,
                schedule=schedule,
                snapshot_type=snapshot_type,
                enabled=True,
                retention_days=retention_days,
                max_snapshots=max_snapshots,
                next_run_at=next_run,
                tenant_id=tenant_id,
                created_by=user_id,
            )
            
            session.add(schedule_obj)
            session.commit()
            session.refresh(schedule_obj)
            
            logger.info(
                f"Created snapshot schedule for {entity_type}/{entity_id}: {schedule}"
            )
            
            return schedule_obj
    
    def get_due_schedules(self) -> List[SnapshotSchedule]:
        """Get schedules that are due for execution."""
        with self.get_session() as session:
            stmt = select(SnapshotSchedule).where(
                SnapshotSchedule.enabled == True,
                SnapshotSchedule.next_run_at <= datetime.utcnow()
            )
            
            result = session.execute(stmt)
            return list(result.scalars().all())
    
    def update_schedule_after_run(
        self,
        schedule_id: str
    ) -> Optional[SnapshotSchedule]:
        """Update schedule after execution."""
        with self.get_session() as session:
            stmt = select(SnapshotSchedule).where(
                SnapshotSchedule.id == UUID(schedule_id)
            )
            result = session.execute(stmt)
            schedule = result.scalar_one_or_none()
            
            if schedule:
                schedule.last_run_at = datetime.utcnow()
                cron = croniter(schedule.schedule, datetime.utcnow())
                schedule.next_run_at = cron.get_next(datetime)
                session.commit()
                session.refresh(schedule)
            
            return schedule
    
    def apply_retention_policy(
        self,
        entity_type: str,
        entity_id: str,
        policy: RetentionPolicy,
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Apply retention policy to snapshots.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            policy: Retention policy to apply
            tenant_id: Tenant ID for isolation
            
        Returns:
            Number of snapshots deleted
        """
        deleted_count = 0
        
        with self.get_session() as session:
            # Get all snapshots for entity
            stmt = select(Snapshot).where(
                Snapshot.entity_type == entity_type,
                Snapshot.entity_id == entity_id
            )
            
            if tenant_id:
                stmt = stmt.where(Snapshot.tenant_id == tenant_id)
            
            stmt = stmt.order_by(Snapshot.created_at.desc())
            
            result = session.execute(stmt)
            snapshots = list(result.scalars().all())
            
            # Apply max age policy
            cutoff_date = datetime.utcnow() - timedelta(days=policy.max_age_days)
            
            for i, snapshot in enumerate(snapshots):
                should_delete = False
                
                # Check age
                if snapshot.created_at < cutoff_date:
                    should_delete = True
                
                # Check count (keep first max_count)
                if i >= policy.max_count:
                    should_delete = True
                
                # Check if expired
                if snapshot.expires_at and snapshot.expires_at < datetime.utcnow():
                    should_delete = True
                
                if should_delete:
                    session.delete(snapshot)
                    deleted_count += 1
            
            session.commit()
        
        if deleted_count > 0:
            logger.info(
                f"Deleted {deleted_count} snapshots for {entity_type}/{entity_id} "
                f"per retention policy"
            )
        
        return deleted_count
    
    def get_snapshot_statistics(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get snapshot statistics."""
        with self.get_session() as session:
            conditions = []
            if tenant_id:
                conditions.append(Snapshot.tenant_id == tenant_id)
            
            # Total count
            total_stmt = select(func.count(Snapshot.id))
            if conditions:
                total_stmt = total_stmt.where(and_(*conditions))
            total = session.execute(total_stmt).scalar() or 0
            
            # Total size
            size_stmt = select(func.sum(Snapshot.size_bytes))
            if conditions:
                size_stmt = size_stmt.where(and_(*conditions))
            total_size = session.execute(size_stmt).scalar() or 0
            
            # By type
            type_stmt = select(
                Snapshot.snapshot_type,
                func.count(Snapshot.id)
            ).group_by(Snapshot.snapshot_type)
            if conditions:
                type_stmt = type_stmt.where(and_(*conditions))
            type_results = session.execute(type_stmt).all()
            by_type = {
                t.value if t else "unknown": c 
                for t, c in type_results
            }
            
            return {
                "total_snapshots": total,
                "total_size_bytes": total_size,
                "by_type": by_type,
                "generated_at": datetime.utcnow().isoformat(),
            }


# Global instance
snapshot_manager = SnapshotManager()
