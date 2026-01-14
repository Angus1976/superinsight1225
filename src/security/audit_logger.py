"""
Audit Logger for SuperInsight Platform.

Implements comprehensive audit logging with tamper-proof hash chain verification.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4
import csv
import io

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from src.models.security import AuditLogModel


class AuditLogger:
    """
    Audit logger with tamper-proof hash chain verification.
    
    Records all security-relevant operations with cryptographic integrity protection.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self._previous_hash: Optional[str] = None
        self._hash_cache_size = 1000  # Cache recent hashes for performance
        self._hash_cache: Dict[str, str] = {}
    
    async def log(
        self,
        event_type: str,
        user_id: str,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[bool] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> AuditLogModel:
        """
        Record an audit log entry with tamper-proof hash chain.
        
        Args:
            event_type: Type of event (e.g., 'login', 'data_access', 'permission_change')
            user_id: ID of user performing the action
            resource: Resource being accessed (optional)
            action: Action being performed (optional)
            result: Success/failure of the action (optional)
            details: Additional event details (optional)
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)
            session_id: Session ID (optional)
            **kwargs: Additional fields
            
        Returns:
            Created AuditLogModel instance
        """
        try:
            # Get previous hash for chain verification
            previous_hash = await self._get_previous_hash()
            
            # Create audit log entry
            log_entry = AuditLogModel(
                id=uuid4(),
                event_type=event_type,
                user_id=user_id,
                resource=resource,
                action=action,
                result=result,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                timestamp=datetime.utcnow(),
                previous_hash=previous_hash,
                **kwargs
            )
            
            # Calculate hash for this entry
            log_entry.hash = self._calculate_hash(log_entry)
            
            # Save to database
            self.db.add(log_entry)
            await self.db.commit()
            
            # Update cache
            self._previous_hash = log_entry.hash
            self._hash_cache[str(log_entry.id)] = log_entry.hash
            
            # Trim cache if too large
            if len(self._hash_cache) > self._hash_cache_size:
                # Remove oldest entries (simplified - in production use LRU)
                keys_to_remove = list(self._hash_cache.keys())[:-self._hash_cache_size//2]
                for key in keys_to_remove:
                    del self._hash_cache[key]
            
            self.logger.debug(f"Audit log recorded: {event_type} by user {user_id}")
            return log_entry
            
        except Exception as e:
            self.logger.error(f"Failed to record audit log: {e}")
            await self.db.rollback()
            raise
    
    def _calculate_hash(self, log_entry: AuditLogModel) -> str:
        """
        Calculate tamper-proof hash for audit log entry.
        
        Creates a SHA-256 hash of critical fields to detect tampering.
        
        Args:
            log_entry: Audit log entry to hash
            
        Returns:
            SHA-256 hash string
        """
        # Create deterministic string from critical fields
        hash_data = (
            f"{log_entry.event_type}|"
            f"{log_entry.user_id}|"
            f"{log_entry.resource or ''}|"
            f"{log_entry.action or ''}|"
            f"{log_entry.result}|"
            f"{log_entry.timestamp.isoformat()}|"
            f"{log_entry.previous_hash or ''}|"
            f"{json.dumps(log_entry.details or {}, sort_keys=True)}|"
            f"{log_entry.ip_address or ''}"
        )
        
        return hashlib.sha256(hash_data.encode('utf-8')).hexdigest()
    
    async def _get_previous_hash(self) -> Optional[str]:
        """
        Get hash of the most recent audit log entry.
        
        Returns:
            Hash of previous entry, or None if this is the first entry
        """
        if self._previous_hash:
            return self._previous_hash
        
        # Query most recent log entry
        stmt = select(AuditLogModel).order_by(desc(AuditLogModel.timestamp)).limit(1)
        result = await self.db.execute(stmt)
        last_log = result.scalar_one_or_none()
        
        if last_log:
            self._previous_hash = last_log.hash
            return last_log.hash
        
        return None
    
    async def verify_integrity(
        self,
        start_id: Optional[str] = None,
        end_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> 'IntegrityResult':
        """
        Verify integrity of audit log chain.
        
        Args:
            start_id: Starting log entry ID (optional)
            end_id: Ending log entry ID (optional)
            start_time: Starting timestamp (optional)
            end_time: Ending timestamp (optional)
            
        Returns:
            IntegrityResult with verification status
        """
        try:
            # Build query
            stmt = select(AuditLogModel).order_by(AuditLogModel.timestamp)
            
            if start_id:
                stmt = stmt.where(AuditLogModel.id >= start_id)
            if end_id:
                stmt = stmt.where(AuditLogModel.id <= end_id)
            if start_time:
                stmt = stmt.where(AuditLogModel.timestamp >= start_time)
            if end_time:
                stmt = stmt.where(AuditLogModel.timestamp <= end_time)
            
            result = await self.db.execute(stmt)
            logs = list(result.scalars().all())
            
            if not logs:
                return IntegrityResult(valid=True, verified_count=0, message="No logs to verify")
            
            # Verify each log entry
            for i, log in enumerate(logs):
                # Verify hash
                expected_hash = self._calculate_hash(log)
                if log.hash != expected_hash:
                    return IntegrityResult(
                        valid=False,
                        verified_count=i,
                        error=f"Hash mismatch at log {log.id}",
                        corrupted_entry_id=str(log.id)
                    )
                
                # Verify chain (skip first entry)
                if i > 0:
                    expected_previous = logs[i-1].hash
                    if log.previous_hash != expected_previous:
                        return IntegrityResult(
                            valid=False,
                            verified_count=i,
                            error=f"Chain broken at log {log.id}",
                            corrupted_entry_id=str(log.id)
                        )
            
            return IntegrityResult(
                valid=True,
                verified_count=len(logs),
                message=f"Successfully verified {len(logs)} log entries"
            )
            
        except Exception as e:
            self.logger.error(f"Integrity verification failed: {e}")
            return IntegrityResult(
                valid=False,
                verified_count=0,
                error=f"Verification error: {e}"
            )
    
    async def query_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogModel]:
        """
        Query audit logs with filtering.
        
        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            resource: Filter by resource (supports partial matching)
            action: Filter by action
            result: Filter by result (success/failure)
            start_time: Filter by start time
            end_time: Filter by end time
            ip_address: Filter by IP address
            session_id: Filter by session ID
            limit: Maximum number of results
            offset: Result offset for pagination
            
        Returns:
            List of matching audit log entries
        """
        stmt = select(AuditLogModel)
        
        # Apply filters
        conditions = []
        
        if user_id:
            conditions.append(AuditLogModel.user_id == user_id)
        
        if event_type:
            conditions.append(AuditLogModel.event_type == event_type)
        
        if resource:
            conditions.append(AuditLogModel.resource.ilike(f"%{resource}%"))
        
        if action:
            conditions.append(AuditLogModel.action == action)
        
        if result is not None:
            conditions.append(AuditLogModel.result == result)
        
        if start_time:
            conditions.append(AuditLogModel.timestamp >= start_time)
        
        if end_time:
            conditions.append(AuditLogModel.timestamp <= end_time)
        
        if ip_address:
            conditions.append(AuditLogModel.ip_address == ip_address)
        
        if session_id:
            conditions.append(AuditLogModel.session_id == session_id)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        # Order by timestamp (newest first)
        stmt = stmt.order_by(desc(AuditLogModel.timestamp))
        
        # Apply pagination
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def export_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        format: str = "json",
        user_id: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> bytes:
        """
        Export audit logs in specified format.
        
        Args:
            start_time: Export start time
            end_time: Export end time
            format: Export format ('json', 'csv')
            user_id: Filter by user ID (optional)
            event_type: Filter by event type (optional)
            
        Returns:
            Exported data as bytes
        """
        # Query logs for export
        logs = await self.query_logs(
            user_id=user_id,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            limit=10000  # Large limit for export
        )
        
        if format.lower() == "json":
            return self._export_json(logs)
        elif format.lower() == "csv":
            return self._export_csv(logs)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_json(self, logs: List[AuditLogModel]) -> bytes:
        """Export logs as JSON."""
        log_data = []
        
        for log in logs:
            log_data.append({
                "id": str(log.id),
                "event_type": log.event_type,
                "user_id": log.user_id,
                "resource": log.resource,
                "action": log.action,
                "result": log.result,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "session_id": log.session_id,
                "timestamp": log.timestamp.isoformat(),
                "hash": log.hash,
                "previous_hash": log.previous_hash
            })
        
        return json.dumps(log_data, indent=2, default=str).encode('utf-8')
    
    def _export_csv(self, logs: List[AuditLogModel]) -> bytes:
        """Export logs as CSV."""
        output = io.StringIO()
        
        fieldnames = [
            'id', 'timestamp', 'event_type', 'user_id', 'resource', 'action',
            'result', 'ip_address', 'user_agent', 'session_id', 'details', 'hash'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for log in logs:
            writer.writerow({
                'id': str(log.id),
                'timestamp': log.timestamp.isoformat(),
                'event_type': log.event_type,
                'user_id': log.user_id,
                'resource': log.resource or '',
                'action': log.action or '',
                'result': log.result,
                'ip_address': log.ip_address or '',
                'user_agent': log.user_agent or '',
                'session_id': log.session_id or '',
                'details': json.dumps(log.details or {}),
                'hash': log.hash
            })
        
        return output.getvalue().encode('utf-8')
    
    async def apply_retention_policy(self, retention_days: int) -> int:
        """
        Apply log retention policy by archiving old logs.
        
        Args:
            retention_days: Number of days to retain logs
            
        Returns:
            Number of logs archived/deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Find old logs
        stmt = select(AuditLogModel).where(AuditLogModel.timestamp < cutoff_date)
        result = await self.db.execute(stmt)
        old_logs = list(result.scalars().all())
        
        if not old_logs:
            return 0
        
        # Archive logs (in production, this would move to archive storage)
        archived_count = len(old_logs)
        
        # For now, we'll keep logs but mark them as archived
        # In production, you might move them to cold storage
        self.logger.info(f"Would archive {archived_count} logs older than {retention_days} days")
        
        # Optionally delete very old logs (be careful with this!)
        # delete_stmt = delete(AuditLogModel).where(AuditLogModel.timestamp < cutoff_date)
        # await self.db.execute(delete_stmt)
        # await self.db.commit()
        
        return archived_count
    
    async def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit log statistics.
        
        Args:
            start_time: Statistics start time (optional)
            end_time: Statistics end time (optional)
            
        Returns:
            Dictionary with statistics
        """
        stmt = select(AuditLogModel)
        
        if start_time:
            stmt = stmt.where(AuditLogModel.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(AuditLogModel.timestamp <= end_time)
        
        # Total count
        count_stmt = select(func.count(AuditLogModel.id))
        if start_time:
            count_stmt = count_stmt.where(AuditLogModel.timestamp >= start_time)
        if end_time:
            count_stmt = count_stmt.where(AuditLogModel.timestamp <= end_time)
        
        result = await self.db.execute(count_stmt)
        total_logs = result.scalar()
        
        # Event type distribution
        event_type_stmt = select(
            AuditLogModel.event_type,
            func.count(AuditLogModel.id).label('count')
        ).group_by(AuditLogModel.event_type)
        
        if start_time:
            event_type_stmt = event_type_stmt.where(AuditLogModel.timestamp >= start_time)
        if end_time:
            event_type_stmt = event_type_stmt.where(AuditLogModel.timestamp <= end_time)
        
        result = await self.db.execute(event_type_stmt)
        event_types = {row.event_type: row.count for row in result}
        
        # Success/failure distribution
        result_stmt = select(
            AuditLogModel.result,
            func.count(AuditLogModel.id).label('count')
        ).group_by(AuditLogModel.result)
        
        if start_time:
            result_stmt = result_stmt.where(AuditLogModel.timestamp >= start_time)
        if end_time:
            result_stmt = result_stmt.where(AuditLogModel.timestamp <= end_time)
        
        result = await self.db.execute(result_stmt)
        results = {str(row.result): row.count for row in result}
        
        return {
            "total_logs": total_logs,
            "event_types": event_types,
            "results": results,
            "period": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            }
        }


class IntegrityResult:
    """Result of audit log integrity verification."""
    
    def __init__(
        self,
        valid: bool,
        verified_count: int = 0,
        error: Optional[str] = None,
        message: Optional[str] = None,
        corrupted_entry_id: Optional[str] = None
    ):
        self.valid = valid
        self.verified_count = verified_count
        self.error = error
        self.message = message
        self.corrupted_entry_id = corrupted_entry_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "valid": self.valid,
            "verified_count": self.verified_count,
            "error": self.error,
            "message": self.message,
            "corrupted_entry_id": self.corrupted_entry_id
        }