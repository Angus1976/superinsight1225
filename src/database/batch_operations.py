"""
Batch database operations module for SuperInsight Platform.

Provides efficient bulk insert and update operations with configurable batch sizes.
Implements Requirement 9.2 for database query optimization.

i18n Translation Keys:
- database.batch.insert_started: 批量插入开始: {count} 条记录
- database.batch.insert_completed: 批量插入完成: {count} 条记录, 耗时 {duration}ms
- database.batch.update_started: 批量更新开始: {count} 条记录
- database.batch.update_completed: 批量更新完成: {count} 条记录, 耗时 {duration}ms
- database.batch.upsert_started: 批量插入或更新开始: {count} 条记录
- database.batch.upsert_completed: 批量插入或更新完成: {count} 条记录, 耗时 {duration}ms
- database.error.batch_failed: 批量操作失败: {error}
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Callable
from uuid import uuid4

from sqlalchemy import insert, update, select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar('T')


class OnConflictStrategy(str, Enum):
    """Strategy for handling conflicts during upsert operations."""
    IGNORE = "ignore"      # Skip conflicting records
    UPDATE = "update"      # Update conflicting records
    ERROR = "error"        # Raise error on conflict


@dataclass
class BatchConfig:
    """Configuration for batch operations.
    
    Attributes:
        batch_size: Number of records per batch (default: 1000)
        return_ids: Whether to return inserted IDs (default: True)
        on_conflict: Strategy for handling conflicts (default: ignore)
        timeout_seconds: Timeout for batch operations (default: None)
    """
    batch_size: int = 1000
    return_ids: bool = True
    on_conflict: OnConflictStrategy = OnConflictStrategy.IGNORE
    timeout_seconds: Optional[int] = None


@dataclass
class BatchResult:
    """Result of a batch operation.
    
    Attributes:
        success_count: Number of successfully processed records
        failed_count: Number of failed records
        total_count: Total number of records attempted
        duration_ms: Duration of the operation in milliseconds
        ids: List of IDs for inserted/updated records (if return_ids=True)
        errors: List of error messages for failed records
    """
    success_count: int = 0
    failed_count: int = 0
    total_count: int = 0
    duration_ms: float = 0.0
    ids: List[Any] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_count == 0:
            return 100.0
        return (self.success_count / self.total_count) * 100


class BatchOperations:
    """Batch database operations utility class.
    
    Provides efficient bulk insert, update, and upsert operations
    with configurable batch sizes and conflict handling.
    
    Example:
        ```python
        async with AsyncSession(engine) as session:
            batch_ops = BatchOperations(session)
            result = await batch_ops.bulk_insert(
                UserModel,
                [{"name": "Alice"}, {"name": "Bob"}],
                batch_size=100
            )
            print(f"Inserted {result.success_count} records")
        ```
    """
    
    def __init__(
        self,
        session: AsyncSession,
        config: Optional[BatchConfig] = None
    ):
        """Initialize BatchOperations.
        
        Args:
            session: SQLAlchemy async session
            config: Optional batch configuration
        """
        self.session = session
        self.config = config or BatchConfig()
    
    async def bulk_insert(
        self,
        model: Type[T],
        records: List[Dict[str, Any]],
        batch_size: Optional[int] = None
    ) -> BatchResult:
        """Bulk insert records into the database.
        
        Args:
            model: SQLAlchemy model class
            records: List of dictionaries containing record data
            batch_size: Optional override for batch size
            
        Returns:
            BatchResult with operation statistics
            
        Raises:
            Exception: If batch operation fails and on_conflict is ERROR
        """
        if not records:
            return BatchResult(total_count=0)
        
        batch_size = batch_size or self.config.batch_size
        total_count = len(records)
        
        # Log start - i18n key: database.batch.insert_started
        logger.info(
            f"database.batch.insert_started: count={total_count}",
            extra={"count": total_count}
        )
        
        start_time = time.time()
        result = BatchResult(total_count=total_count)
        
        try:
            # Process in batches
            for i in range(0, total_count, batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    # Add default ID if not present
                    for record in batch:
                        if 'id' not in record:
                            record['id'] = str(uuid4())
                    
                    # Execute bulk insert
                    stmt = insert(model).values(batch)
                    
                    if self.config.return_ids:
                        stmt = stmt.returning(model.id)
                        batch_result = await self.session.execute(stmt)
                        inserted_ids = [row[0] for row in batch_result.fetchall()]
                        result.ids.extend(inserted_ids)
                    else:
                        await self.session.execute(stmt)
                    
                    result.success_count += len(batch)
                    
                except Exception as e:
                    error_msg = f"Batch {i // batch_size + 1} failed: {str(e)}"
                    logger.error(
                        f"database.error.batch_failed: error={error_msg}",
                        extra={"error": error_msg}
                    )
                    result.errors.append(error_msg)
                    result.failed_count += len(batch)
                    
                    if self.config.on_conflict == OnConflictStrategy.ERROR:
                        raise
            
            # Commit the transaction
            await self.session.commit()
            
        except Exception as e:
            await self.session.rollback()
            if self.config.on_conflict == OnConflictStrategy.ERROR:
                raise
        
        # Calculate duration
        result.duration_ms = (time.time() - start_time) * 1000
        
        # Log completion - i18n key: database.batch.insert_completed
        logger.info(
            f"database.batch.insert_completed: count={result.success_count}, duration={result.duration_ms:.2f}ms",
            extra={"count": result.success_count, "duration": result.duration_ms}
        )
        
        return result
    
    async def bulk_update(
        self,
        model: Type[T],
        records: List[Dict[str, Any]],
        key_field: str = "id",
        batch_size: Optional[int] = None
    ) -> BatchResult:
        """Bulk update records in the database.
        
        Args:
            model: SQLAlchemy model class
            records: List of dictionaries containing record data with key field
            key_field: Field to use for matching records (default: "id")
            batch_size: Optional override for batch size
            
        Returns:
            BatchResult with operation statistics
        """
        if not records:
            return BatchResult(total_count=0)
        
        batch_size = batch_size or self.config.batch_size
        total_count = len(records)
        
        # Log start - i18n key: database.batch.update_started
        logger.info(
            f"database.batch.update_started: count={total_count}",
            extra={"count": total_count}
        )
        
        start_time = time.time()
        result = BatchResult(total_count=total_count)
        
        try:
            # Process in batches
            for i in range(0, total_count, batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    # Update each record individually within the batch
                    for record in batch:
                        key_value = record.get(key_field)
                        if key_value is None:
                            result.failed_count += 1
                            result.errors.append(f"Missing key field '{key_field}' in record")
                            continue
                        
                        # Build update values (exclude key field)
                        update_values = {k: v for k, v in record.items() if k != key_field}
                        
                        if not update_values:
                            result.failed_count += 1
                            result.errors.append(f"No fields to update for record with {key_field}={key_value}")
                            continue
                        
                        # Execute update
                        stmt = (
                            update(model)
                            .where(getattr(model, key_field) == key_value)
                            .values(**update_values)
                        )
                        await self.session.execute(stmt)
                        result.success_count += 1
                        
                        if self.config.return_ids:
                            result.ids.append(key_value)
                    
                except Exception as e:
                    error_msg = f"Batch {i // batch_size + 1} failed: {str(e)}"
                    logger.error(
                        f"database.error.batch_failed: error={error_msg}",
                        extra={"error": error_msg}
                    )
                    result.errors.append(error_msg)
                    result.failed_count += len(batch)
                    
                    if self.config.on_conflict == OnConflictStrategy.ERROR:
                        raise
            
            # Commit the transaction
            await self.session.commit()
            
        except Exception as e:
            await self.session.rollback()
            if self.config.on_conflict == OnConflictStrategy.ERROR:
                raise
        
        # Calculate duration
        result.duration_ms = (time.time() - start_time) * 1000
        
        # Log completion - i18n key: database.batch.update_completed
        logger.info(
            f"database.batch.update_completed: count={result.success_count}, duration={result.duration_ms:.2f}ms",
            extra={"count": result.success_count, "duration": result.duration_ms}
        )
        
        return result
    
    async def bulk_upsert(
        self,
        model: Type[T],
        records: List[Dict[str, Any]],
        key_fields: List[str],
        update_fields: Optional[List[str]] = None,
        batch_size: Optional[int] = None
    ) -> BatchResult:
        """Bulk insert or update records (upsert).
        
        Uses PostgreSQL's ON CONFLICT clause for efficient upsert operations.
        
        Args:
            model: SQLAlchemy model class
            records: List of dictionaries containing record data
            key_fields: Fields to use for conflict detection
            update_fields: Fields to update on conflict (default: all non-key fields)
            batch_size: Optional override for batch size
            
        Returns:
            BatchResult with operation statistics
        """
        if not records:
            return BatchResult(total_count=0)
        
        batch_size = batch_size or self.config.batch_size
        total_count = len(records)
        
        # Log start - i18n key: database.batch.upsert_started
        logger.info(
            f"database.batch.upsert_started: count={total_count}",
            extra={"count": total_count}
        )
        
        start_time = time.time()
        result = BatchResult(total_count=total_count)
        
        try:
            # Process in batches
            for i in range(0, total_count, batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    # Add default ID if not present and 'id' is a key field
                    for record in batch:
                        if 'id' not in record and 'id' in key_fields:
                            record['id'] = str(uuid4())
                    
                    # Build upsert statement using PostgreSQL dialect
                    stmt = pg_insert(model).values(batch)
                    
                    # Determine fields to update on conflict
                    if update_fields is None:
                        # Update all fields except key fields
                        all_fields = set(batch[0].keys()) if batch else set()
                        update_fields_set = all_fields - set(key_fields)
                    else:
                        update_fields_set = set(update_fields)
                    
                    # Build update dict for ON CONFLICT
                    update_dict = {
                        field: getattr(stmt.excluded, field)
                        for field in update_fields_set
                        if hasattr(stmt.excluded, field)
                    }
                    
                    if self.config.on_conflict == OnConflictStrategy.IGNORE:
                        stmt = stmt.on_conflict_do_nothing(index_elements=key_fields)
                    elif self.config.on_conflict == OnConflictStrategy.UPDATE and update_dict:
                        stmt = stmt.on_conflict_do_update(
                            index_elements=key_fields,
                            set_=update_dict
                        )
                    
                    if self.config.return_ids:
                        stmt = stmt.returning(model.id)
                        batch_result = await self.session.execute(stmt)
                        upserted_ids = [row[0] for row in batch_result.fetchall()]
                        result.ids.extend(upserted_ids)
                    else:
                        await self.session.execute(stmt)
                    
                    result.success_count += len(batch)
                    
                except Exception as e:
                    error_msg = f"Batch {i // batch_size + 1} failed: {str(e)}"
                    logger.error(
                        f"database.error.batch_failed: error={error_msg}",
                        extra={"error": error_msg}
                    )
                    result.errors.append(error_msg)
                    result.failed_count += len(batch)
                    
                    if self.config.on_conflict == OnConflictStrategy.ERROR:
                        raise
            
            # Commit the transaction
            await self.session.commit()
            
        except Exception as e:
            await self.session.rollback()
            if self.config.on_conflict == OnConflictStrategy.ERROR:
                raise
        
        # Calculate duration
        result.duration_ms = (time.time() - start_time) * 1000
        
        # Log completion - i18n key: database.batch.upsert_completed
        logger.info(
            f"database.batch.upsert_completed: count={result.success_count}, duration={result.duration_ms:.2f}ms",
            extra={"count": result.success_count, "duration": result.duration_ms}
        )
        
        return result
    
    async def bulk_delete(
        self,
        model: Type[T],
        ids: List[Any],
        key_field: str = "id",
        batch_size: Optional[int] = None
    ) -> BatchResult:
        """Bulk delete records from the database.
        
        Args:
            model: SQLAlchemy model class
            ids: List of IDs to delete
            key_field: Field to use for matching records (default: "id")
            batch_size: Optional override for batch size
            
        Returns:
            BatchResult with operation statistics
        """
        if not ids:
            return BatchResult(total_count=0)
        
        batch_size = batch_size or self.config.batch_size
        total_count = len(ids)
        
        logger.info(
            f"database.batch.delete_started: count={total_count}",
            extra={"count": total_count}
        )
        
        start_time = time.time()
        result = BatchResult(total_count=total_count)
        
        try:
            # Process in batches
            for i in range(0, total_count, batch_size):
                batch_ids = ids[i:i + batch_size]
                
                try:
                    from sqlalchemy import delete
                    stmt = delete(model).where(
                        getattr(model, key_field).in_(batch_ids)
                    )
                    await self.session.execute(stmt)
                    result.success_count += len(batch_ids)
                    
                except Exception as e:
                    error_msg = f"Batch {i // batch_size + 1} failed: {str(e)}"
                    logger.error(
                        f"database.error.batch_failed: error={error_msg}",
                        extra={"error": error_msg}
                    )
                    result.errors.append(error_msg)
                    result.failed_count += len(batch_ids)
            
            # Commit the transaction
            await self.session.commit()
            
        except Exception as e:
            await self.session.rollback()
            raise
        
        # Calculate duration
        result.duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"database.batch.delete_completed: count={result.success_count}, duration={result.duration_ms:.2f}ms",
            extra={"count": result.success_count, "duration": result.duration_ms}
        )
        
        return result


class SyncBatchOperations:
    """Synchronous batch operations for non-async contexts.
    
    Provides the same functionality as BatchOperations but for
    synchronous database sessions.
    """
    
    def __init__(
        self,
        session: Session,
        config: Optional[BatchConfig] = None
    ):
        """Initialize SyncBatchOperations.
        
        Args:
            session: SQLAlchemy synchronous session
            config: Optional batch configuration
        """
        self.session = session
        self.config = config or BatchConfig()
    
    def bulk_insert(
        self,
        model: Type[T],
        records: List[Dict[str, Any]],
        batch_size: Optional[int] = None
    ) -> BatchResult:
        """Synchronous bulk insert records into the database."""
        if not records:
            return BatchResult(total_count=0)
        
        batch_size = batch_size or self.config.batch_size
        total_count = len(records)
        
        logger.info(
            f"database.batch.insert_started: count={total_count}",
            extra={"count": total_count}
        )
        
        start_time = time.time()
        result = BatchResult(total_count=total_count)
        
        try:
            for i in range(0, total_count, batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    for record in batch:
                        if 'id' not in record:
                            record['id'] = str(uuid4())
                    
                    stmt = insert(model).values(batch)
                    
                    if self.config.return_ids:
                        stmt = stmt.returning(model.id)
                        batch_result = self.session.execute(stmt)
                        inserted_ids = [row[0] for row in batch_result.fetchall()]
                        result.ids.extend(inserted_ids)
                    else:
                        self.session.execute(stmt)
                    
                    result.success_count += len(batch)
                    
                except Exception as e:
                    error_msg = f"Batch {i // batch_size + 1} failed: {str(e)}"
                    logger.error(f"database.error.batch_failed: error={error_msg}")
                    result.errors.append(error_msg)
                    result.failed_count += len(batch)
                    
                    if self.config.on_conflict == OnConflictStrategy.ERROR:
                        raise
            
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            if self.config.on_conflict == OnConflictStrategy.ERROR:
                raise
        
        result.duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"database.batch.insert_completed: count={result.success_count}, duration={result.duration_ms:.2f}ms",
            extra={"count": result.success_count, "duration": result.duration_ms}
        )
        
        return result
    
    def bulk_update(
        self,
        model: Type[T],
        records: List[Dict[str, Any]],
        key_field: str = "id",
        batch_size: Optional[int] = None
    ) -> BatchResult:
        """Synchronous bulk update records in the database."""
        if not records:
            return BatchResult(total_count=0)
        
        batch_size = batch_size or self.config.batch_size
        total_count = len(records)
        
        logger.info(
            f"database.batch.update_started: count={total_count}",
            extra={"count": total_count}
        )
        
        start_time = time.time()
        result = BatchResult(total_count=total_count)
        
        try:
            for i in range(0, total_count, batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    for record in batch:
                        key_value = record.get(key_field)
                        if key_value is None:
                            result.failed_count += 1
                            result.errors.append(f"Missing key field '{key_field}' in record")
                            continue
                        
                        update_values = {k: v for k, v in record.items() if k != key_field}
                        
                        if not update_values:
                            result.failed_count += 1
                            continue
                        
                        stmt = (
                            update(model)
                            .where(getattr(model, key_field) == key_value)
                            .values(**update_values)
                        )
                        self.session.execute(stmt)
                        result.success_count += 1
                        
                        if self.config.return_ids:
                            result.ids.append(key_value)
                    
                except Exception as e:
                    error_msg = f"Batch {i // batch_size + 1} failed: {str(e)}"
                    logger.error(f"database.error.batch_failed: error={error_msg}")
                    result.errors.append(error_msg)
                    result.failed_count += len(batch)
                    
                    if self.config.on_conflict == OnConflictStrategy.ERROR:
                        raise
            
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            if self.config.on_conflict == OnConflictStrategy.ERROR:
                raise
        
        result.duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"database.batch.update_completed: count={result.success_count}, duration={result.duration_ms:.2f}ms",
            extra={"count": result.success_count, "duration": result.duration_ms}
        )
        
        return result
