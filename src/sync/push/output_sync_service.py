"""
Output Sync Service.

Handles output sync execution for writing AI-friendly data back to customer
target databases. Supports full/incremental strategies, data validation,
and checkpoint resume.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import db_manager
from src.sync.models import (
    SyncJobModel,
    SyncExecutionModel,
    SyncExecutionStatus,
    DataSourceModel,
)
from src.sync.transformer.field_mapper import FieldMapper, MappedData, ValidationError
from src.sync.push.incremental_push import (
    IncrementalPushService,
    ChangeRecord,
    PushTarget,
    PushResult,
)
from src.sync.push.connection_test_service import (
    ConnectionTestService,
    ConnectionStatus,
    ConnectionTestResult
)

logger = logging.getLogger(__name__)


class SyncResult(BaseModel):
    """Result of an output sync execution."""
    execution_id: UUID
    job_id: UUID
    status: str  # success, failed, partial
    records_total: int
    records_written: int
    records_failed: int
    error_message: Optional[str] = None
    execution_time_ms: float
    checkpoint: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationResult(BaseModel):
    """Result of data validation."""
    is_valid: bool
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)


class OutputSyncService:
    """
    Output sync service for writing AI-friendly data to target databases.
    
    Features:
    - Full and incremental sync strategies
    - Pre-write data validation
    - Checkpoint-based resume for failed syncs
    - Reuses IncrementalPushService for push and retry logic
    """
    
    def __init__(self):
        self.field_mapper = FieldMapper()
        self.push_service = IncrementalPushService()
        self.connection_test_service = ConnectionTestService()
    
    async def execute_output_sync(
        self,
        job_id: UUID,
        strategy: Optional[str] = None
    ) -> SyncResult:
        """
        Execute output sync for a job.
        
        Args:
            job_id: Sync job identifier
            strategy: Sync strategy override (full/incremental)
            
        Returns:
            Sync result with execution metrics
        """
        start_time = datetime.utcnow()
        execution_id = uuid4()
        
        async with db_manager.get_session() as session:
            try:
                # Load sync job
                job = await self._load_sync_job(session, job_id)
                if not job:
                    raise ValueError(f"Sync job {job_id} not found")
                
                # Test target connection before proceeding
                if job.target_source_id:
                    connection_test = await self.connection_test_service.test_connection(
                        job.target_source_id
                    )
                    
                    if connection_test.status != ConnectionStatus.SUCCESS:
                        error_msg = (
                            f"Target connection failed: {connection_test.error_message}. "
                            f"Suggestions: {'; '.join(connection_test.troubleshooting_suggestions[:3])}"
                        )
                        raise ConnectionError(error_msg)
                
                # Determine sync strategy
                sync_strategy = strategy or job.output_sync_strategy or "full"
                
                # Create execution record
                execution = await self._create_execution_record(
                    session, job, execution_id, sync_strategy
                )
                
                # Load source data
                source_data = await self._load_source_data(
                    session, job, sync_strategy
                )
                
                # Apply field mapping
                mapped_data = self._apply_field_mapping(
                    source_data, job.field_mapping_rules
                )
                
                # Validate data before writing
                validation_result = self.validate_output_data(
                    mapped_data, job.field_mapping_rules
                )
                
                if not validation_result.is_valid:
                    raise ValueError(
                        f"Data validation failed: {validation_result.errors}"
                    )
                
                # Convert to change records for push service
                change_records = self._convert_to_change_records(
                    mapped_data, job
                )
                
                # Create push target from job configuration
                push_target = await self._create_push_target(session, job)
                
                # Execute push with retry
                push_result = await self.push_service.push_with_retry(
                    tenant_id=job.tenant_id,
                    changes=change_records,
                    target=push_target,
                    max_retries=job.max_retries
                )
                
                # Update execution record
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                await self._update_execution_record(
                    session,
                    execution,
                    push_result,
                    execution_time,
                    sync_strategy
                )
                
                # Update job checkpoint
                if sync_strategy == "incremental":
                    await self._update_checkpoint(session, job, source_data)
                
                await session.commit()
                
                return SyncResult(
                    execution_id=execution_id,
                    job_id=job_id,
                    status=push_result.status,
                    records_total=len(source_data),
                    records_written=push_result.records_pushed,
                    records_failed=push_result.records_failed,
                    error_message=push_result.error_message,
                    execution_time_ms=execution_time
                )
                
            except Exception as e:
                logger.error(f"Output sync failed for job {job_id}: {e}")
                await session.rollback()
                
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return SyncResult(
                    execution_id=execution_id,
                    job_id=job_id,
                    status="failed",
                    records_total=0,
                    records_written=0,
                    records_failed=0,
                    error_message=str(e),
                    execution_time_ms=execution_time
                )
    
    def validate_output_data(
        self,
        data: List[Dict[str, Any]],
        mapping: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate data before writing to target database.
        
        Args:
            data: Data records to validate
            mapping: Field mapping rules
            
        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []
        
        if not data:
            warnings.append({
                "type": "empty_dataset",
                "message": "No data to sync"
            })
            return ValidationResult(is_valid=True, warnings=warnings)
        
        # Extract target schema from mapping
        target_schema = self._extract_target_schema(mapping)
        
        # Validate each record
        for idx, record in enumerate(data):
            # Check required fields
            for field_name, field_config in target_schema.items():
                if field_config.get("required", False):
                    if field_name not in record or record[field_name] is None:
                        errors.append({
                            "record_index": idx,
                            "field": field_name,
                            "type": "missing_required_field",
                            "message": f"Required field '{field_name}' is missing"
                        })
            
            # Check field types
            for field_name, value in record.items():
                if field_name in target_schema:
                    expected_type = target_schema[field_name].get("type")
                    if expected_type and not self._validate_field_type(
                        value, expected_type
                    ):
                        errors.append({
                            "record_index": idx,
                            "field": field_name,
                            "type": "type_mismatch",
                            "message": f"Field '{field_name}' type mismatch. "
                                     f"Expected {expected_type}, got {type(value).__name__}",
                            "expected_type": expected_type,
                            "actual_type": type(value).__name__
                        })
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
    
    async def resume_from_checkpoint(
        self,
        job_id: UUID
    ) -> SyncResult:
        """
        Resume output sync from last checkpoint.
        
        Args:
            job_id: Sync job identifier
            
        Returns:
            Sync result with execution metrics
        """
        async with db_manager.get_session() as session:
            # Load sync job
            job = await self._load_sync_job(session, job_id)
            if not job:
                raise ValueError(f"Sync job {job_id} not found")
            
            # Check if checkpoint exists
            if not job.output_checkpoint:
                logger.info(f"No checkpoint found for job {job_id}, starting full sync")
                return await self.execute_output_sync(job_id, strategy="full")
            
            logger.info(
                f"Resuming output sync from checkpoint: {job.output_checkpoint}"
            )
            
            # Execute incremental sync from checkpoint
            return await self.execute_output_sync(job_id, strategy="incremental")
    
    async def test_target_connection(
        self,
        job_id: UUID
    ) -> ConnectionTestResult:
        """
        Test target database connection for a job.
        
        Args:
            job_id: Sync job identifier
            
        Returns:
            Connection test result with troubleshooting suggestions
        """
        async with db_manager.get_session() as session:
            # Load sync job
            job = await self._load_sync_job(session, job_id)
            if not job:
                raise ValueError(f"Sync job {job_id} not found")
            
            if not job.target_source_id:
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    target_id="",
                    target_type="unknown",
                    response_time_ms=0.0,
                    error_message="No target data source configured",
                    troubleshooting_suggestions=[
                        "Configure a target data source for this sync job",
                        "Set the target_source_id field in the job configuration"
                    ]
                )
            
            # Test connection
            return await self.connection_test_service.test_connection(
                job.target_source_id
            )
    
    # Private helper methods
    
    async def _load_sync_job(
        self,
        session: AsyncSession,
        job_id: UUID
    ) -> Optional[SyncJobModel]:
        """Load sync job from database."""
        result = await session.execute(
            select(SyncJobModel).where(SyncJobModel.id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def _create_execution_record(
        self,
        session: AsyncSession,
        job: SyncJobModel,
        execution_id: UUID,
        sync_strategy: str
    ) -> SyncExecutionModel:
        """Create execution record."""
        execution = SyncExecutionModel(
            id=execution_id,
            job_id=job.id,
            tenant_id=job.tenant_id,
            status=SyncExecutionStatus.RUNNING,
            sync_direction="output",
            started_at=datetime.utcnow(),
            trigger_type="manual"
        )
        session.add(execution)
        await session.flush()
        return execution

    
    async def _load_source_data(
        self,
        session: AsyncSession,
        job: SyncJobModel,
        strategy: str
    ) -> List[Dict[str, Any]]:
        """
        Load source data based on sync strategy.
        
        For full sync: load all data
        For incremental sync: load only changed data since checkpoint
        """
        # This is a simplified implementation
        # In production, this would query the actual AI data tables
        # (annotations, augmented_data, quality_reports, experiments)
        
        if strategy == "incremental" and job.output_checkpoint:
            checkpoint_value = job.output_checkpoint.get("last_sync_value")
            checkpoint_field = job.output_checkpoint.get("checkpoint_field", "updated_at")
            
            logger.info(
                f"Loading incremental data since {checkpoint_field}={checkpoint_value}"
            )
            
            # TODO: Query data where checkpoint_field > checkpoint_value
            # For now, return empty list as placeholder
            return []
        else:
            logger.info("Loading full dataset")
            # TODO: Query all data
            # For now, return empty list as placeholder
            return []
    
    def _apply_field_mapping(
        self,
        data: List[Dict[str, Any]],
        mapping_rules: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply field mapping rules to data."""
        if not mapping_rules or not data:
            return data
        
        # Extract field mappings from rules
        field_mappings = mapping_rules.get("field_mappings", [])
        if not field_mappings:
            return data
        
        mapped_data = []
        for record in data:
            try:
                mapped_result = self.field_mapper.apply_mapping(record, field_mappings)
                mapped_data.append(mapped_result.data)
            except Exception as e:
                logger.error(f"Field mapping failed for record: {e}")
                # Skip failed records
                continue
        
        return mapped_data
    
    def _convert_to_change_records(
        self,
        data: List[Dict[str, Any]],
        job: SyncJobModel
    ) -> List[ChangeRecord]:
        """Convert data records to change records for push service."""
        change_records = []
        
        for record in data:
            change_record = ChangeRecord(
                record_id=str(record.get("id", uuid4())),
                operation="INSERT",  # Default to INSERT for output sync
                table_name=job.target_config.get("table_name", "output_data"),
                new_data=record,
                timestamp=datetime.utcnow(),
                metadata={
                    "job_id": str(job.id),
                    "tenant_id": job.tenant_id
                }
            )
            change_records.append(change_record)
        
        return change_records
    
    async def _create_push_target(
        self,
        session: AsyncSession,
        job: SyncJobModel
    ) -> PushTarget:
        """Create push target from job configuration."""
        # Load target data source
        if not job.target_source_id:
            raise ValueError("Target source ID not configured")
        
        result = await session.execute(
            select(DataSourceModel).where(DataSourceModel.id == job.target_source_id)
        )
        target_source = result.scalar_one_or_none()
        
        if not target_source:
            raise ValueError(f"Target data source {job.target_source_id} not found")
        
        return PushTarget(
            target_id=str(job.target_source_id),
            target_type=target_source.source_type.value,
            connection_config=target_source.connection_config,
            format_config=job.target_config.get("format_config", {}),
            retry_config={
                "max_retries": job.max_retries,
                "retry_delay": job.retry_delay
            },
            enabled=True
        )
    
    async def _update_execution_record(
        self,
        session: AsyncSession,
        execution: SyncExecutionModel,
        push_result: PushResult,
        execution_time_ms: float,
        sync_strategy: str
    ) -> None:
        """Update execution record with results."""
        execution.status = (
            SyncExecutionStatus.COMPLETED
            if push_result.status == "success"
            else SyncExecutionStatus.FAILED
        )
        execution.completed_at = datetime.utcnow()
        execution.duration_seconds = execution_time_ms / 1000
        execution.rows_written = push_result.records_pushed
        execution.records_processed = push_result.records_pushed + push_result.records_failed
        execution.records_failed = push_result.records_failed
        
        if push_result.error_message:
            execution.error_message = push_result.error_message
            execution.write_errors = {
                "error": push_result.error_message,
                "retry_count": push_result.retry_count
            }
        
        await session.flush()
    
    async def _update_checkpoint(
        self,
        session: AsyncSession,
        job: SyncJobModel,
        source_data: List[Dict[str, Any]]
    ) -> None:
        """Update job checkpoint after successful sync."""
        if not source_data:
            return
        
        # Find the latest timestamp/value in the synced data
        checkpoint_field = job.output_checkpoint.get(
            "checkpoint_field", "updated_at"
        ) if job.output_checkpoint else "updated_at"
        
        # Get max value for checkpoint field
        max_value = None
        for record in source_data:
            if checkpoint_field in record:
                value = record[checkpoint_field]
                if max_value is None or value > max_value:
                    max_value = value
        
        if max_value:
            job.output_checkpoint = {
                "checkpoint_field": checkpoint_field,
                "last_sync_value": str(max_value),
                "last_sync_time": datetime.utcnow().isoformat()
            }
            await session.flush()
    
    def _extract_target_schema(
        self,
        mapping: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Extract target schema from mapping rules."""
        target_schema = {}
        
        if not mapping:
            return target_schema
        
        # Extract field mappings
        field_mappings = mapping.get("field_mappings", [])
        
        for field_mapping in field_mappings:
            target_field = field_mapping.get("target_field")
            if target_field:
                target_schema[target_field] = {
                    "type": field_mapping.get("target_type"),
                    "required": field_mapping.get("required", False),
                    "nullable": field_mapping.get("nullable", True)
                }
        
        return target_schema
    
    def _validate_field_type(
        self,
        value: Any,
        expected_type: str
    ) -> bool:
        """Validate field value against expected type."""
        if value is None:
            return True  # Null values handled separately
        
        type_mapping = {
            "string": str,
            "integer": int,
            "float": (int, float),
            "boolean": bool,
            "datetime": (datetime, str),
            "date": (datetime, str),
            "json": (dict, list)
        }
        
        expected_python_type = type_mapping.get(expected_type.lower())
        if not expected_python_type:
            # Unknown type, skip validation
            return True
        
        return isinstance(value, expected_python_type)
