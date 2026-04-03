"""
Audit Logger Service for Data Lifecycle Management.

Provides comprehensive audit logging for all state-changing operations,
supporting filtering, querying, and CSV export for compliance reporting.
"""

import csv
import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from src.models.data_lifecycle import (
    AuditLogModel,
    OperationType,
    OperationResult,
    ResourceType,
    Action,
    AuditLog
)


class AuditLogger:
    """
    Audit Logger service for recording and retrieving audit logs.
    
    Responsibilities:
    - Log all data operations with timestamp, user, and details
    - Provide audit trail with filtering capabilities
    - Support compliance reporting
    - Enable forensic analysis
    - Export audit logs in CSV format
    """
    
    def __init__(self, db: Session):
        """
        Initialize the Audit Logger.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def log_operation(
        self,
        operation_type: OperationType,
        user_id: str,
        resource_type: ResourceType,
        resource_id: str,
        action: Action,
        result: OperationResult,
        duration: int,
        error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Log a single operation to the audit trail.
        
        Args:
            operation_type: Type of operation (CREATE, READ, UPDATE, DELETE, etc.)
            user_id: ID of the user performing the operation
            resource_type: Type of resource being operated on
            resource_id: ID of the specific resource
            action: Action being performed (VIEW, EDIT, DELETE, etc.)
            result: Result of the operation (SUCCESS, FAILURE, PARTIAL)
            duration: Duration of the operation in milliseconds
            error: Error message if operation failed
            details: Additional operation details
            ip_address: IP address of the user
            user_agent: User agent string
            
        Returns:
            Created audit log entry
            
        Validates: Requirements 10.1, 10.2, 10.5
        """
        # Create audit log entry
        audit_log = AuditLogModel(
            operation_type=operation_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            duration=duration,
            error=error,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow()
        )
        
        # Store in database (immutable - no updates allowed)
        self.db.add(audit_log)
        self.db.flush()
        # Validate before commit so we never rely on session.refresh() after commit.
        # refresh() can fail on SQLite + PGUUID when tests temporarily swap column types.
        out = AuditLog.model_validate(audit_log, from_attributes=True)
        self.db.commit()
        return out
    
    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        operation_type: Optional[OperationType] = None,
        result: Optional[OperationResult] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Retrieve audit logs with optional filtering.
        
        Args:
            user_id: Filter by user ID
            resource_type: Filter by resource type
            operation_type: Filter by operation type
            result: Filter by operation result
            start_date: Filter by start date (inclusive)
            end_date: Filter by end date (inclusive)
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of audit log entries matching the filters
            
        Validates: Requirements 10.3
        """
        # Build query with filters
        query = self.db.query(AuditLogModel)
        
        filters = []
        
        if user_id:
            filters.append(AuditLogModel.user_id == user_id)
        
        if resource_type:
            filters.append(AuditLogModel.resource_type == resource_type)
        
        if operation_type:
            filters.append(AuditLogModel.operation_type == operation_type)
        
        if result:
            filters.append(AuditLogModel.result == result)
        
        if start_date:
            filters.append(AuditLogModel.timestamp >= start_date)
        
        if end_date:
            filters.append(AuditLogModel.timestamp <= end_date)
        
        # Apply filters
        if filters:
            query = query.filter(and_(*filters))
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(AuditLogModel.timestamp.desc())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        results = query.all()
        
        # Convert to Pydantic models
        return [AuditLog.model_validate(log) for log in results]
    
    def get_data_history(
        self,
        resource_id: str,
        resource_type: Optional[ResourceType] = None
    ) -> List[AuditLog]:
        """
        Get complete audit history for a specific data item.
        
        Args:
            resource_id: ID of the resource
            resource_type: Optional resource type filter
            
        Returns:
            List of audit log entries for the resource, ordered by timestamp
            
        Validates: Requirements 10.1, 10.2
        """
        query = self.db.query(AuditLogModel).filter(
            AuditLogModel.resource_id == resource_id
        )
        
        if resource_type:
            query = query.filter(AuditLogModel.resource_type == resource_type)
        
        # Order by timestamp ascending (chronological order)
        query = query.order_by(AuditLogModel.timestamp.asc())
        
        results = query.all()
        
        return [AuditLog.model_validate(log) for log in results]
    
    def get_user_activity(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific user's activity.
        
        Args:
            user_id: ID of the user
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of results
            
        Returns:
            List of audit log entries for the user
            
        Validates: Requirements 10.3
        """
        query = self.db.query(AuditLogModel).filter(
            AuditLogModel.user_id == user_id
        )
        
        if start_date:
            query = query.filter(AuditLogModel.timestamp >= start_date)
        
        if end_date:
            query = query.filter(AuditLogModel.timestamp <= end_date)
        
        # Order by timestamp descending
        query = query.order_by(AuditLogModel.timestamp.desc())
        
        # Apply limit
        query = query.limit(limit)
        
        results = query.all()
        
        return [AuditLog.model_validate(log) for log in results]
    
    def export_audit_log(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        operation_type: Optional[OperationType] = None,
        result: Optional[OperationResult] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        Export audit logs to CSV format.
        
        Args:
            user_id: Filter by user ID
            resource_type: Filter by resource type
            operation_type: Filter by operation type
            result: Filter by operation result
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            CSV string containing the audit logs
            
        Validates: Requirements 10.4
        """
        # Get filtered audit logs (no limit for export)
        logs = self.get_audit_log(
            user_id=user_id,
            resource_type=resource_type,
            operation_type=operation_type,
            result=result,
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Large limit for export
        )
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID',
            'Timestamp',
            'User ID',
            'Operation Type',
            'Resource Type',
            'Resource ID',
            'Action',
            'Result',
            'Duration (ms)',
            'Error',
            'IP Address',
            'User Agent',
            'Details'
        ])
        
        # Write data rows
        for log in logs:
            writer.writerow([
                str(log.id),
                log.timestamp.isoformat(),
                log.user_id,
                log.operation_type.value,
                log.resource_type.value,
                log.resource_id,
                log.action.value,
                log.result.value,
                log.duration,
                log.error or '',
                log.ip_address or '',
                log.user_agent or '',
                str(log.details) if log.details else ''
            ])
        
        # Get CSV string
        csv_content = output.getvalue()
        output.close()
        
        return csv_content
