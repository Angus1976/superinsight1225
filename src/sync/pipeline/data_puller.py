"""
Data Puller for Data Sync Pipeline.

Supports scheduled/incremental data pulling with checkpoints and retry mechanism.
"""

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import logging

from src.sync.pipeline.enums import DatabaseType
from src.sync.pipeline.schemas import (
    DataSourceConfig,
    DataPage,
    PullConfig,
    Checkpoint,
    PullResult,
)
from src.sync.pipeline.data_reader import DataReader
from src.sync.pipeline.checkpoint_store import CheckpointStore

logger = logging.getLogger(__name__)


class CronExpressionError(Exception):
    """Raised when cron expression is invalid."""
    pass


class DataPuller:
    """
    Data Puller for scheduled and incremental data pulling.
    
    Features:
    - Scheduled pulling with cron expressions
    - Incremental pulling with checkpoints
    - Automatic retry on failure
    - Parallel pulling from multiple sources
    """
    
    def __init__(
        self,
        data_reader: DataReader,
        checkpoint_store: CheckpointStore
    ):
        """
        Initialize the Data Puller.
        
        Args:
            data_reader: DataReader instance for reading data
            checkpoint_store: CheckpointStore for managing checkpoints
        """
        self.data_reader = data_reader
        self.checkpoint_store = checkpoint_store
    
    async def pull(
        self,
        source_id: str,
        config: PullConfig,
        data_source_config: DataSourceConfig
    ) -> PullResult:
        """
        Execute a full data pull.
        
        Args:
            source_id: ID of the data source
            config: Pull configuration
            data_source_config: Data source connection config
            
        Returns:
            PullResult with pull status and statistics
        """
        try:
            # Validate cron expression
            self._validate_cron_expression(config.cron_expression)
            
            # Connect to data source
            await self.data_reader.connect(data_source_config)
            
            # Build query
            if config.query:
                query = config.query
            elif config.table_name:
                query = f"SELECT * FROM {config.table_name}"
            else:
                raise ValueError("Either query or table_name must be provided")
            
            # Execute pull
            rows_pulled = 0
            last_value = None
            
            async for page in self.data_reader.read_by_query(
                query, config.page_size
            ):
                rows_pulled += page.row_count
                
                # Track last value for checkpoint
                if page.rows and config.checkpoint_field:
                    last_row = page.rows[-1]
                    if config.checkpoint_field in last_row:
                        last_value = last_row[config.checkpoint_field]
            
            # Save checkpoint
            checkpoint = Checkpoint(
                source_id=source_id,
                last_value=last_value,
                last_pull_at=datetime.utcnow(),
                rows_pulled=rows_pulled
            )
            await self.checkpoint_store.save(checkpoint)
            
            return PullResult(
                source_id=source_id,
                success=True,
                rows_pulled=rows_pulled,
                checkpoint=checkpoint
            )
            
        except Exception as e:
            logger.error(f"Pull failed for source {source_id}: {str(e)}")
            return PullResult(
                source_id=source_id,
                success=False,
                rows_pulled=0,
                error_message=str(e)
            )
        finally:
            await self.data_reader.disconnect()
    
    async def pull_incremental(
        self,
        source_id: str,
        config: PullConfig,
        data_source_config: DataSourceConfig
    ) -> PullResult:
        """
        Execute an incremental data pull based on checkpoint.
        
        Args:
            source_id: ID of the data source
            config: Pull configuration
            data_source_config: Data source connection config
            
        Returns:
            PullResult with pull status and statistics
        """
        try:
            # Validate cron expression
            self._validate_cron_expression(config.cron_expression)
            
            # Get existing checkpoint
            checkpoint = await self.checkpoint_store.get(source_id)
            
            # Connect to data source
            await self.data_reader.connect(data_source_config)
            
            # Build incremental query
            if config.query:
                base_query = config.query
            elif config.table_name:
                base_query = f"SELECT * FROM {config.table_name}"
            else:
                raise ValueError("Either query or table_name must be provided")
            
            # Add incremental filter if checkpoint exists
            if checkpoint and checkpoint.last_value:
                # Determine if we need quotes based on value type
                if isinstance(checkpoint.last_value, str):
                    filter_value = f"'{checkpoint.last_value}'"
                else:
                    filter_value = str(checkpoint.last_value)
                
                if "WHERE" in base_query.upper():
                    query = f"{base_query} AND {config.checkpoint_field} > {filter_value}"
                else:
                    query = f"{base_query} WHERE {config.checkpoint_field} > {filter_value}"
            else:
                query = base_query
            
            # Execute pull
            rows_pulled = 0
            last_value = checkpoint.last_value if checkpoint else None
            
            async for page in self.data_reader.read_by_query(
                query, config.page_size
            ):
                rows_pulled += page.row_count
                
                # Track last value for checkpoint
                if page.rows and config.checkpoint_field:
                    last_row = page.rows[-1]
                    if config.checkpoint_field in last_row:
                        last_value = last_row[config.checkpoint_field]
            
            # Update checkpoint
            new_checkpoint = await self.checkpoint_store.update_last_value(
                source_id, last_value, rows_pulled
            )
            
            return PullResult(
                source_id=source_id,
                success=True,
                rows_pulled=rows_pulled,
                checkpoint=new_checkpoint
            )
            
        except Exception as e:
            logger.error(f"Incremental pull failed for source {source_id}: {str(e)}")
            return PullResult(
                source_id=source_id,
                success=False,
                rows_pulled=0,
                error_message=str(e)
            )
        finally:
            await self.data_reader.disconnect()
    
    async def save_checkpoint(self, source_id: str, checkpoint: Checkpoint) -> None:
        """
        Save a checkpoint manually.
        
        Args:
            source_id: ID of the data source
            checkpoint: Checkpoint to save
        """
        await self.checkpoint_store.save(checkpoint)
    
    async def resume_from_checkpoint(
        self,
        source_id: str,
        config: PullConfig,
        data_source_config: DataSourceConfig
    ) -> PullResult:
        """
        Resume pulling from the last checkpoint.
        
        Args:
            source_id: ID of the data source
            config: Pull configuration
            data_source_config: Data source connection config
            
        Returns:
            PullResult with pull status
        """
        # This is essentially the same as incremental pull
        return await self.pull_incremental(source_id, config, data_source_config)
    
    async def pull_with_retry(
        self,
        source_id: str,
        config: PullConfig,
        data_source_config: DataSourceConfig,
        max_retries: int = 3
    ) -> PullResult:
        """
        Execute a pull with automatic retry on failure.
        
        Args:
            source_id: ID of the data source
            config: Pull configuration
            data_source_config: Data source connection config
            max_retries: Maximum number of retry attempts (default 3)
            
        Returns:
            PullResult with retry count
        """
        retries = 0
        last_error = None
        
        while retries <= max_retries:
            if config.incremental:
                result = await self.pull_incremental(
                    source_id, config, data_source_config
                )
            else:
                result = await self.pull(source_id, config, data_source_config)
            
            if result.success:
                result.retries_used = retries
                return result
            
            last_error = result.error_message
            retries += 1
            
            if retries <= max_retries:
                # Exponential backoff
                wait_time = 2 ** retries
                logger.warning(
                    f"Pull failed for {source_id}, retrying in {wait_time}s "
                    f"(attempt {retries}/{max_retries})"
                )
                await asyncio.sleep(wait_time)
        
        return PullResult(
            source_id=source_id,
            success=False,
            rows_pulled=0,
            error_message=f"Failed after {max_retries} retries: {last_error}",
            retries_used=retries
        )
    
    async def pull_parallel(
        self,
        source_configs: List[Tuple[str, PullConfig, DataSourceConfig]]
    ) -> List[PullResult]:
        """
        Pull from multiple data sources in parallel.
        
        Args:
            source_configs: List of (source_id, pull_config, data_source_config) tuples
            
        Returns:
            List of PullResult for each source
        """
        tasks = []
        
        for source_id, pull_config, data_source_config in source_configs:
            # Create a new DataReader for each parallel pull
            reader = DataReader()
            puller = DataPuller(reader, self.checkpoint_store)
            
            if pull_config.incremental:
                task = puller.pull_incremental(
                    source_id, pull_config, data_source_config
                )
            else:
                task = puller.pull(source_id, pull_config, data_source_config)
            
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source_id = source_configs[i][0]
                final_results.append(PullResult(
                    source_id=source_id,
                    success=False,
                    rows_pulled=0,
                    error_message=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def _validate_cron_expression(self, cron_expression: str) -> None:
        """
        Validate a cron expression.
        
        Args:
            cron_expression: Cron expression to validate
            
        Raises:
            CronExpressionError: If expression is invalid
        """
        # Basic cron expression pattern (5 or 6 fields)
        # minute hour day month weekday [year]
        parts = cron_expression.strip().split()
        
        if len(parts) < 5 or len(parts) > 6:
            raise CronExpressionError(
                f"Invalid cron expression: expected 5-6 fields, got {len(parts)}"
            )
        
        # Validate each field
        field_ranges = [
            (0, 59),   # minute
            (0, 23),   # hour
            (1, 31),   # day
            (1, 12),   # month
            (0, 6),    # weekday
        ]
        
        for i, (part, (min_val, max_val)) in enumerate(zip(parts[:5], field_ranges)):
            if not self._validate_cron_field(part, min_val, max_val):
                raise CronExpressionError(
                    f"Invalid cron field at position {i}: {part}"
                )
        
        # Check minimum interval (1 minute)
        # If minute field is not *, check it's not running more than once per minute
        minute_field = parts[0]
        if minute_field != "*" and "/" in minute_field:
            # Check step value
            step = minute_field.split("/")[-1]
            if step.isdigit() and int(step) < 1:
                raise CronExpressionError(
                    "Minimum interval is 1 minute"
                )
    
    def _validate_cron_field(
        self,
        field: str,
        min_val: int,
        max_val: int
    ) -> bool:
        """
        Validate a single cron field.
        
        Args:
            field: Cron field value
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            True if valid
        """
        # Handle special characters
        if field == "*":
            return True
        
        # Handle step values (*/5, 1-10/2)
        if "/" in field:
            base, step = field.split("/", 1)
            if not step.isdigit():
                return False
            field = base
        
        # Handle ranges (1-5)
        if "-" in field:
            parts = field.split("-")
            if len(parts) != 2:
                return False
            try:
                start, end = int(parts[0]), int(parts[1])
                return min_val <= start <= max_val and min_val <= end <= max_val
            except ValueError:
                return False
        
        # Handle lists (1,2,3)
        if "," in field:
            parts = field.split(",")
            for part in parts:
                if not self._validate_cron_field(part.strip(), min_val, max_val):
                    return False
            return True
        
        # Handle single value
        if field == "*":
            return True
        
        try:
            value = int(field)
            return min_val <= value <= max_val
        except ValueError:
            return False
