"""
Access Log Manager for SuperInsight Platform.

Implements comprehensive data access logging:
- Read/Modify/Export/API call logging
- Log querying and filtering
- Log export in multiple formats
"""

import logging
import csv
import json
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from src.models.data_permission import (
    DataAccessLogModel, AccessLogOperation, SensitivityLevel,
    DataClassificationModel
)
from src.schemas.data_permission import (
    AccessContext, AccessLogFilter, AccessLogResponse, AccessStatistics
)

logger = logging.getLogger(__name__)


class AccessLogManager:
    """
    Access Log Manager.
    
    Records and manages all data access operations:
    - Read operations
    - Modify operations
    - Export operations
    - API calls
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    # ========================================================================
    # Logging Operations
    # ========================================================================
    
    async def log_read(
        self,
        user_id: UUID,
        resource: str,
        resource_type: str,
        tenant_id: str,
        db: Session,
        fields: Optional[List[str]] = None,
        context: Optional[AccessContext] = None,
        record_count: Optional[int] = None
    ) -> DataAccessLogModel:
        """
        Log a read operation.
        
        Args:
            user_id: User performing the read
            resource: Resource identifier
            resource_type: Type of resource
            tenant_id: Tenant context
            db: Database session
            fields: Optional list of fields accessed
            context: Optional access context
            record_count: Optional number of records read
            
        Returns:
            Created DataAccessLogModel
        """
        sensitivity = await self._get_resource_sensitivity(
            resource=resource,
            resource_type=resource_type,
            tenant_id=tenant_id,
            db=db
        )
        
        log = DataAccessLogModel(
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type=AccessLogOperation.READ,
            resource=resource,
            resource_type=resource_type,
            fields_accessed=fields,
            record_count=record_count,
            ip_address=context.ip_address if context else None,
            user_agent=context.user_agent if context else None,
            session_id=context.session_id if context else None,
            request_id=context.request_id if context else None,
            details=context.additional_info if context else None,
            sensitivity_level=sensitivity
        )
        
        db.add(log)
        db.commit()
        db.refresh(log)
        
        self.logger.debug(f"Logged read operation: {user_id} -> {resource}")
        return log
    
    async def log_modify(
        self,
        user_id: UUID,
        resource: str,
        resource_type: str,
        tenant_id: str,
        db: Session,
        changes: Dict[str, Any],
        context: Optional[AccessContext] = None
    ) -> DataAccessLogModel:
        """
        Log a modify operation.
        
        Args:
            user_id: User performing the modification
            resource: Resource identifier
            resource_type: Type of resource
            tenant_id: Tenant context
            db: Database session
            changes: Dictionary of changes made
            context: Optional access context
            
        Returns:
            Created DataAccessLogModel
        """
        sensitivity = await self._get_resource_sensitivity(
            resource=resource,
            resource_type=resource_type,
            tenant_id=tenant_id,
            db=db
        )
        
        log = DataAccessLogModel(
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type=AccessLogOperation.MODIFY,
            resource=resource,
            resource_type=resource_type,
            fields_accessed=list(changes.keys()) if changes else None,
            details={"changes": changes, **(context.additional_info if context else {})},
            ip_address=context.ip_address if context else None,
            user_agent=context.user_agent if context else None,
            session_id=context.session_id if context else None,
            request_id=context.request_id if context else None,
            sensitivity_level=sensitivity
        )
        
        db.add(log)
        db.commit()
        db.refresh(log)
        
        self.logger.debug(f"Logged modify operation: {user_id} -> {resource}")
        return log
    
    async def log_export(
        self,
        user_id: UUID,
        resource: str,
        resource_type: str,
        tenant_id: str,
        db: Session,
        export_format: str,
        record_count: int,
        context: Optional[AccessContext] = None
    ) -> DataAccessLogModel:
        """
        Log an export operation.
        
        Args:
            user_id: User performing the export
            resource: Resource identifier
            resource_type: Type of resource
            tenant_id: Tenant context
            db: Database session
            export_format: Format of export (csv, json, etc.)
            record_count: Number of records exported
            context: Optional access context
            
        Returns:
            Created DataAccessLogModel
        """
        sensitivity = await self._get_resource_sensitivity(
            resource=resource,
            resource_type=resource_type,
            tenant_id=tenant_id,
            db=db
        )
        
        log = DataAccessLogModel(
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type=AccessLogOperation.EXPORT,
            resource=resource,
            resource_type=resource_type,
            record_count=record_count,
            details={
                "export_format": export_format,
                **(context.additional_info if context else {})
            },
            ip_address=context.ip_address if context else None,
            user_agent=context.user_agent if context else None,
            session_id=context.session_id if context else None,
            request_id=context.request_id if context else None,
            sensitivity_level=sensitivity
        )
        
        db.add(log)
        db.commit()
        db.refresh(log)
        
        self.logger.info(f"Logged export operation: {user_id} -> {resource} ({record_count} records)")
        return log
    
    async def log_api_call(
        self,
        user_id: UUID,
        endpoint: str,
        method: str,
        tenant_id: str,
        db: Session,
        params: Optional[Dict[str, Any]] = None,
        response_code: int = 200,
        context: Optional[AccessContext] = None
    ) -> DataAccessLogModel:
        """
        Log an API call.
        
        Args:
            user_id: User making the API call
            endpoint: API endpoint
            method: HTTP method
            tenant_id: Tenant context
            db: Database session
            params: Request parameters
            response_code: HTTP response code
            context: Optional access context
            
        Returns:
            Created DataAccessLogModel
        """
        log = DataAccessLogModel(
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type=AccessLogOperation.API_CALL,
            resource=endpoint,
            resource_type="api",
            details={
                "method": method,
                "params": params,
                "response_code": response_code,
                **(context.additional_info if context else {})
            },
            ip_address=context.ip_address if context else None,
            user_agent=context.user_agent if context else None,
            session_id=context.session_id if context else None,
            request_id=context.request_id if context else None
        )
        
        db.add(log)
        db.commit()
        db.refresh(log)
        
        self.logger.debug(f"Logged API call: {user_id} -> {method} {endpoint}")
        return log
    
    # ========================================================================
    # Query Operations
    # ========================================================================
    
    async def query_logs(
        self,
        filters: AccessLogFilter,
        tenant_id: str,
        db: Session
    ) -> List[DataAccessLogModel]:
        """
        Query access logs with filters.
        
        Args:
            filters: Filter criteria
            tenant_id: Tenant context
            db: Database session
            
        Returns:
            List of matching access logs
        """
        query = db.query(DataAccessLogModel).filter(
            DataAccessLogModel.tenant_id == tenant_id
        )
        
        # Apply filters
        if filters.user_id:
            query = query.filter(DataAccessLogModel.user_id == filters.user_id)
        
        if filters.resource:
            query = query.filter(DataAccessLogModel.resource.ilike(f"%{filters.resource}%"))
        
        if filters.resource_type:
            query = query.filter(DataAccessLogModel.resource_type == filters.resource_type)
        
        if filters.operation_type:
            query = query.filter(DataAccessLogModel.operation_type == filters.operation_type)
        
        if filters.sensitivity_level:
            query = query.filter(DataAccessLogModel.sensitivity_level == filters.sensitivity_level)
        
        if filters.start_time:
            query = query.filter(DataAccessLogModel.timestamp >= filters.start_time)
        
        if filters.end_time:
            query = query.filter(DataAccessLogModel.timestamp <= filters.end_time)
        
        if filters.ip_address:
            query = query.filter(DataAccessLogModel.ip_address == filters.ip_address)
        
        # Order by timestamp descending
        query = query.order_by(desc(DataAccessLogModel.timestamp))
        
        # Apply pagination
        query = query.offset(filters.offset).limit(filters.limit)
        
        return query.all()
    
    async def get_log_by_id(
        self,
        log_id: UUID,
        tenant_id: str,
        db: Session
    ) -> Optional[DataAccessLogModel]:
        """Get a specific access log by ID."""
        return db.query(DataAccessLogModel).filter(
            and_(
                DataAccessLogModel.id == log_id,
                DataAccessLogModel.tenant_id == tenant_id
            )
        ).first()
    
    async def get_user_activity(
        self,
        user_id: UUID,
        tenant_id: str,
        db: Session,
        days: int = 30
    ) -> List[DataAccessLogModel]:
        """Get recent activity for a user."""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        return db.query(DataAccessLogModel).filter(
            and_(
                DataAccessLogModel.tenant_id == tenant_id,
                DataAccessLogModel.user_id == user_id,
                DataAccessLogModel.timestamp >= start_time
            )
        ).order_by(desc(DataAccessLogModel.timestamp)).limit(1000).all()
    
    async def get_resource_access_history(
        self,
        resource: str,
        resource_type: str,
        tenant_id: str,
        db: Session,
        days: int = 30
    ) -> List[DataAccessLogModel]:
        """Get access history for a resource."""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        return db.query(DataAccessLogModel).filter(
            and_(
                DataAccessLogModel.tenant_id == tenant_id,
                DataAccessLogModel.resource == resource,
                DataAccessLogModel.resource_type == resource_type,
                DataAccessLogModel.timestamp >= start_time
            )
        ).order_by(desc(DataAccessLogModel.timestamp)).limit(1000).all()
    
    # ========================================================================
    # Statistics
    # ========================================================================
    
    async def get_statistics(
        self,
        tenant_id: str,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AccessStatistics:
        """
        Get access statistics.
        
        Args:
            tenant_id: Tenant context
            db: Database session
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            AccessStatistics with aggregated data
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        base_query = db.query(DataAccessLogModel).filter(
            and_(
                DataAccessLogModel.tenant_id == tenant_id,
                DataAccessLogModel.timestamp >= start_date,
                DataAccessLogModel.timestamp <= end_date
            )
        )
        
        # Total count
        total = base_query.count()
        
        # By operation type
        by_operation = {}
        for op in AccessLogOperation:
            count = base_query.filter(
                DataAccessLogModel.operation_type == op
            ).count()
            by_operation[op.value] = count
        
        # By resource type
        resource_types = db.query(
            DataAccessLogModel.resource_type,
            func.count(DataAccessLogModel.id)
        ).filter(
            and_(
                DataAccessLogModel.tenant_id == tenant_id,
                DataAccessLogModel.timestamp >= start_date,
                DataAccessLogModel.timestamp <= end_date
            )
        ).group_by(DataAccessLogModel.resource_type).all()
        
        by_resource_type = {rt: count for rt, count in resource_types}
        
        # By sensitivity level
        by_sensitivity = {}
        for level in SensitivityLevel:
            count = base_query.filter(
                DataAccessLogModel.sensitivity_level == level
            ).count()
            by_sensitivity[level.value] = count
        
        # By user (top 10)
        top_users = db.query(
            DataAccessLogModel.user_id,
            func.count(DataAccessLogModel.id)
        ).filter(
            and_(
                DataAccessLogModel.tenant_id == tenant_id,
                DataAccessLogModel.timestamp >= start_date,
                DataAccessLogModel.timestamp <= end_date
            )
        ).group_by(DataAccessLogModel.user_id).order_by(
            desc(func.count(DataAccessLogModel.id))
        ).limit(10).all()
        
        by_user = {str(user_id): count for user_id, count in top_users}
        
        return AccessStatistics(
            total_accesses=total,
            by_operation=by_operation,
            by_resource_type=by_resource_type,
            by_sensitivity=by_sensitivity,
            by_user=by_user,
            time_range={"start": start_date, "end": end_date}
        )
    
    # ========================================================================
    # Export Operations
    # ========================================================================
    
    async def export_logs(
        self,
        filters: AccessLogFilter,
        tenant_id: str,
        db: Session,
        format: str = "csv"
    ) -> bytes:
        """
        Export access logs.
        
        Args:
            filters: Filter criteria
            tenant_id: Tenant context
            db: Database session
            format: Export format (csv or json)
            
        Returns:
            Exported data as bytes
        """
        # Remove pagination for export
        filters.limit = 10000
        filters.offset = 0
        
        logs = await self.query_logs(filters, tenant_id, db)
        
        if format.lower() == "json":
            return await self._export_json(logs)
        else:
            return await self._export_csv(logs)
    
    async def _export_csv(self, logs: List[DataAccessLogModel]) -> bytes:
        """Export logs as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "ID", "Timestamp", "User ID", "Operation", "Resource Type",
            "Resource", "Fields Accessed", "Record Count", "IP Address",
            "User Agent", "Sensitivity Level"
        ])
        
        # Data rows
        for log in logs:
            writer.writerow([
                str(log.id),
                log.timestamp.isoformat() if log.timestamp else "",
                str(log.user_id),
                log.operation_type.value if log.operation_type else "",
                log.resource_type or "",
                log.resource or "",
                ",".join(log.fields_accessed) if log.fields_accessed else "",
                log.record_count or "",
                log.ip_address or "",
                log.user_agent or "",
                log.sensitivity_level.value if log.sensitivity_level else ""
            ])
        
        return output.getvalue().encode('utf-8')
    
    async def _export_json(self, logs: List[DataAccessLogModel]) -> bytes:
        """Export logs as JSON."""
        data = []
        
        for log in logs:
            data.append({
                "id": str(log.id),
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "user_id": str(log.user_id),
                "operation_type": log.operation_type.value if log.operation_type else None,
                "resource_type": log.resource_type,
                "resource": log.resource,
                "fields_accessed": log.fields_accessed,
                "record_count": log.record_count,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "session_id": log.session_id,
                "sensitivity_level": log.sensitivity_level.value if log.sensitivity_level else None
            })
        
        return json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
    
    # ========================================================================
    # Internal Methods
    # ========================================================================
    
    async def _get_resource_sensitivity(
        self,
        resource: str,
        resource_type: str,
        tenant_id: str,
        db: Session
    ) -> Optional[SensitivityLevel]:
        """Get sensitivity level for a resource."""
        classification = db.query(DataClassificationModel).filter(
            and_(
                DataClassificationModel.tenant_id == tenant_id,
                DataClassificationModel.dataset_id == resource
            )
        ).first()
        
        if classification:
            return classification.sensitivity_level
        
        return None


# Global instance
_access_log_manager: Optional[AccessLogManager] = None


def get_access_log_manager() -> AccessLogManager:
    """Get or create the global access log manager instance."""
    global _access_log_manager
    if _access_log_manager is None:
        _access_log_manager = AccessLogManager()
    return _access_log_manager
