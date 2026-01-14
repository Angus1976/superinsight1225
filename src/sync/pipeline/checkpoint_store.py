"""
Checkpoint Store for Data Sync Pipeline.

Manages persistence and retrieval of sync checkpoints for incremental pulling.
"""

from datetime import datetime
from typing import Any, Dict, Optional
import json
import logging

from src.sync.pipeline.schemas import Checkpoint

logger = logging.getLogger(__name__)


class CheckpointStore:
    """
    Store for managing sync checkpoints.
    
    Supports both in-memory and database-backed storage.
    """
    
    def __init__(self, db_session=None):
        """
        Initialize the checkpoint store.
        
        Args:
            db_session: Optional database session for persistent storage.
                       If None, uses in-memory storage.
        """
        self.db_session = db_session
        self._memory_store: Dict[str, Checkpoint] = {}
    
    async def get(self, source_id: str) -> Optional[Checkpoint]:
        """
        Get checkpoint for a source.
        
        Args:
            source_id: ID of the data source
            
        Returns:
            Checkpoint if exists, None otherwise
        """
        if self.db_session:
            return await self._get_from_db(source_id)
        return self._memory_store.get(source_id)
    
    async def save(self, checkpoint: Checkpoint) -> None:
        """
        Save a checkpoint.
        
        Args:
            checkpoint: Checkpoint to save
        """
        if self.db_session:
            await self._save_to_db(checkpoint)
        else:
            self._memory_store[checkpoint.source_id] = checkpoint
        
        logger.debug(f"Saved checkpoint for source {checkpoint.source_id}")
    
    async def delete(self, source_id: str) -> bool:
        """
        Delete a checkpoint.
        
        Args:
            source_id: ID of the data source
            
        Returns:
            True if deleted, False if not found
        """
        if self.db_session:
            return await self._delete_from_db(source_id)
        
        if source_id in self._memory_store:
            del self._memory_store[source_id]
            return True
        return False
    
    async def exists(self, source_id: str) -> bool:
        """
        Check if checkpoint exists for a source.
        
        Args:
            source_id: ID of the data source
            
        Returns:
            True if checkpoint exists
        """
        checkpoint = await self.get(source_id)
        return checkpoint is not None
    
    async def update_last_value(
        self,
        source_id: str,
        last_value: Any,
        rows_pulled: int = 0
    ) -> Optional[Checkpoint]:
        """
        Update the last value for a checkpoint.
        
        Args:
            source_id: ID of the data source
            last_value: New last value
            rows_pulled: Number of rows pulled in this batch
            
        Returns:
            Updated checkpoint or None if not found
        """
        checkpoint = await self.get(source_id)
        
        if checkpoint:
            checkpoint.last_value = last_value
            checkpoint.last_pull_at = datetime.utcnow()
            checkpoint.rows_pulled += rows_pulled
            await self.save(checkpoint)
            return checkpoint
        
        # Create new checkpoint if not exists
        checkpoint = Checkpoint(
            source_id=source_id,
            last_value=last_value,
            last_pull_at=datetime.utcnow(),
            rows_pulled=rows_pulled
        )
        await self.save(checkpoint)
        return checkpoint
    
    async def _get_from_db(self, source_id: str) -> Optional[Checkpoint]:
        """Get checkpoint from database."""
        from sqlalchemy import select
        from src.sync.pipeline.models import SyncCheckpointModel
        
        stmt = select(SyncCheckpointModel).where(
            SyncCheckpointModel.source_id == source_id
        )
        result = await self.db_session.execute(stmt)
        record = result.scalar_one_or_none()
        
        if record:
            return Checkpoint(
                source_id=str(record.source_id),
                last_value=record.last_value,
                last_pull_at=record.last_pull_at,
                rows_pulled=record.rows_pulled
            )
        return None
    
    async def _save_to_db(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to database."""
        from sqlalchemy import select
        from src.sync.pipeline.models import SyncCheckpointModel
        
        # Check if exists
        stmt = select(SyncCheckpointModel).where(
            SyncCheckpointModel.source_id == checkpoint.source_id
        )
        result = await self.db_session.execute(stmt)
        record = result.scalar_one_or_none()
        
        if record:
            # Update existing
            record.last_value = json.dumps(checkpoint.last_value) if checkpoint.last_value else None
            record.last_pull_at = checkpoint.last_pull_at
            record.rows_pulled = checkpoint.rows_pulled
        else:
            # Create new
            record = SyncCheckpointModel(
                source_id=checkpoint.source_id,
                checkpoint_field="updated_at",
                last_value=json.dumps(checkpoint.last_value) if checkpoint.last_value else None,
                last_pull_at=checkpoint.last_pull_at,
                rows_pulled=checkpoint.rows_pulled
            )
            self.db_session.add(record)
        
        await self.db_session.commit()
    
    async def _delete_from_db(self, source_id: str) -> bool:
        """Delete checkpoint from database."""
        from sqlalchemy import delete
        from src.sync.pipeline.models import SyncCheckpointModel
        
        stmt = delete(SyncCheckpointModel).where(
            SyncCheckpointModel.source_id == source_id
        )
        result = await self.db_session.execute(stmt)
        await self.db_session.commit()
        
        return result.rowcount > 0
    
    def clear_memory(self) -> None:
        """Clear all in-memory checkpoints."""
        self._memory_store.clear()
