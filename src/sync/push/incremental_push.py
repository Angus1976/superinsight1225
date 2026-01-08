"""
Incremental Push Service.

Implements enterprise-level incremental data push with:
- Data change detection and incremental push
- Permission validation and access control
- Data format conversion and transformation
- Push failure retry mechanisms with exponential backoff
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select, update

from src.database.connection import db_manager
from src.sync.models import (
    SyncJobModel, 
    SyncExecutionModel, 
    SyncExecutionStatus,
    DataSourceModel,
    SyncAuditLogModel,
    AuditAction
)
from src.sync.gateway.auth import AuthToken, Permission, PermissionLevel, ResourceType
from src.sync.transformer.transformer import DataTransformer
from src.utils.encryption import encrypt_sensitive_data, decrypt_sensitive_data

logger = logging.getLogger(__name__)


class ChangeRecord(BaseModel):
    """Represents a data change record for incremental push."""
    record_id: str
    operation: str  # INSERT, UPDATE, DELETE
    table_name: str
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    timestamp: datetime
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PushPermission(BaseModel):
    """Push permission configuration."""
    tenant_id: str
    user_id: Optional[str] = None
    resource_type: ResourceType
    permission_level: PermissionLevel
    allowed_tables: Set[str] = Field(default_factory=set)
    allowed_fields: Dict[str, Set[str]] = Field(default_factory=dict)
    denied_tables: Set[str] = Field(default_factory=set)
    denied_fields: Dict[str, Set[str]] = Field(default_factory=dict)
    ip_whitelist: Set[str] = Field(default_factory=set)
    time_restrictions: Optional[Dict[str, Any]] = None


class PushTarget(BaseModel):
    """Push target configuration."""
    target_id: str
    target_type: str  # database, api, file, webhook
    connection_config: Dict[str, Any]
    format_config: Dict[str, Any] = Field(default_factory=dict)
    retry_config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class PushResult(BaseModel):
    """Result of a push operation."""
    push_id: str
    target_id: str
    status: str  # success, failed, partial
    records_pushed: int
    records_failed: int
    error_message: Optional[str] = None
    execution_time_ms: float
    retry_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IncrementalPushService:
    """
    Enterprise-level incremental push service.
    
    Handles data change detection, permission validation, format conversion,
    and reliable push delivery with retry mechanisms.
    """
    
    def __init__(self):
        self.transformer = DataTransformer()
        self._change_buffer: List[ChangeRecord] = []
        self._push_targets: Dict[str, PushTarget] = {}
        self._permissions_cache: Dict[str, PushPermission] = {}
        self._retry_queue: List[Tuple[str, ChangeRecord, PushTarget]] = []
        
    async def detect_changes(
        self,
        tenant_id: str,
        source_id: str,
        since_timestamp: Optional[datetime] = None
    ) -> List[ChangeRecord]:
        """
        Detect data changes since the last push.
        
        Args:
            tenant_id: Tenant identifier
            source_id: Data source identifier
            since_timestamp: Timestamp to detect changes from
            
        Returns:
            List of detected change records
        """
        try:
            with db_manager.get_session() as session:
                # Get the data source configuration
                source_query = select(DataSourceModel).where(
                    DataSourceModel.id == UUID(source_id),
                    DataSourceModel.tenant_id == tenant_id
                )
                source_result = session.execute(source_query)
                source = source_result.scalar_one_or_none()
                
                if not source:
                    raise ValueError(f"Data source {source_id} not found")
                
                # Get last sync timestamp if not provided
                if not since_timestamp:
                    last_exec_query = select(SyncExecutionModel).where(
                        SyncExecutionModel.tenant_id == tenant_id,
                        SyncExecutionModel.status == SyncExecutionStatus.COMPLETED
                    ).order_by(SyncExecutionModel.completed_at.desc()).limit(1)
                    
                    last_exec_result = session.execute(last_exec_query)
                    last_exec = last_exec_result.scalar_one_or_none()
                    
                    if last_exec:
                        since_timestamp = last_exec.completed_at
                    else:
                        since_timestamp = datetime.utcnow() - timedelta(hours=24)
                
                # Detect changes based on source type
                changes = await self._detect_changes_by_source_type(
                    source, since_timestamp
                )
                
                logger.info(
                    f"Detected {len(changes)} changes for source {source_id} "
                    f"since {since_timestamp}"
                )
                
                return changes
                
        except Exception as e:
            logger.error(f"Error detecting changes: {e}")
            raise
    
    async def _detect_changes_by_source_type(
        self,
        source: DataSourceModel,
        since_timestamp: datetime
    ) -> List[ChangeRecord]:
        """Detect changes based on data source type."""
        changes = []
        
        if source.source_type.value in ["mysql", "postgresql", "oracle", "sqlserver"]:
            changes = await self._detect_database_changes(source, since_timestamp)
        elif source.source_type.value in ["rest_api", "graphql_api"]:
            changes = await self._detect_api_changes(source, since_timestamp)
        elif source.source_type.value in ["s3", "local_file", "ftp", "sftp"]:
            changes = await self._detect_file_changes(source, since_timestamp)
        else:
            logger.warning(f"Unsupported source type: {source.source_type}")
            
        return changes
    
    async def _detect_database_changes(
        self,
        source: DataSourceModel,
        since_timestamp: datetime
    ) -> List[ChangeRecord]:
        """Detect changes in database sources using CDC or timestamp-based detection."""
        changes = []
        
        # This would integrate with CDC systems like Debezium
        # For now, simulate change detection
        config = source.connection_config
        
        # Example: Query change log table or use timestamp-based detection
        # In production, this would connect to the actual database
        logger.info(f"Detecting database changes for {source.name} since {since_timestamp}")
        
        # Simulate some changes
        for i in range(3):
            change = ChangeRecord(
                record_id=f"record_{i}",
                operation="UPDATE",
                table_name="customer_data",
                old_data={"id": i, "name": f"old_name_{i}", "updated_at": since_timestamp},
                new_data={"id": i, "name": f"new_name_{i}", "updated_at": datetime.utcnow()},
                timestamp=datetime.utcnow(),
                checksum=f"checksum_{i}",
                metadata={"source_id": str(source.id)}
            )
            changes.append(change)
            
        return changes
    
    async def _detect_api_changes(
        self,
        source: DataSourceModel,
        since_timestamp: datetime
    ) -> List[ChangeRecord]:
        """Detect changes in API sources."""
        changes = []
        
        # This would call the API to get changes since timestamp
        logger.info(f"Detecting API changes for {source.name} since {since_timestamp}")
        
        # Simulate API change detection
        for i in range(2):
            change = ChangeRecord(
                record_id=f"api_record_{i}",
                operation="INSERT",
                table_name="api_data",
                new_data={"id": i, "data": f"api_data_{i}", "created_at": datetime.utcnow()},
                timestamp=datetime.utcnow(),
                metadata={"source_id": str(source.id), "api_endpoint": "/data"}
            )
            changes.append(change)
            
        return changes
    
    async def _detect_file_changes(
        self,
        source: DataSourceModel,
        since_timestamp: datetime
    ) -> List[ChangeRecord]:
        """Detect changes in file sources."""
        changes = []
        
        # This would check file modification times or use file system events
        logger.info(f"Detecting file changes for {source.name} since {since_timestamp}")
        
        # Simulate file change detection
        change = ChangeRecord(
            record_id="file_record_1",
            operation="UPDATE",
            table_name="file_data",
            new_data={"filename": "data.csv", "modified_at": datetime.utcnow()},
            timestamp=datetime.utcnow(),
            metadata={"source_id": str(source.id), "file_path": "/data/data.csv"}
        )
        changes.append(change)
        
        return changes
    
    async def validate_push_permissions(
        self,
        auth_token: AuthToken,
        tenant_id: str,
        changes: List[ChangeRecord],
        target_id: str
    ) -> Tuple[List[ChangeRecord], List[str]]:
        """
        Validate push permissions for the given changes.
        
        Args:
            auth_token: Authentication token
            tenant_id: Tenant identifier
            changes: List of change records to validate
            target_id: Target identifier for push
            
        Returns:
            Tuple of (allowed_changes, permission_errors)
        """
        allowed_changes = []
        permission_errors = []
        
        try:
            # Get or create permission configuration
            permission_key = f"{tenant_id}:{auth_token.user_id}:{target_id}"
            permission = self._permissions_cache.get(permission_key)
            
            if not permission:
                permission = await self._load_push_permissions(
                    auth_token, tenant_id, target_id
                )
                self._permissions_cache[permission_key] = permission
            
            # Validate each change record
            for change in changes:
                validation_result = await self._validate_change_permission(
                    change, permission, auth_token
                )
                
                if validation_result["allowed"]:
                    allowed_changes.append(change)
                else:
                    permission_errors.append(
                        f"Permission denied for {change.table_name}.{change.record_id}: "
                        f"{validation_result['reason']}"
                    )
            
            logger.info(
                f"Permission validation: {len(allowed_changes)} allowed, "
                f"{len(permission_errors)} denied"
            )
            
            return allowed_changes, permission_errors
            
        except Exception as e:
            logger.error(f"Error validating permissions: {e}")
            raise
    
    async def _load_push_permissions(
        self,
        auth_token: AuthToken,
        tenant_id: str,
        target_id: str
    ) -> PushPermission:
        """Load push permissions for user and target."""
        # In production, this would load from database or permission service
        # For now, create default permissions based on auth token
        
        permission = PushPermission(
            tenant_id=tenant_id,
            user_id=auth_token.user_id,
            resource_type=ResourceType.SYNC_JOB,
            permission_level=PermissionLevel.WRITE
        )
        
        # Set default allowed tables based on permission level
        if auth_token.permissions.get(ResourceType.SYNC_JOB) == PermissionLevel.ADMIN:
            permission.allowed_tables = {"*"}  # All tables
        else:
            permission.allowed_tables = {"customer_data", "api_data", "file_data"}
            
        return permission
    
    async def _validate_change_permission(
        self,
        change: ChangeRecord,
        permission: PushPermission,
        auth_token: AuthToken
    ) -> Dict[str, Any]:
        """Validate permission for a single change record."""
        
        # Check table-level permissions
        if permission.denied_tables and change.table_name in permission.denied_tables:
            return {"allowed": False, "reason": "Table access denied"}
        
        if permission.allowed_tables and "*" not in permission.allowed_tables:
            if change.table_name not in permission.allowed_tables:
                return {"allowed": False, "reason": "Table not in allowed list"}
        
        # Check field-level permissions
        if change.table_name in permission.denied_fields:
            denied_fields = permission.denied_fields[change.table_name]
            if change.new_data:
                for field in change.new_data.keys():
                    if field in denied_fields:
                        return {"allowed": False, "reason": f"Field {field} access denied"}
        
        # Check IP restrictions
        if permission.ip_whitelist:
            # In production, get actual client IP from request context
            client_ip = "127.0.0.1"  # Placeholder
            if client_ip not in permission.ip_whitelist:
                return {"allowed": False, "reason": "IP address not whitelisted"}
        
        # Check time restrictions
        if permission.time_restrictions:
            current_hour = datetime.utcnow().hour
            allowed_hours = permission.time_restrictions.get("allowed_hours", [])
            if allowed_hours and current_hour not in allowed_hours:
                return {"allowed": False, "reason": "Outside allowed time window"}
        
        return {"allowed": True, "reason": "Permission granted"}
    
    async def convert_data_format(
        self,
        changes: List[ChangeRecord],
        target: PushTarget
    ) -> List[Dict[str, Any]]:
        """
        Convert change records to target format.
        
        Args:
            changes: List of change records
            target: Target configuration
            
        Returns:
            List of converted data records
        """
        converted_records = []
        
        try:
            format_config = target.format_config
            target_format = format_config.get("format", "json")
            
            for change in changes:
                # Apply data transformation based on target format
                if target_format == "json":
                    converted = await self._convert_to_json(change, format_config)
                elif target_format == "xml":
                    converted = await self._convert_to_xml(change, format_config)
                elif target_format == "csv":
                    converted = await self._convert_to_csv(change, format_config)
                elif target_format == "avro":
                    converted = await self._convert_to_avro(change, format_config)
                else:
                    # Default to JSON
                    converted = await self._convert_to_json(change, format_config)
                
                converted_records.append(converted)
            
            logger.info(f"Converted {len(changes)} records to {target_format} format")
            return converted_records
            
        except Exception as e:
            logger.error(f"Error converting data format: {e}")
            raise
    
    async def _convert_to_json(
        self,
        change: ChangeRecord,
        format_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert change record to JSON format."""
        json_record = {
            "record_id": change.record_id,
            "operation": change.operation,
            "table_name": change.table_name,
            "timestamp": change.timestamp.isoformat(),
            "data": change.new_data or change.old_data,
            "metadata": change.metadata
        }
        
        # Apply field mappings if configured
        field_mappings = format_config.get("field_mappings", {})
        if field_mappings and json_record["data"]:
            mapped_data = {}
            for source_field, target_field in field_mappings.items():
                if source_field in json_record["data"]:
                    mapped_data[target_field] = json_record["data"][source_field]
            json_record["data"] = mapped_data
        
        return json_record
    
    async def _convert_to_xml(
        self,
        change: ChangeRecord,
        format_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert change record to XML format."""
        # Simplified XML conversion - in production use proper XML library
        xml_data = f"""
        <record>
            <id>{change.record_id}</id>
            <operation>{change.operation}</operation>
            <table>{change.table_name}</table>
            <timestamp>{change.timestamp.isoformat()}</timestamp>
            <data>{change.new_data or change.old_data}</data>
        </record>
        """
        
        return {"xml_data": xml_data.strip()}
    
    async def _convert_to_csv(
        self,
        change: ChangeRecord,
        format_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert change record to CSV format."""
        # Flatten the data for CSV
        csv_data = {
            "record_id": change.record_id,
            "operation": change.operation,
            "table_name": change.table_name,
            "timestamp": change.timestamp.isoformat()
        }
        
        # Add data fields
        if change.new_data:
            for key, value in change.new_data.items():
                csv_data[f"data_{key}"] = str(value)
        
        return csv_data
    
    async def _convert_to_avro(
        self,
        change: ChangeRecord,
        format_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert change record to Avro format."""
        # Simplified Avro conversion - in production use proper Avro library
        avro_record = {
            "record_id": change.record_id,
            "operation": change.operation,
            "table_name": change.table_name,
            "timestamp": int(change.timestamp.timestamp()),
            "data": change.new_data or change.old_data or {}
        }
        
        return avro_record
    
    async def push_with_retry(
        self,
        tenant_id: str,
        changes: List[ChangeRecord],
        target: PushTarget,
        max_retries: int = 3
    ) -> PushResult:
        """
        Push data with retry mechanism.
        
        Args:
            tenant_id: Tenant identifier
            changes: List of change records to push
            target: Target configuration
            max_retries: Maximum number of retry attempts
            
        Returns:
            Push result with status and metrics
        """
        push_id = str(uuid4())
        start_time = datetime.utcnow()
        
        try:
            # Convert data to target format
            converted_records = await self.convert_data_format(changes, target)
            
            # Attempt push with retries
            for attempt in range(max_retries + 1):
                try:
                    result = await self._execute_push(
                        push_id, converted_records, target, attempt
                    )
                    
                    if result.status == "success":
                        # Log successful push
                        await self._log_push_audit(
                            tenant_id, push_id, target.target_id, 
                            AuditAction.DATA_PUSHED, True, result
                        )
                        
                        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                        result.execution_time_ms = execution_time
                        return result
                    
                except Exception as e:
                    logger.warning(f"Push attempt {attempt + 1} failed: {e}")
                    
                    if attempt < max_retries:
                        # Calculate exponential backoff delay
                        delay = min(2 ** attempt, 60)  # Max 60 seconds
                        await asyncio.sleep(delay)
                    else:
                        # Final attempt failed
                        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                        
                        failed_result = PushResult(
                            push_id=push_id,
                            target_id=target.target_id,
                            status="failed",
                            records_pushed=0,
                            records_failed=len(changes),
                            error_message=str(e),
                            execution_time_ms=execution_time,
                            retry_count=attempt
                        )
                        
                        # Log failed push
                        await self._log_push_audit(
                            tenant_id, push_id, target.target_id,
                            AuditAction.DATA_PUSHED, False, failed_result
                        )
                        
                        return failed_result
            
        except Exception as e:
            logger.error(f"Error in push_with_retry: {e}")
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return PushResult(
                push_id=push_id,
                target_id=target.target_id,
                status="failed",
                records_pushed=0,
                records_failed=len(changes),
                error_message=str(e),
                execution_time_ms=execution_time,
                retry_count=0
            )
    
    async def _execute_push(
        self,
        push_id: str,
        records: List[Dict[str, Any]],
        target: PushTarget,
        attempt: int
    ) -> PushResult:
        """Execute the actual push operation."""
        
        if target.target_type == "database":
            return await self._push_to_database(push_id, records, target)
        elif target.target_type == "api":
            return await self._push_to_api(push_id, records, target)
        elif target.target_type == "file":
            return await self._push_to_file(push_id, records, target)
        elif target.target_type == "webhook":
            return await self._push_to_webhook(push_id, records, target)
        else:
            raise ValueError(f"Unsupported target type: {target.target_type}")
    
    async def _push_to_database(
        self,
        push_id: str,
        records: List[Dict[str, Any]],
        target: PushTarget
    ) -> PushResult:
        """Push records to database target."""
        # Simulate database push
        logger.info(f"Pushing {len(records)} records to database {target.target_id}")
        
        # In production, this would connect to the target database and insert/update records
        await asyncio.sleep(0.1)  # Simulate processing time
        
        return PushResult(
            push_id=push_id,
            target_id=target.target_id,
            status="success",
            records_pushed=len(records),
            records_failed=0,
            execution_time_ms=100.0
        )
    
    async def _push_to_api(
        self,
        push_id: str,
        records: List[Dict[str, Any]],
        target: PushTarget
    ) -> PushResult:
        """Push records to API target."""
        # Simulate API push
        logger.info(f"Pushing {len(records)} records to API {target.target_id}")
        
        # In production, this would make HTTP requests to the target API
        await asyncio.sleep(0.2)  # Simulate network delay
        
        return PushResult(
            push_id=push_id,
            target_id=target.target_id,
            status="success",
            records_pushed=len(records),
            records_failed=0,
            execution_time_ms=200.0
        )
    
    async def _push_to_file(
        self,
        push_id: str,
        records: List[Dict[str, Any]],
        target: PushTarget
    ) -> PushResult:
        """Push records to file target."""
        # Simulate file push
        logger.info(f"Pushing {len(records)} records to file {target.target_id}")
        
        # In production, this would write records to the target file system
        await asyncio.sleep(0.05)  # Simulate file I/O
        
        return PushResult(
            push_id=push_id,
            target_id=target.target_id,
            status="success",
            records_pushed=len(records),
            records_failed=0,
            execution_time_ms=50.0
        )
    
    async def _push_to_webhook(
        self,
        push_id: str,
        records: List[Dict[str, Any]],
        target: PushTarget
    ) -> PushResult:
        """Push records to webhook target."""
        # Simulate webhook push
        logger.info(f"Pushing {len(records)} records to webhook {target.target_id}")
        
        # In production, this would send HTTP POST requests to the webhook URL
        await asyncio.sleep(0.15)  # Simulate network delay
        
        return PushResult(
            push_id=push_id,
            target_id=target.target_id,
            status="success",
            records_pushed=len(records),
            records_failed=0,
            execution_time_ms=150.0
        )
    
    async def _log_push_audit(
        self,
        tenant_id: str,
        push_id: str,
        target_id: str,
        action: AuditAction,
        success: bool,
        result: PushResult
    ) -> None:
        """Log push operation to audit trail."""
        try:
            with db_manager.get_session() as session:
                audit_log = SyncAuditLogModel(
                    tenant_id=tenant_id,
                    action=action,
                    actor_type="system",
                    action_details={
                        "push_id": push_id,
                        "target_id": target_id,
                        "records_pushed": result.records_pushed,
                        "records_failed": result.records_failed,
                        "execution_time_ms": result.execution_time_ms,
                        "retry_count": result.retry_count
                    },
                    success=success,
                    error_message=result.error_message
                )
                
                session.add(audit_log)
                session.commit()
                
        except Exception as e:
            logger.error(f"Error logging push audit: {e}")
    
    def register_push_target(self, target: PushTarget) -> None:
        """Register a push target configuration."""
        self._push_targets[target.target_id] = target
        logger.info(f"Registered push target: {target.target_id}")
    
    def get_push_target(self, target_id: str) -> Optional[PushTarget]:
        """Get push target configuration by ID."""
        return self._push_targets.get(target_id)
    
    def list_push_targets(self) -> List[PushTarget]:
        """List all registered push targets."""
        return list(self._push_targets.values())