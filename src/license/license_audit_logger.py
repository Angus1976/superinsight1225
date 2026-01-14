"""
License Audit Logger for SuperInsight Platform.

Records all license-related operations for audit purposes.
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.license import LicenseAuditLogModel, LicenseEventType
from src.schemas.license import AuditLogFilter, AuditLogResponse


class LicenseAuditLogger:
    """
    License Audit Logger.
    
    Records and queries license audit logs.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize License Audit Logger.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def log_event(
        self,
        event_type: LicenseEventType,
        license_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditLogResponse:
        """
        Log a license event.
        
        Args:
            event_type: Type of event
            license_id: Associated license ID
            details: Event details
            user_id: User who triggered the event
            ip_address: Client IP address
            success: Whether the operation succeeded
            error_message: Error message if failed
            
        Returns:
            Created audit log entry
        """
        log_entry = LicenseAuditLogModel(
            id=uuid4(),
            license_id=license_id,
            event_type=event_type,
            details=details or {},
            user_id=user_id,
            ip_address=ip_address,
            success=success,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc),
        )
        
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        
        return self._to_response(log_entry)
    
    async def log_activation(
        self,
        license_id: UUID,
        hardware_id: str,
        result: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuditLogResponse:
        """Log activation event."""
        return await self.log_event(
            event_type=LicenseEventType.ACTIVATED,
            license_id=license_id,
            details={
                "hardware_id": hardware_id,
                "result": result,
            },
            user_id=user_id,
            ip_address=ip_address,
            success=result == "success",
            error_message=None if result == "success" else result,
        )
    
    async def log_validation(
        self,
        license_id: UUID,
        result: str,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuditLogResponse:
        """Log validation event."""
        event_type = (
            LicenseEventType.VALIDATED
            if result == "valid"
            else LicenseEventType.VALIDATION_FAILED
        )
        
        return await self.log_event(
            event_type=event_type,
            license_id=license_id,
            details=details or {"result": result},
            user_id=user_id,
            ip_address=ip_address,
            success=result == "valid",
            error_message=None if result == "valid" else result,
        )
    
    async def log_concurrent_usage(
        self,
        current_users: int,
        max_users: int,
        license_id: Optional[UUID] = None,
        user_id: Optional[str] = None
    ) -> AuditLogResponse:
        """Log concurrent usage check."""
        return await self.log_event(
            event_type=LicenseEventType.CONCURRENT_CHECK,
            license_id=license_id,
            details={
                "current_users": current_users,
                "max_users": max_users,
                "utilization_percent": (current_users / max_users * 100) if max_users > 0 else 0,
            },
            user_id=user_id,
            success=True,
        )
    
    async def log_resource_usage(
        self,
        resource_type: str,
        current_value: int,
        max_value: int,
        license_id: Optional[UUID] = None
    ) -> AuditLogResponse:
        """Log resource usage check."""
        return await self.log_event(
            event_type=LicenseEventType.RESOURCE_CHECK,
            license_id=license_id,
            details={
                "resource_type": resource_type,
                "current_value": current_value,
                "max_value": max_value,
                "utilization_percent": (current_value / max_value * 100) if max_value > 0 else 0,
            },
            success=True,
        )
    
    async def log_feature_access(
        self,
        feature: str,
        allowed: bool,
        license_id: Optional[UUID] = None,
        user_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> AuditLogResponse:
        """Log feature access attempt."""
        return await self.log_event(
            event_type=LicenseEventType.FEATURE_ACCESS,
            license_id=license_id,
            details={
                "feature": feature,
                "allowed": allowed,
                "reason": reason,
            },
            user_id=user_id,
            success=allowed,
            error_message=reason if not allowed else None,
        )
    
    async def log_session_event(
        self,
        event_type: LicenseEventType,
        user_id: str,
        session_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLogResponse:
        """Log session event (created, released, forced logout)."""
        return await self.log_event(
            event_type=event_type,
            details={
                "session_id": session_id,
                **(details or {}),
            },
            user_id=user_id,
            ip_address=ip_address,
            success=True,
        )
    
    async def query_logs(
        self,
        filter: AuditLogFilter
    ) -> List[AuditLogResponse]:
        """
        Query audit logs with filters.
        
        Args:
            filter: Query filters
            
        Returns:
            List of matching audit logs
        """
        query = select(LicenseAuditLogModel)
        
        conditions = []
        
        if filter.license_id:
            conditions.append(LicenseAuditLogModel.license_id == filter.license_id)
        
        if filter.event_type:
            conditions.append(LicenseAuditLogModel.event_type == filter.event_type)
        
        if filter.user_id:
            conditions.append(LicenseAuditLogModel.user_id == filter.user_id)
        
        if filter.start_time:
            conditions.append(LicenseAuditLogModel.timestamp >= filter.start_time)
        
        if filter.end_time:
            conditions.append(LicenseAuditLogModel.timestamp <= filter.end_time)
        
        if filter.success is not None:
            conditions.append(LicenseAuditLogModel.success == filter.success)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(LicenseAuditLogModel.timestamp.desc())
        query = query.limit(filter.limit).offset(filter.offset)
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return [self._to_response(log) for log in logs]
    
    async def get_log_by_id(self, log_id: UUID) -> Optional[AuditLogResponse]:
        """Get a specific audit log by ID."""
        result = await self.db.execute(
            select(LicenseAuditLogModel).where(LicenseAuditLogModel.id == log_id)
        )
        log = result.scalar_one_or_none()
        
        if not log:
            return None
        
        return self._to_response(log)
    
    async def get_event_counts(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        license_id: Optional[UUID] = None
    ) -> Dict[str, int]:
        """
        Get event counts by type.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            license_id: Filter by license
            
        Returns:
            Dictionary of event type -> count
        """
        query = select(
            LicenseAuditLogModel.event_type,
            func.count(LicenseAuditLogModel.id)
        )
        
        conditions = []
        
        if start_time:
            conditions.append(LicenseAuditLogModel.timestamp >= start_time)
        if end_time:
            conditions.append(LicenseAuditLogModel.timestamp <= end_time)
        if license_id:
            conditions.append(LicenseAuditLogModel.license_id == license_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.group_by(LicenseAuditLogModel.event_type)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return {row[0].value: row[1] for row in rows}
    
    async def export_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        format: str = "csv",
        license_id: Optional[UUID] = None
    ) -> bytes:
        """
        Export audit logs.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            format: Export format (csv or json)
            license_id: Filter by license
            
        Returns:
            Exported data as bytes
        """
        filter = AuditLogFilter(
            start_time=start_time,
            end_time=end_time,
            license_id=license_id,
            limit=10000,  # Max export limit
        )
        
        logs = await self.query_logs(filter)
        
        if format == "json":
            data = [
                {
                    "id": str(log.id),
                    "license_id": str(log.license_id) if log.license_id else None,
                    "event_type": log.event_type.value,
                    "details": log.details,
                    "user_id": log.user_id,
                    "ip_address": log.ip_address,
                    "success": log.success,
                    "error_message": log.error_message,
                    "timestamp": log.timestamp.isoformat(),
                }
                for log in logs
            ]
            return json.dumps(data, indent=2).encode()
        
        else:  # CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "id", "license_id", "event_type", "details",
                "user_id", "ip_address", "success", "error_message", "timestamp"
            ])
            
            # Data
            for log in logs:
                writer.writerow([
                    str(log.id),
                    str(log.license_id) if log.license_id else "",
                    log.event_type.value,
                    json.dumps(log.details),
                    log.user_id or "",
                    log.ip_address or "",
                    str(log.success),
                    log.error_message or "",
                    log.timestamp.isoformat(),
                ])
            
            return output.getvalue().encode()
    
    def _to_response(self, model: LicenseAuditLogModel) -> AuditLogResponse:
        """Convert model to response."""
        return AuditLogResponse(
            id=model.id,
            license_id=model.license_id,
            event_type=model.event_type,
            details=model.details,
            user_id=model.user_id,
            ip_address=model.ip_address,
            success=model.success,
            error_message=model.error_message,
            timestamp=model.timestamp,
        )
