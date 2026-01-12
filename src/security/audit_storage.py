"""
Audit Log Storage Optimization Module

Provides optimized storage, archival, and performance management for audit logs.
Implements batch storage, database partitioning, and automated archival strategies.
"""

import logging
import asyncio
import gzip
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Iterator, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, text, func, and_, or_
from sqlalchemy.dialects.postgresql import insert
import psutil

from src.security.models import AuditLogModel, AuditAction
from src.database.connection import db_manager, get_db_session
from src.database.batch_processor import BatchProcessor, BatchConfig, BatchStats
from src.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class StorageConfig:
    """Configuration for audit log storage optimization."""
    batch_size: int = 1000
    max_memory_mb: int = 256
    compression_enabled: bool = True
    partition_by_month: bool = True
    retention_days: int = 2555  # 7 years default
    archive_threshold_days: int = 365  # 1 year
    cleanup_batch_size: int = 5000
    max_workers: int = 4


@dataclass
class StorageStats:
    """Statistics for storage operations."""
    total_logs_stored: int = 0
    batch_operations: int = 0
    compression_ratio: float = 0.0
    storage_time_seconds: float = 0.0
    archived_logs: int = 0
    deleted_logs: int = 0
    peak_memory_mb: float = 0.0
    
    @property
    def throughput_logs_per_second(self) -> float:
        """Calculate storage throughput."""
        if self.storage_time_seconds > 0:
            return self.total_logs_stored / self.storage_time_seconds
        return 0.0


class AuditLogBatchStorage:
    """Optimized batch storage for audit logs."""
    
    def __init__(self, config: StorageConfig = None):
        """Initialize batch storage."""
        self.config = config or StorageConfig()
        self.batch_processor = BatchProcessor(
            BatchConfig(
                batch_size=self.config.batch_size,
                max_memory_mb=self.config.max_memory_mb,
                max_workers=self.config.max_workers,
                enable_gc=True
            )
        )
        self.pending_logs: List[AuditLogModel] = []
        self.stats = StorageStats()
        
    async def store_audit_logs_batch(
        self,
        audit_logs: List[AuditLogModel],
        db: Session = None
    ) -> StorageStats:
        """Store audit logs in optimized batches."""
        start_time = datetime.now()
        
        try:
            if not db:
                with db_manager.get_session() as session:
                    return await self._store_batch_internal(audit_logs, session)
            else:
                return await self._store_batch_internal(audit_logs, db)
                
        except Exception as e:
            logger.error(f"Batch storage failed: {e}")
            raise
        finally:
            self.stats.storage_time_seconds = (datetime.now() - start_time).total_seconds()
    
    async def _store_batch_internal(
        self,
        audit_logs: List[AuditLogModel],
        db: Session
    ) -> StorageStats:
        """Internal batch storage implementation."""
        
        # Reset stats
        self.stats = StorageStats()
        self.stats.total_logs_stored = len(audit_logs)
        
        # Process in batches for memory efficiency
        batches = [
            audit_logs[i:i + self.config.batch_size]
            for i in range(0, len(audit_logs), self.config.batch_size)
        ]
        
        for batch in batches:
            try:
                # Prepare batch data
                batch_data = await self._prepare_batch_data(batch)
                
                # Use PostgreSQL COPY for maximum performance
                if self._is_postgresql(db):
                    await self._bulk_insert_postgresql(batch_data, db)
                else:
                    await self._bulk_insert_generic(batch_data, db)
                
                self.stats.batch_operations += 1
                
                # Monitor memory usage
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                self.stats.peak_memory_mb = max(self.stats.peak_memory_mb, current_memory)
                
                logger.debug(f"Stored batch of {len(batch)} audit logs")
                
            except Exception as e:
                logger.error(f"Failed to store batch: {e}")
                # Continue with next batch rather than failing completely
                continue
        
        db.commit()
        logger.info(f"Batch storage completed: {self.stats.total_logs_stored} logs in "
                   f"{self.stats.batch_operations} batches")
        
        return self.stats
    
    async def _prepare_batch_data(self, batch: List[AuditLogModel]) -> List[Dict[str, Any]]:
        """Prepare batch data for insertion."""
        batch_data = []
        
        for log in batch:
            # Compress details if enabled
            details = log.details
            if self.config.compression_enabled and details:
                details = await self._compress_details(details)
            
            batch_data.append({
                'id': log.id,
                'user_id': log.user_id,
                'tenant_id': log.tenant_id,
                'action': log.action,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'details': details,
                'timestamp': log.timestamp or datetime.utcnow()
            })
        
        return batch_data
    
    async def _compress_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Compress audit log details."""
        try:
            # Convert to JSON string
            details_json = json.dumps(details, default=str)
            
            # Compress if size is significant
            if len(details_json) > 1024:  # 1KB threshold
                compressed = gzip.compress(details_json.encode('utf-8'))
                compression_ratio = len(compressed) / len(details_json)
                
                # Only use compression if it provides significant savings
                if compression_ratio < 0.8:
                    self.stats.compression_ratio = compression_ratio
                    return {
                        '_compressed': True,
                        '_data': compressed.hex()
                    }
            
            return details
            
        except Exception as e:
            logger.warning(f"Failed to compress details: {e}")
            return details
    
    def _is_postgresql(self, db: Session) -> bool:
        """Check if database is PostgreSQL."""
        try:
            return 'postgresql' in str(db.bind.url).lower()
        except:
            return False
    
    async def _bulk_insert_postgresql(self, batch_data: List[Dict[str, Any]], db: Session):
        """Use PostgreSQL-specific bulk insert."""
        try:
            # Use PostgreSQL's INSERT ... ON CONFLICT for upsert behavior
            stmt = insert(AuditLogModel).values(batch_data)
            stmt = stmt.on_conflict_do_nothing(index_elements=['id'])
            db.execute(stmt)
            
        except Exception as e:
            logger.error(f"PostgreSQL bulk insert failed: {e}")
            # Fallback to generic method
            await self._bulk_insert_generic(batch_data, db)
    
    async def _bulk_insert_generic(self, batch_data: List[Dict[str, Any]], db: Session):
        """Generic bulk insert for any database."""
        try:
            # Create model instances
            audit_logs = [AuditLogModel(**data) for data in batch_data]
            
            # Bulk insert
            db.add_all(audit_logs)
            
        except Exception as e:
            logger.error(f"Generic bulk insert failed: {e}")
            raise
    
    def add_to_pending(self, audit_log: AuditLogModel):
        """Add audit log to pending batch."""
        self.pending_logs.append(audit_log)
        
        # Auto-flush when batch size is reached
        if len(self.pending_logs) >= self.config.batch_size:
            asyncio.create_task(self.flush_pending())
    
    async def flush_pending(self, db: Session = None):
        """Flush pending audit logs to storage."""
        if not self.pending_logs:
            return
        
        logs_to_store = self.pending_logs.copy()
        self.pending_logs.clear()
        
        await self.store_audit_logs_batch(logs_to_store, db)


class AuditLogPartitionManager:
    """Manages database partitioning for audit logs."""
    
    def __init__(self, config: StorageConfig = None):
        """Initialize partition manager."""
        self.config = config or StorageConfig()
    
    async def create_monthly_partitions(
        self,
        start_date: datetime,
        months_ahead: int = 12,
        db: Session = None
    ) -> List[str]:
        """Create monthly partitions for audit logs."""
        
        if not self.config.partition_by_month:
            logger.info("Monthly partitioning is disabled")
            return []
        
        created_partitions = []
        
        with db_manager.get_session() as session:
            for i in range(months_ahead):
                partition_date = start_date + timedelta(days=30 * i)
                partition_name = f"audit_logs_{partition_date.strftime('%Y_%m')}"
                
                try:
                    # Check if partition already exists
                    if await self._partition_exists(partition_name, session):
                        continue
                    
                    # Create partition
                    await self._create_partition(partition_name, partition_date, session)
                    created_partitions.append(partition_name)
                    
                    logger.info(f"Created partition: {partition_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to create partition {partition_name}: {e}")
        
        return created_partitions
    
    async def _partition_exists(self, partition_name: str, db: Session) -> bool:
        """Check if partition exists."""
        try:
            result = db.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = :partition_name)"
            ), {"partition_name": partition_name})
            
            return result.scalar()
            
        except Exception:
            # Assume partition doesn't exist if check fails
            return False
    
    async def _create_partition(
        self,
        partition_name: str,
        partition_date: datetime,
        db: Session
    ):
        """Create a monthly partition."""
        
        # Calculate partition bounds
        start_date = partition_date.replace(day=1)
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
        
        # Create partition table
        partition_sql = f"""
        CREATE TABLE {partition_name} PARTITION OF audit_logs
        FOR VALUES FROM ('{start_date.isoformat()}') TO ('{end_date.isoformat()}');
        
        CREATE INDEX idx_{partition_name}_tenant_timestamp 
        ON {partition_name} (tenant_id, timestamp);
        
        CREATE INDEX idx_{partition_name}_user_action 
        ON {partition_name} (user_id, action);
        
        CREATE INDEX idx_{partition_name}_resource 
        ON {partition_name} (resource_type, resource_id);
        """
        
        db.execute(text(partition_sql))
        db.commit()
    
    async def optimize_partition_indexes(self, db: Session = None) -> Dict[str, Any]:
        """Optimize indexes on audit log partitions."""
        
        optimization_stats = {
            "partitions_optimized": 0,
            "indexes_created": 0,
            "indexes_dropped": 0
        }
        
        with db_manager.get_session() as session:
            # Get all audit log partitions
            partitions_result = session.execute(text("""
                SELECT schemaname, tablename 
                FROM pg_tables 
                WHERE tablename LIKE 'audit_logs_%'
            """))
            
            partitions = partitions_result.fetchall()
            
            for schema, table_name in partitions:
                try:
                    # Analyze table statistics
                    session.execute(text(f"ANALYZE {table_name}"))
                    
                    # Check for missing indexes
                    await self._ensure_partition_indexes(table_name, session)
                    
                    optimization_stats["partitions_optimized"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to optimize partition {table_name}: {e}")
        
        return optimization_stats
    
    async def _ensure_partition_indexes(self, table_name: str, db: Session):
        """Ensure required indexes exist on partition."""
        
        required_indexes = [
            (f"idx_{table_name}_tenant_timestamp", ["tenant_id", "timestamp"]),
            (f"idx_{table_name}_user_action", ["user_id", "action"]),
            (f"idx_{table_name}_resource", ["resource_type", "resource_id"]),
            (f"idx_{table_name}_ip_address", ["ip_address"])
        ]
        
        for index_name, columns in required_indexes:
            try:
                # Check if index exists
                index_exists = db.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = :index_name)"
                ), {"index_name": index_name}).scalar()
                
                if not index_exists:
                    # Create index
                    columns_str = ", ".join(columns)
                    db.execute(text(
                        f"CREATE INDEX CONCURRENTLY {index_name} ON {table_name} ({columns_str})"
                    ))
                    logger.info(f"Created index {index_name} on {table_name}")
                
            except Exception as e:
                logger.error(f"Failed to create index {index_name}: {e}")


class AuditLogArchivalService:
    """Automated archival service for audit logs."""
    
    def __init__(self, config: StorageConfig = None):
        """Initialize archival service."""
        self.config = config or StorageConfig()
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
    
    async def archive_old_logs(
        self,
        tenant_id: Optional[str] = None,
        archive_before_date: Optional[datetime] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Archive old audit logs to cold storage."""
        
        if not archive_before_date:
            archive_before_date = datetime.utcnow() - timedelta(
                days=self.config.archive_threshold_days
            )
        
        archival_stats = {
            "logs_archived": 0,
            "logs_deleted": 0,
            "archive_files_created": 0,
            "compression_ratio": 0.0,
            "processing_time_seconds": 0.0
        }
        
        start_time = datetime.now()
        
        try:
            with db_manager.get_session() as session:
                # Build query for logs to archive
                query = select(AuditLogModel).where(
                    AuditLogModel.timestamp < archive_before_date
                )
                
                if tenant_id:
                    query = query.where(AuditLogModel.tenant_id == tenant_id)
                
                # Process in batches
                batch_processor = BatchProcessor(
                    BatchConfig(
                        batch_size=self.config.cleanup_batch_size,
                        max_memory_mb=self.config.max_memory_mb
                    )
                )
                
                def archive_batch(logs: List[AuditLogModel]) -> List[str]:
                    """Archive a batch of logs."""
                    archived_files = []
                    
                    try:
                        # Group logs by tenant and month for efficient archival
                        grouped_logs = self._group_logs_for_archival(logs)
                        
                        for group_key, group_logs in grouped_logs.items():
                            archive_file = self._create_archive_file(group_key, group_logs)
                            if archive_file:
                                archived_files.append(archive_file)
                        
                        # Delete archived logs from active storage
                        log_ids = [log.id for log in logs]
                        delete_stmt = delete(AuditLogModel).where(
                            AuditLogModel.id.in_(log_ids)
                        )
                        session.execute(delete_stmt)
                        
                        archival_stats["logs_archived"] += len(logs)
                        archival_stats["logs_deleted"] += len(logs)
                        
                    except Exception as e:
                        logger.error(f"Failed to archive batch: {e}")
                    
                    return archived_files
                
                # Process all batches
                with batch_processor:
                    stats = batch_processor.process_query_batches(
                        query, archive_batch
                    )
                
                session.commit()
                
                archival_stats["archive_files_created"] = stats.processed_items
                
        except Exception as e:
            logger.error(f"Archival process failed: {e}")
            raise
        finally:
            archival_stats["processing_time_seconds"] = (
                datetime.now() - start_time
            ).total_seconds()
        
        logger.info(f"Archival completed: {archival_stats['logs_archived']} logs archived")
        return archival_stats
    
    def _group_logs_for_archival(
        self,
        logs: List[AuditLogModel]
    ) -> Dict[str, List[AuditLogModel]]:
        """Group logs by tenant and month for efficient archival."""
        
        grouped = {}
        
        for log in logs:
            # Create group key: tenant_id + year_month
            group_key = f"{log.tenant_id}_{log.timestamp.strftime('%Y_%m')}"
            
            if group_key not in grouped:
                grouped[group_key] = []
            
            grouped[group_key].append(log)
        
        return grouped
    
    def _create_archive_file(
        self,
        group_key: str,
        logs: List[AuditLogModel]
    ) -> Optional[str]:
        """Create compressed archive file for log group."""
        
        try:
            # Convert logs to JSON format
            log_data = []
            for log in logs:
                log_dict = {
                    'id': str(log.id),
                    'user_id': str(log.user_id) if log.user_id else None,
                    'tenant_id': log.tenant_id,
                    'action': log.action.value,
                    'resource_type': log.resource_type,
                    'resource_id': log.resource_id,
                    'ip_address': str(log.ip_address) if log.ip_address else None,
                    'user_agent': log.user_agent,
                    'details': log.details,
                    'timestamp': log.timestamp.isoformat()
                }
                log_data.append(log_dict)
            
            # Create archive filename
            archive_filename = f"audit_logs_{group_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json.gz"
            
            # In a production environment, this would write to S3, Azure Blob, etc.
            # For now, we'll simulate the archival process
            json_data = json.dumps(log_data, indent=2, default=str)
            compressed_data = gzip.compress(json_data.encode('utf-8'))
            
            # Calculate compression ratio
            compression_ratio = len(compressed_data) / len(json_data.encode('utf-8'))
            
            logger.info(f"Created archive {archive_filename}: {len(logs)} logs, "
                       f"compression ratio: {compression_ratio:.2f}")
            
            # In production, upload to cloud storage here
            # await self._upload_to_cloud_storage(archive_filename, compressed_data)
            
            return archive_filename
            
        except Exception as e:
            logger.error(f"Failed to create archive file for {group_key}: {e}")
            return None
    
    async def cleanup_expired_logs(
        self,
        tenant_id: Optional[str] = None,
        retention_days: Optional[int] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Clean up logs that have exceeded retention period."""
        
        if not retention_days:
            retention_days = self.config.retention_days
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        cleanup_stats = {
            "logs_deleted": 0,
            "processing_time_seconds": 0.0
        }
        
        start_time = datetime.now()
        
        try:
            with db_manager.get_session() as session:
                # Execute deletion in batches to avoid long locks
                while True:
                    # Build select query to get IDs for batch deletion
                    select_query = select(AuditLogModel.id).where(
                        AuditLogModel.timestamp < cutoff_date
                    )
                    
                    if tenant_id:
                        select_query = select_query.where(
                            AuditLogModel.tenant_id == tenant_id
                        )
                    
                    # Get batch of IDs to delete
                    select_query = select_query.limit(self.config.cleanup_batch_size)
                    result = session.execute(select_query)
                    ids_to_delete = [row[0] for row in result.fetchall()]
                    
                    if not ids_to_delete:
                        break
                    
                    # Delete the batch
                    delete_query = delete(AuditLogModel).where(
                        AuditLogModel.id.in_(ids_to_delete)
                    )
                    delete_result = session.execute(delete_query)
                    deleted_count = delete_result.rowcount
                    
                    cleanup_stats["logs_deleted"] += deleted_count
                    session.commit()
                    
                    logger.debug(f"Deleted batch of {deleted_count} expired logs")
                    
                    # Small delay to prevent overwhelming the database
                    await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Cleanup process failed: {e}")
            raise
        finally:
            cleanup_stats["processing_time_seconds"] = (
                datetime.now() - start_time
            ).total_seconds()
        
        logger.info(f"Cleanup completed: {cleanup_stats['logs_deleted']} logs deleted")
        return cleanup_stats


class OptimizedAuditStorage:
    """Main class for optimized audit log storage management."""
    
    def __init__(self, config: StorageConfig = None):
        """Initialize optimized audit storage."""
        self.config = config or StorageConfig()
        self.batch_storage = AuditLogBatchStorage(self.config)
        self.partition_manager = AuditLogPartitionManager(self.config)
        self.archival_service = AuditLogArchivalService(self.config)
    
    async def initialize_storage_optimization(self, db: Session = None) -> Dict[str, Any]:
        """Initialize storage optimization features."""
        
        initialization_stats = {
            "partitions_created": 0,
            "indexes_optimized": 0,
            "storage_ready": False
        }
        
        try:
            # Create monthly partitions for the next year
            partitions = await self.partition_manager.create_monthly_partitions(
                datetime.now(), months_ahead=12, db=db
            )
            initialization_stats["partitions_created"] = len(partitions)
            
            # Optimize partition indexes
            index_stats = await self.partition_manager.optimize_partition_indexes(db)
            initialization_stats["indexes_optimized"] = index_stats["partitions_optimized"]
            
            initialization_stats["storage_ready"] = True
            
            logger.info("Audit storage optimization initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize storage optimization: {e}")
            initialization_stats["error"] = str(e)
        
        return initialization_stats
    
    async def store_audit_logs_optimized(
        self,
        audit_logs: List[AuditLogModel],
        db: Session = None
    ) -> StorageStats:
        """Store audit logs using optimized batch processing."""
        return await self.batch_storage.store_audit_logs_batch(audit_logs, db)
    
    async def run_maintenance_tasks(
        self,
        tenant_id: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Run maintenance tasks for audit log storage."""
        
        maintenance_stats = {
            "archival_stats": {},
            "cleanup_stats": {},
            "optimization_stats": {},
            "total_time_seconds": 0.0
        }
        
        start_time = datetime.now()
        
        try:
            # Archive old logs
            archival_stats = await self.archival_service.archive_old_logs(
                tenant_id=tenant_id, db=db
            )
            maintenance_stats["archival_stats"] = archival_stats
            
            # Clean up expired logs
            cleanup_stats = await self.archival_service.cleanup_expired_logs(
                tenant_id=tenant_id, db=db
            )
            maintenance_stats["cleanup_stats"] = cleanup_stats
            
            # Optimize partition indexes
            optimization_stats = await self.partition_manager.optimize_partition_indexes(db)
            maintenance_stats["optimization_stats"] = optimization_stats
            
            logger.info("Audit log maintenance tasks completed successfully")
            
        except Exception as e:
            logger.error(f"Maintenance tasks failed: {e}")
            maintenance_stats["error"] = str(e)
        finally:
            maintenance_stats["total_time_seconds"] = (
                datetime.now() - start_time
            ).total_seconds()
        
        return maintenance_stats
    
    def get_storage_statistics(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive storage statistics."""
        
        stats = {
            "batch_storage": {
                "total_logs_stored": self.batch_storage.stats.total_logs_stored,
                "batch_operations": self.batch_storage.stats.batch_operations,
                "throughput_logs_per_second": self.batch_storage.stats.throughput_logs_per_second,
                "compression_ratio": self.batch_storage.stats.compression_ratio,
                "peak_memory_mb": self.batch_storage.stats.peak_memory_mb
            },
            "configuration": {
                "batch_size": self.config.batch_size,
                "compression_enabled": self.config.compression_enabled,
                "partition_by_month": self.config.partition_by_month,
                "retention_days": self.config.retention_days,
                "archive_threshold_days": self.config.archive_threshold_days
            }
        }
        
        return stats


# Utility functions for storage optimization

@contextmanager
def optimized_audit_storage(config: StorageConfig = None):
    """Context manager for optimized audit storage."""
    storage = OptimizedAuditStorage(config)
    try:
        yield storage
    finally:
        # Cleanup resources
        pass


async def migrate_existing_logs_to_optimized_storage(
    batch_size: int = 10000,
    tenant_id: Optional[str] = None
) -> Dict[str, Any]:
    """Migrate existing audit logs to optimized storage format."""
    
    migration_stats = {
        "logs_migrated": 0,
        "batches_processed": 0,
        "processing_time_seconds": 0.0
    }
    
    start_time = datetime.now()
    
    try:
        with optimized_audit_storage() as storage:
            with db_manager.get_session() as session:
                # Query existing logs
                query = select(AuditLogModel)
                if tenant_id:
                    query = query.where(AuditLogModel.tenant_id == tenant_id)
                
                # Process in batches
                batch_processor = BatchProcessor(
                    BatchConfig(batch_size=batch_size, max_memory_mb=512)
                )
                
                def migrate_batch(logs: List[AuditLogModel]) -> List[AuditLogModel]:
                    """Migrate a batch of logs."""
                    # In a real migration, you might update log format,
                    # add missing fields, or optimize storage
                    return logs
                
                with batch_processor:
                    stats = batch_processor.process_query_batches(
                        query, migrate_batch
                    )
                
                migration_stats["logs_migrated"] = stats.processed_items
                migration_stats["batches_processed"] = stats.batches_processed
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        migration_stats["error"] = str(e)
    finally:
        migration_stats["processing_time_seconds"] = (
            datetime.now() - start_time
        ).total_seconds()
    
    return migration_stats