"""
Save Strategy Manager for Data Sync Pipeline.

Manages data persistence strategies: persistent, memory, and hybrid modes.
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
import logging

from src.sync.pipeline.enums import SaveStrategy
from src.sync.pipeline.schemas import SaveConfig, SaveResult

logger = logging.getLogger(__name__)


class SaveStrategyManager:
    """
    Manager for data save strategies.
    
    Supports:
    - Persistent: Save to PostgreSQL database
    - Memory: Process in memory only (no persistence)
    - Hybrid: Auto-select based on data size
    """
    
    def __init__(self, db_session=None, cache=None):
        """
        Initialize the Save Strategy Manager.
        
        Args:
            db_session: Database session for persistent storage
            cache: Redis cache for temporary storage
        """
        self.db_session = db_session
        self.cache = cache
        self._memory_store: Dict[str, List[Dict]] = {}
    
    async def save(
        self,
        data: List[Dict[str, Any]],
        strategy: SaveStrategy,
        config: SaveConfig
    ) -> SaveResult:
        """
        Save data according to the specified strategy.
        
        Args:
            data: Data to save
            strategy: Save strategy to use
            config: Save configuration
            
        Returns:
            SaveResult with save status
        """
        if strategy == SaveStrategy.PERSISTENT:
            return await self.save_to_db(data, config)
        elif strategy == SaveStrategy.MEMORY:
            return await self.save_to_memory(data, config)
        else:  # HYBRID
            return await self.save_hybrid(data, config)
    
    async def save_to_db(
        self,
        data: List[Dict[str, Any]],
        config: SaveConfig
    ) -> SaveResult:
        """
        Save data to PostgreSQL database.
        
        Args:
            data: Data to save
            config: Save configuration
            
        Returns:
            SaveResult with save status
        """
        try:
            if not self.db_session:
                # Fallback to memory if no DB session
                logger.warning("No database session, falling back to memory storage")
                return await self.save_to_memory(data, config)
            
            # Generate batch ID
            batch_id = str(uuid4())
            
            # Save to database (implementation depends on model)
            from src.sync.pipeline.models import SyncedDataModel
            
            for record in data:
                db_record = SyncedDataModel(
                    batch_id=batch_id,
                    data=record,
                    table_name=config.table_name,
                    created_at=datetime.utcnow()
                )
                self.db_session.add(db_record)
            
            await self.db_session.commit()
            
            logger.info(f"Saved {len(data)} records to database (batch: {batch_id})")
            
            return SaveResult(
                success=True,
                strategy_used=SaveStrategy.PERSISTENT,
                rows_saved=len(data),
                storage_location="database"
            )
            
        except Exception as e:
            logger.error(f"Failed to save to database: {str(e)}")
            return SaveResult(
                success=False,
                strategy_used=SaveStrategy.PERSISTENT,
                rows_saved=0,
                storage_location="database",
                error_message=str(e)
            )
    
    async def save_to_memory(
        self,
        data: List[Dict[str, Any]],
        config: SaveConfig
    ) -> SaveResult:
        """
        Process data in memory only (no persistence).
        
        Args:
            data: Data to process
            config: Save configuration
            
        Returns:
            SaveResult with processing status
        """
        try:
            # Generate batch ID for tracking
            batch_id = str(uuid4())
            
            # Store in memory temporarily
            self._memory_store[batch_id] = data
            
            logger.info(f"Processed {len(data)} records in memory (batch: {batch_id})")
            
            return SaveResult(
                success=True,
                strategy_used=SaveStrategy.MEMORY,
                rows_saved=len(data),
                storage_location="memory"
            )
            
        except Exception as e:
            logger.error(f"Failed to process in memory: {str(e)}")
            return SaveResult(
                success=False,
                strategy_used=SaveStrategy.MEMORY,
                rows_saved=0,
                storage_location="memory",
                error_message=str(e)
            )
    
    async def save_hybrid(
        self,
        data: List[Dict[str, Any]],
        config: SaveConfig
    ) -> SaveResult:
        """
        Auto-select strategy based on data size.
        
        Uses persistent storage if data exceeds threshold,
        otherwise uses memory processing.
        
        Args:
            data: Data to save
            config: Save configuration
            
        Returns:
            SaveResult with save status
        """
        threshold = config.hybrid_threshold_bytes
        data_size = self.calculate_size(data)
        
        if data_size > threshold:
            logger.info(
                f"Data size ({data_size} bytes) exceeds threshold "
                f"({threshold} bytes), using persistent storage"
            )
            return await self.save_to_db(data, config)
        else:
            logger.info(
                f"Data size ({data_size} bytes) within threshold "
                f"({threshold} bytes), using memory processing"
            )
            return await self.save_to_memory(data, config)
    
    async def cleanup_expired(self, retention_days: int) -> int:
        """
        Clean up expired data from persistent storage.
        
        Args:
            retention_days: Number of days to retain data
            
        Returns:
            Number of records cleaned up
        """
        if not self.db_session:
            return 0
        
        try:
            from sqlalchemy import delete
            from src.sync.pipeline.models import SyncedDataModel
            
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            stmt = delete(SyncedDataModel).where(
                SyncedDataModel.created_at < cutoff_date
            )
            result = await self.db_session.execute(stmt)
            await self.db_session.commit()
            
            deleted_count = result.rowcount
            logger.info(f"Cleaned up {deleted_count} expired records")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {str(e)}")
            return 0
    
    def calculate_size(self, data: List[Dict[str, Any]]) -> int:
        """
        Calculate the approximate size of data in bytes.
        
        Args:
            data: Data to measure
            
        Returns:
            Approximate size in bytes
        """
        # Use JSON serialization to estimate size
        try:
            json_str = json.dumps(data)
            return len(json_str.encode('utf-8'))
        except Exception:
            # Fallback: estimate based on sys.getsizeof
            return sum(sys.getsizeof(record) for record in data)
    
    def get_memory_data(self, batch_id: str) -> Optional[List[Dict]]:
        """
        Retrieve data from memory store.
        
        Args:
            batch_id: Batch ID to retrieve
            
        Returns:
            Data if found, None otherwise
        """
        return self._memory_store.get(batch_id)
    
    def clear_memory_batch(self, batch_id: str) -> bool:
        """
        Clear a batch from memory store.
        
        Args:
            batch_id: Batch ID to clear
            
        Returns:
            True if cleared, False if not found
        """
        if batch_id in self._memory_store:
            del self._memory_store[batch_id]
            return True
        return False
    
    def clear_all_memory(self) -> int:
        """
        Clear all data from memory store.
        
        Returns:
            Number of batches cleared
        """
        count = len(self._memory_store)
        self._memory_store.clear()
        return count
    
    @property
    def memory_batch_count(self) -> int:
        """Get the number of batches in memory."""
        return len(self._memory_store)
    
    @property
    def memory_record_count(self) -> int:
        """Get the total number of records in memory."""
        return sum(len(batch) for batch in self._memory_store.values())
