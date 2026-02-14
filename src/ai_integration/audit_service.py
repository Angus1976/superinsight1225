"""
AI Integration Audit Service.

Provides comprehensive audit logging for AI gateway activities with:
- Data access logging with HMAC-SHA256 signatures
- Security event monitoring
- Audit log querying with filtering
- Tamper detection through cryptographic signatures

Requirements:
- 8.1: Log gateway data access with metadata
- 8.2: Log gateway operations with parameters
- 8.3: Immutable logs with cryptographic signatures
- 8.4: Query audit logs with filtering
"""

import hmac
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from src.models.ai_integration import AIAuditLog


class AuditService:
    """Service for auditing AI gateway activities."""

    def __init__(self, secret_key: str = "ai_gateway_audit_secret"):
        """Initialize audit service.

        Args:
            secret_key: Secret key for HMAC-SHA256 signature generation
        """
        self._secret_key = secret_key.encode()

    def log_data_access(
        self,
        gateway_id: str,
        tenant_id: str,
        resource: str,
        action: str,
        metadata: Dict[str, Any],
        db: Session,
        user_identifier: Optional[str] = None,
        channel: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AIAuditLog:
        """Log data access event with signature.

        Args:
            gateway_id: Gateway ID
            tenant_id: Tenant ID
            resource: Resource accessed
            action: Action performed
            metadata: Event metadata
            db: Database session
            user_identifier: User/channel identifier
            channel: Communication channel
            success: Whether operation succeeded
            error_message: Error message if failed

        Returns:
            Created audit log entry
        """
        log_entry = AIAuditLog(
            id=str(uuid4()),
            gateway_id=gateway_id,
            tenant_id=tenant_id,
            event_type="data_access",
            resource=resource,
            action=action,
            event_metadata=metadata,
            user_identifier=user_identifier,
            channel=channel,
            success=success,
            error_message=error_message,
            timestamp=datetime.utcnow()
        )

        # Generate HMAC-SHA256 signature
        log_entry.signature = self._generate_signature(log_entry)

        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        return log_entry

    def log_security_event(
        self,
        gateway_id: str,
        tenant_id: str,
        event_type: str,
        details: Dict[str, Any],
        db: Session,
        user_identifier: Optional[str] = None
    ) -> AIAuditLog:
        """Log security event for monitoring.

        Args:
            gateway_id: Gateway ID
            tenant_id: Tenant ID
            event_type: Type of security event
            details: Event details
            db: Database session
            user_identifier: User identifier

        Returns:
            Created audit log entry
        """
        log_entry = AIAuditLog(
            id=str(uuid4()),
            gateway_id=gateway_id,
            tenant_id=tenant_id,
            event_type=event_type,
            resource="security",
            action="monitor",
            event_metadata=details,
            user_identifier=user_identifier,
            success=True,
            timestamp=datetime.utcnow()
        )

        # Generate signature
        log_entry.signature = self._generate_signature(log_entry)

        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        return log_entry

    def query_audit_logs(
        self,
        db: Session,
        gateway_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        skill_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        operation_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AIAuditLog]:
        """Query audit logs with filtering.

        Args:
            db: Database session
            gateway_id: Filter by gateway ID
            tenant_id: Filter by tenant ID
            skill_name: Filter by skill name
            start_time: Filter by start time
            end_time: Filter by end time
            operation_type: Filter by operation type
            limit: Maximum results
            offset: Result offset

        Returns:
            List of matching audit log entries
        """
        query = db.query(AIAuditLog)

        # Apply filters
        filters = []
        if gateway_id:
            filters.append(AIAuditLog.gateway_id == gateway_id)
        if tenant_id:
            filters.append(AIAuditLog.tenant_id == tenant_id)
        if skill_name:
            filters.append(
                AIAuditLog.event_metadata["skill_name"].astext == skill_name
            )
        if start_time:
            filters.append(AIAuditLog.timestamp >= start_time)
        if end_time:
            filters.append(AIAuditLog.timestamp <= end_time)
        if operation_type:
            filters.append(AIAuditLog.event_type == operation_type)

        if filters:
            query = query.filter(and_(*filters))

        # Order by timestamp descending
        query = query.order_by(desc(AIAuditLog.timestamp))

        # Apply pagination
        query = query.limit(limit).offset(offset)

        return query.all()

    def _generate_signature(self, log_entry: AIAuditLog) -> str:
        """Generate HMAC-SHA256 signature for log entry.

        Args:
            log_entry: Audit log entry

        Returns:
            HMAC signature as hex string
        """
        # Create canonical representation
        canonical_data = {
            "id": log_entry.id,
            "gateway_id": log_entry.gateway_id,
            "tenant_id": log_entry.tenant_id,
            "event_type": log_entry.event_type,
            "resource": log_entry.resource,
            "action": log_entry.action,
            "timestamp": log_entry.timestamp.isoformat(),
            "metadata": log_entry.event_metadata,
            "success": log_entry.success
        }

        canonical_str = json.dumps(canonical_data, sort_keys=True)
        signature = hmac.new(
            self._secret_key,
            canonical_str.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    def verify_signature(
        self,
        log_entry: AIAuditLog
    ) -> bool:
        """Verify cryptographic signature of log entry.

        Args:
            log_entry: Audit log entry to verify

        Returns:
            True if signature is valid, False otherwise
        """
        if not log_entry.signature:
            return False

        expected_signature = self._generate_signature(log_entry)
        return hmac.compare_digest(log_entry.signature, expected_signature)
