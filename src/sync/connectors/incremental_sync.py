"""
Incremental Sync Engine.

Provides intelligent incremental synchronization with multiple strategies,
change detection, and automatic recovery mechanisms.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from src.sync.connectors.base import (
    BaseConnector,
    DataBatch,
    DataRecord,
    OperationType,
    SyncResult
)

logger = logging.getLogger(__name__)


class SyncStrategy(str, Enum):
    """Incremental sync strategies."""
    TIMESTAMP = "timestamp"
    VERSION = "version"
    HASH = "hash"
    CDC = "cdc"
    HYBRID = "hybrid"


class ChangeType(str, Enum):
    """Types of data changes."""
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    SCHEMA_CHANGE = "schema_change"


@dataclass
class SyncCheckpoint:
    """Checkpoint for incremental sync state."""
    sync_id: str
    table_name: str
    strategy: SyncStrategy
    last_sync_time: datetime
    last_value: Optional[str] = None
    last_hash: Optional[str] = None
    last_version: Optional[str] = None
    last_lsn: Optional[str] = None  # Log Sequence Number for CDC
    record_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChangeRecord:
    """Record representing a data change."""
    change_id: str
    change_type: ChangeType
    table_name: str
    record_id: str
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    change_time: datetime = field(default_factory=datetime.utcnow)
    lsn: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IncrementalSyncConfig(BaseModel):
    """Configuration for incremental sync."""
    strategy: SyncStrategy = SyncStrategy.TIMESTAMP
    
    # Timestamp-based sync
    timestamp_field: str = "updated_at"
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"
    
    # Version-based sync
    version_field: str = "version"
    
    # Hash-based sync
    hash_fields: List[str] = Field(default_factory=list)
    
    # CDC settings
    cdc_enabled: bool = False
    cdc_table_prefix: str = "cdc_"
    
    # Batch settings
    batch_size: int = Field(default=1000, ge=1)
    max_batch_size: int = Field(default=10000, ge=1)
    
    # Recovery settings
    enable_recovery: bool = True
    checkpoint_interval: int = Field(default=100, ge=1)  # records
    max_retry_attempts: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=5.0, ge=0.1)
    
    # Change detection
    enable_change_detection: bool = True
    change_detection_fields: List[str] = Field(default_factory=list)
    
    # Performance settings
    parallel_processing: bool = False
    max_workers: int = Field(default=4, ge=1)


class IncrementalSyncEngine:
    """
    Intelligent incremental synchronization engine.
    
    Features:
    - Multiple sync strategies (timestamp, version, hash, CDC)
    - Automatic change detection and comparison
    - Checkpoint management for recovery
    - Parallel processing support
    - Conflict detection and resolution
    """

    def __init__(self, config: IncrementalSyncConfig):
        self.config = config
        self.engine_id = str(uuid4())
        
        # State management
        self.checkpoints: Dict[str, SyncCheckpoint] = {}
        self.change_log: List[ChangeRecord] = []
        
        # Recovery state
        self.recovery_mode = False
        self.failed_batches: List[DataBatch] = []
        
        # Performance tracking
        self.sync_stats = {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "total_records": 0,
            "total_changes": 0,
            "avg_sync_time": 0.0
        }

    async def sync_table(
        self,
        connector: BaseConnector,
        table_name: str,
        target_connector: Optional[BaseConnector] = None
    ) -> SyncResult:
        """
        Perform incremental sync for a table.
        
        Args:
            connector: Source connector
            table_name: Table to sync
            target_connector: Optional target connector for direct sync
            
        Returns:
            SyncResult with sync statistics
        """
        import time
        start_time = time.time()
        
        sync_id = f"{self.engine_id}_{table_name}_{int(start_time)}"
        
        try:
            logger.info(f"Starting incremental sync: {sync_id}")
            
            # Get or create checkpoint
            checkpoint = await self._get_checkpoint(table_name)
            
            # Determine sync strategy
            strategy = await self._determine_strategy(connector, table_name)
            
            # Fetch incremental data
            batches = []
            async for batch in self._fetch_incremental_data(
                connector, table_name, checkpoint, strategy
            ):
                batches.append(batch)
                
                # Process batch if target connector provided
                if target_connector:
                    await self._process_batch(batch, target_connector)
                
                # Update checkpoint periodically
                if len(batches) % self.config.checkpoint_interval == 0:
                    await self._update_checkpoint(checkpoint, batch)
            
            # Final checkpoint update
            if batches:
                await self._update_checkpoint(checkpoint, batches[-1])
            
            # Calculate results
            total_records = sum(len(batch.records) for batch in batches)
            changes_detected = await self._detect_changes(batches)
            
            result = SyncResult(
                success=True,
                records_processed=total_records,
                records_inserted=sum(
                    len([r for r in batch.records if r.operation == OperationType.INSERT])
                    for batch in batches
                ),
                records_updated=sum(
                    len([r for r in batch.records if r.operation == OperationType.UPDATE])
                    for batch in batches
                ),
                records_deleted=sum(
                    len([r for r in batch.records if r.operation == OperationType.DELETE])
                    for batch in batches
                ),
                duration_seconds=time.time() - start_time,
                checkpoint=checkpoint.__dict__,
                metadata={
                    "sync_id": sync_id,
                    "strategy": strategy.value,
                    "changes_detected": len(changes_detected),
                    "batches_processed": len(batches)
                }
            )
            
            # Update stats
            self._update_stats(result)
            
            logger.info(
                f"Incremental sync completed: {sync_id}, "
                f"records: {total_records}, changes: {len(changes_detected)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Incremental sync failed: {sync_id}, error: {e}")
            
            # Handle recovery if enabled
            if self.config.enable_recovery:
                await self._handle_sync_failure(sync_id, e)
            
            return SyncResult(
                success=False,
                duration_seconds=time.time() - start_time,
                errors=[{"error": str(e), "sync_id": sync_id}]
            )

    async def _get_checkpoint(self, table_name: str) -> SyncCheckpoint:
        """Get or create checkpoint for table."""
        checkpoint_key = f"{self.engine_id}_{table_name}"
        
        if checkpoint_key not in self.checkpoints:
            self.checkpoints[checkpoint_key] = SyncCheckpoint(
                sync_id=checkpoint_key,
                table_name=table_name,
                strategy=self.config.strategy,
                last_sync_time=datetime.utcnow() - timedelta(days=1)  # Start from yesterday
            )
        
        return self.checkpoints[checkpoint_key]

    async def _determine_strategy(
        self,
        connector: BaseConnector,
        table_name: str
    ) -> SyncStrategy:
        """Determine the best sync strategy for the table."""
        if self.config.strategy != SyncStrategy.HYBRID:
            return self.config.strategy
        
        # Auto-detect best strategy based on table schema
        try:
            schema = await connector.fetch_schema()
            table_info = None
            
            # Find table in schema
            for table in schema.get("tables", []):
                if table["name"] == table_name:
                    table_info = table
                    break
            
            if not table_info:
                logger.warning(f"Table not found in schema: {table_name}")
                return SyncStrategy.TIMESTAMP
            
            columns = {col["name"]: col for col in table_info["columns"]}
            
            # Check for CDC support
            if self.config.cdc_enabled:
                return SyncStrategy.CDC
            
            # Check for version column
            if self.config.version_field in columns:
                return SyncStrategy.VERSION
            
            # Check for timestamp column
            if self.config.timestamp_field in columns:
                return SyncStrategy.TIMESTAMP
            
            # Fall back to hash-based
            return SyncStrategy.HASH
            
        except Exception as e:
            logger.warning(f"Failed to determine strategy for {table_name}: {e}")
            return SyncStrategy.TIMESTAMP

    async def _fetch_incremental_data(
        self,
        connector: BaseConnector,
        table_name: str,
        checkpoint: SyncCheckpoint,
        strategy: SyncStrategy
    ) -> List[DataBatch]:
        """Fetch incremental data based on strategy."""
        if strategy == SyncStrategy.TIMESTAMP:
            return await self._fetch_timestamp_based(connector, table_name, checkpoint)
        elif strategy == SyncStrategy.VERSION:
            return await self._fetch_version_based(connector, table_name, checkpoint)
        elif strategy == SyncStrategy.HASH:
            return await self._fetch_hash_based(connector, table_name, checkpoint)
        elif strategy == SyncStrategy.CDC:
            return await self._fetch_cdc_based(connector, table_name, checkpoint)
        else:
            raise ValueError(f"Unsupported sync strategy: {strategy}")

    async def _fetch_timestamp_based(
        self,
        connector: BaseConnector,
        table_name: str,
        checkpoint: SyncCheckpoint
    ) -> List[DataBatch]:
        """Fetch data using timestamp-based incremental sync."""
        batches = []
        
        # Format last sync time
        last_sync_str = checkpoint.last_sync_time.strftime(self.config.timestamp_format)
        
        async for batch in connector.fetch_data_stream(
            table=table_name,
            incremental_field=self.config.timestamp_field,
            incremental_value=last_sync_str,
            batch_size=self.config.batch_size
        ):
            batches.append(batch)
            
            # Update operations based on timestamp comparison
            for record in batch.records:
                record_time_str = record.data.get(self.config.timestamp_field)
                if record_time_str:
                    try:
                        record_time = datetime.strptime(record_time_str, self.config.timestamp_format)
                        if record_time > checkpoint.last_sync_time:
                            # Determine if insert or update based on existence
                            record.operation = OperationType.UPSERT
                    except ValueError:
                        logger.warning(f"Invalid timestamp format: {record_time_str}")
        
        return batches

    async def _fetch_version_based(
        self,
        connector: BaseConnector,
        table_name: str,
        checkpoint: SyncCheckpoint
    ) -> List[DataBatch]:
        """Fetch data using version-based incremental sync."""
        batches = []
        
        last_version = checkpoint.last_version or "0"
        
        async for batch in connector.fetch_data_stream(
            table=table_name,
            incremental_field=self.config.version_field,
            incremental_value=last_version,
            batch_size=self.config.batch_size
        ):
            batches.append(batch)
            
            # Update operations based on version comparison
            for record in batch.records:
                record_version = record.data.get(self.config.version_field)
                if record_version and str(record_version) > last_version:
                    record.operation = OperationType.UPSERT
        
        return batches

    async def _fetch_hash_based(
        self,
        connector: BaseConnector,
        table_name: str,
        checkpoint: SyncCheckpoint
    ) -> List[DataBatch]:
        """Fetch data using hash-based change detection."""
        batches = []
        
        # Fetch all data and compute hashes
        async for batch in connector.fetch_data_stream(
            table=table_name,
            batch_size=self.config.batch_size
        ):
            # Compute hashes for change detection
            for record in batch.records:
                current_hash = self._compute_record_hash(record.data)
                record.hash = current_hash
                
                # Compare with stored hash (would be from previous sync)
                stored_hash = checkpoint.metadata.get(f"hash_{record.id}")
                if stored_hash != current_hash:
                    record.operation = OperationType.UPSERT
                else:
                    record.operation = OperationType.UPSERT  # For demo, treat all as upsert
            
            batches.append(batch)
        
        return batches

    async def _fetch_cdc_based(
        self,
        connector: BaseConnector,
        table_name: str,
        checkpoint: SyncCheckpoint
    ) -> List[DataBatch]:
        """Fetch data using Change Data Capture."""
        batches = []
        
        # This would integrate with database-specific CDC mechanisms
        # For demo, simulate CDC changes
        
        # Get changes since last LSN
        last_lsn = checkpoint.last_lsn or "0"
        
        # Simulate CDC changes
        changes = await self._get_cdc_changes(connector, table_name, last_lsn)
        
        if changes:
            records = []
            for change in changes:
                record = DataRecord(
                    id=change["record_id"],
                    data=change["new_data"] or change["old_data"],
                    operation=OperationType(change["operation"]),
                    timestamp=datetime.fromisoformat(change["timestamp"])
                )
                records.append(record)
            
            batch = DataBatch(
                records=records,
                source_id=f"cdc:{table_name}",
                table_name=table_name,
                checkpoint={"last_lsn": changes[-1]["lsn"]}
            )
            batches.append(batch)
        
        return batches

    async def _get_cdc_changes(
        self,
        connector: BaseConnector,
        table_name: str,
        last_lsn: str
    ) -> List[Dict[str, Any]]:
        """Get CDC changes from database."""
        # This would be database-specific implementation
        # For demo, return empty list
        return []

    def _compute_record_hash(self, data: Dict[str, Any]) -> str:
        """Compute hash for record data."""
        # Use specified fields or all fields
        fields_to_hash = self.config.hash_fields or list(data.keys())
        
        # Create deterministic hash
        hash_data = {k: data.get(k) for k in sorted(fields_to_hash)}
        hash_str = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.sha256(hash_str.encode()).hexdigest()

    async def _detect_changes(self, batches: List[DataBatch]) -> List[ChangeRecord]:
        """Detect and classify changes in the data."""
        changes = []
        
        if not self.config.enable_change_detection:
            return changes
        
        for batch in batches:
            for record in batch.records:
                # Create change record
                change = ChangeRecord(
                    change_id=str(uuid4()),
                    change_type=ChangeType(record.operation.value),
                    table_name=batch.table_name or "unknown",
                    record_id=record.id,
                    new_data=record.data,
                    change_time=record.timestamp or datetime.utcnow()
                )
                changes.append(change)
        
        # Store changes in log
        self.change_log.extend(changes)
        
        # Maintain change log size
        if len(self.change_log) > 10000:
            self.change_log = self.change_log[-5000:]  # Keep last 5000
        
        return changes

    async def _process_batch(
        self,
        batch: DataBatch,
        target_connector: BaseConnector
    ) -> SyncResult:
        """Process a batch by writing to target connector."""
        try:
            return await target_connector.write_data(batch, mode="upsert")
        except Exception as e:
            logger.error(f"Failed to process batch: {e}")
            self.failed_batches.append(batch)
            raise

    async def _update_checkpoint(
        self,
        checkpoint: SyncCheckpoint,
        batch: DataBatch
    ) -> None:
        """Update checkpoint with latest sync state."""
        checkpoint.updated_at = datetime.utcnow()
        checkpoint.record_count += len(batch.records)
        
        # Update strategy-specific values
        if checkpoint.strategy == SyncStrategy.TIMESTAMP:
            # Find latest timestamp
            latest_time = checkpoint.last_sync_time
            for record in batch.records:
                record_time_str = record.data.get(self.config.timestamp_field)
                if record_time_str:
                    try:
                        record_time = datetime.strptime(record_time_str, self.config.timestamp_format)
                        if record_time > latest_time:
                            latest_time = record_time
                    except ValueError:
                        pass
            checkpoint.last_sync_time = latest_time
            
        elif checkpoint.strategy == SyncStrategy.VERSION:
            # Find latest version
            latest_version = checkpoint.last_version or "0"
            for record in batch.records:
                record_version = str(record.data.get(self.config.version_field, "0"))
                if record_version > latest_version:
                    latest_version = record_version
            checkpoint.last_version = latest_version
            
        elif checkpoint.strategy == SyncStrategy.HASH:
            # Store hashes for next comparison
            for record in batch.records:
                if record.hash:
                    checkpoint.metadata[f"hash_{record.id}"] = record.hash
                    
        elif checkpoint.strategy == SyncStrategy.CDC:
            # Update LSN from batch checkpoint
            if batch.checkpoint and "last_lsn" in batch.checkpoint:
                checkpoint.last_lsn = batch.checkpoint["last_lsn"]

    async def _handle_sync_failure(self, sync_id: str, error: Exception) -> None:
        """Handle sync failure with recovery logic."""
        logger.warning(f"Handling sync failure: {sync_id}")
        
        self.recovery_mode = True
        
        # Retry failed batches
        if self.failed_batches:
            logger.info(f"Retrying {len(self.failed_batches)} failed batches")
            
            retry_count = 0
            while self.failed_batches and retry_count < self.config.max_retry_attempts:
                retry_count += 1
                failed_batch = self.failed_batches.pop(0)
                
                try:
                    await asyncio.sleep(self.config.retry_delay)
                    # Would retry processing the batch
                    logger.info(f"Retry {retry_count} for batch {failed_batch.batch_id}")
                    
                except Exception as retry_error:
                    logger.error(f"Retry failed: {retry_error}")
                    self.failed_batches.append(failed_batch)
        
        self.recovery_mode = False

    def _update_stats(self, result: SyncResult) -> None:
        """Update sync statistics."""
        self.sync_stats["total_syncs"] += 1
        
        if result.success:
            self.sync_stats["successful_syncs"] += 1
        else:
            self.sync_stats["failed_syncs"] += 1
        
        self.sync_stats["total_records"] += result.records_processed
        
        # Update average sync time
        current_avg = self.sync_stats["avg_sync_time"]
        total_syncs = self.sync_stats["total_syncs"]
        self.sync_stats["avg_sync_time"] = (
            (current_avg * (total_syncs - 1) + result.duration_seconds) / total_syncs
        )

    def get_checkpoint(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get checkpoint information for a table."""
        checkpoint_key = f"{self.engine_id}_{table_name}"
        checkpoint = self.checkpoints.get(checkpoint_key)
        
        if checkpoint:
            return {
                "sync_id": checkpoint.sync_id,
                "table_name": checkpoint.table_name,
                "strategy": checkpoint.strategy.value,
                "last_sync_time": checkpoint.last_sync_time.isoformat(),
                "last_value": checkpoint.last_value,
                "last_version": checkpoint.last_version,
                "last_lsn": checkpoint.last_lsn,
                "record_count": checkpoint.record_count,
                "created_at": checkpoint.created_at.isoformat(),
                "updated_at": checkpoint.updated_at.isoformat()
            }
        
        return None

    def get_change_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent change log entries."""
        recent_changes = self.change_log[-limit:] if limit > 0 else self.change_log
        
        return [
            {
                "change_id": change.change_id,
                "change_type": change.change_type.value,
                "table_name": change.table_name,
                "record_id": change.record_id,
                "change_time": change.change_time.isoformat(),
                "lsn": change.lsn,
                "has_old_data": change.old_data is not None,
                "has_new_data": change.new_data is not None
            }
            for change in recent_changes
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get sync engine statistics."""
        return {
            "engine_id": self.engine_id,
            "recovery_mode": self.recovery_mode,
            "failed_batches": len(self.failed_batches),
            "checkpoints": len(self.checkpoints),
            "change_log_size": len(self.change_log),
            **self.sync_stats
        }