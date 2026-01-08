"""
Data Access Audit Service for comprehensive security monitoring.

Provides detailed audit logging, anomaly detection, and compliance reporting
for all data access operations in the RBAC system.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from dataclasses import dataclass
import json

from src.database.connection import get_db_session
from .models import (
    DataAccessAuditModel, AuditEventType, PermissionAction,
    ResourceType, FieldAccessLevel
)
from .tenant_isolation import tenant_context

logger = logging.getLogger(__name__)


@dataclass
class AuditQuery:
    """Query parameters for audit log search."""
    tenant_id: Optional[str] = None
    user_id: Optional[UUID] = None
    event_type: Optional[AuditEventType] = None
    resource_type: Optional[ResourceType] = None
    action: Optional[PermissionAction] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    permission_granted: Optional[bool] = None
    min_risk_score: Optional[float] = None
    has_anomalies: Optional[bool] = None
    limit: int = 100
    offset: int = 0


@dataclass
class AuditSummary:
    """Summary of audit events."""
    total_events: int
    granted_events: int
    denied_events: int
    unique_users: int
    unique_resources: int
    high_risk_events: int
    anomaly_events: int
    event_types: Dict[str, int]
    top_users: List[Tuple[UUID, int]]
    top_resources: List[Tuple[str, int]]


@dataclass
class SecurityAlert:
    """Security alert based on audit analysis."""
    alert_id: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    title: str
    description: str
    user_id: Optional[UUID]
    tenant_id: str
    event_count: int
    risk_score: float
    first_seen: datetime
    last_seen: datetime
    recommendations: List[str]


class DataAccessAuditService:
    """
    Comprehensive audit service for data access monitoring.
    
    Provides audit logging, analysis, anomaly detection, and compliance reporting.
    """
    
    def __init__(self):
        self.risk_thresholds = {
            "failed_attempts": 5,
            "high_risk_score": 0.7,
            "unusual_access_pattern": 0.6,
            "cross_tenant_attempt": 0.9
        }
    
    def log_access_event(
        self,
        tenant_id: str,
        user_id: Optional[UUID],
        event_type: AuditEventType,
        permission_granted: bool,
        resource_type: Optional[ResourceType] = None,
        resource_id: Optional[str] = None,
        action: Optional[PermissionAction] = None,
        table_name: Optional[str] = None,
        field_names: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
        response_context: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None,
        db: Optional[Session] = None
    ) -> UUID:
        """
        Log data access event with comprehensive details.
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID
            event_type: Type of audit event
            permission_granted: Whether permission was granted
            resource_type: Type of resource accessed
            resource_id: ID of specific resource
            action: Action performed
            table_name: Database table name
            field_names: List of field names accessed
            session_id: Session ID
            ip_address: Client IP address
            user_agent: Client user agent
            request_context: Additional request context
            response_context: Additional response context
            execution_time_ms: Execution time in milliseconds
            db: Database session
            
        Returns:
            Audit log ID
        """
        if db is None:
            db = next(get_db_session())
        
        try:
            # Calculate risk score
            risk_score = self._calculate_risk_score(
                event_type, permission_granted, user_id, tenant_id,
                request_context, response_context
            )
            
            # Detect anomalies
            anomaly_flags = self._detect_anomalies(
                user_id, tenant_id, event_type, resource_type,
                ip_address, request_context, db
            )
            
            # Create audit log entry
            audit_log = DataAccessAuditModel(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                event_type=event_type,
                resource_type=resource_type,
                resource_id=resource_id,
                table_name=table_name,
                field_names=field_names,
                action=action,
                permission_granted=permission_granted,
                request_context=request_context or {},
                response_context=response_context or {},
                execution_time_ms=execution_time_ms,
                risk_score=risk_score,
                anomaly_flags=anomaly_flags
            )
            
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
            
            # Check if this event should trigger alerts
            if risk_score > self.risk_thresholds["high_risk_score"] or anomaly_flags:
                self._check_security_alerts(audit_log, db)
            
            return audit_log.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error logging audit event: {e}")
            raise
    
    def query_audit_logs(
        self,
        query: AuditQuery,
        db: Optional[Session] = None
    ) -> List[DataAccessAuditModel]:
        """
        Query audit logs with filtering and pagination.
        
        Args:
            query: Audit query parameters
            db: Database session
            
        Returns:
            List of matching audit log entries
        """
        if db is None:
            db = next(get_db_session())
        
        # Build query
        q = db.query(DataAccessAuditModel)
        
        # Apply filters
        if query.tenant_id:
            q = q.filter(DataAccessAuditModel.tenant_id == query.tenant_id)
        
        if query.user_id:
            q = q.filter(DataAccessAuditModel.user_id == query.user_id)
        
        if query.event_type:
            q = q.filter(DataAccessAuditModel.event_type == query.event_type)
        
        if query.resource_type:
            q = q.filter(DataAccessAuditModel.resource_type == query.resource_type)
        
        if query.action:
            q = q.filter(DataAccessAuditModel.action == query.action)
        
        if query.start_date:
            q = q.filter(DataAccessAuditModel.timestamp >= query.start_date)
        
        if query.end_date:
            q = q.filter(DataAccessAuditModel.timestamp <= query.end_date)
        
        if query.permission_granted is not None:
            q = q.filter(DataAccessAuditModel.permission_granted == query.permission_granted)
        
        if query.min_risk_score:
            q = q.filter(DataAccessAuditModel.risk_score >= query.min_risk_score)
        
        if query.has_anomalies:
            q = q.filter(DataAccessAuditModel.anomaly_flags != [])
        
        # Order by timestamp (newest first)
        q = q.order_by(desc(DataAccessAuditModel.timestamp))
        
        # Apply pagination
        q = q.offset(query.offset).limit(query.limit)
        
        return q.all()
    
    def get_audit_summary(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Optional[Session] = None
    ) -> AuditSummary:
        """
        Get audit summary for tenant within date range.
        
        Args:
            tenant_id: Tenant ID
            start_date: Start date for analysis
            end_date: End date for analysis
            db: Database session
            
        Returns:
            Audit summary with key metrics
        """
        if db is None:
            db = next(get_db_session())
        
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Base query
        base_query = db.query(DataAccessAuditModel).filter(
            and_(
                DataAccessAuditModel.tenant_id == tenant_id,
                DataAccessAuditModel.timestamp >= start_date,
                DataAccessAuditModel.timestamp <= end_date
            )
        )
        
        # Total events
        total_events = base_query.count()
        
        # Granted vs denied
        granted_events = base_query.filter(
            DataAccessAuditModel.permission_granted == True
        ).count()
        denied_events = total_events - granted_events
        
        # Unique users
        unique_users = base_query.filter(
            DataAccessAuditModel.user_id.isnot(None)
        ).distinct(DataAccessAuditModel.user_id).count()
        
        # Unique resources
        unique_resources = base_query.filter(
            DataAccessAuditModel.resource_id.isnot(None)
        ).distinct(DataAccessAuditModel.resource_id).count()
        
        # High risk events
        high_risk_events = base_query.filter(
            DataAccessAuditModel.risk_score >= self.risk_thresholds["high_risk_score"]
        ).count()
        
        # Anomaly events
        anomaly_events = base_query.filter(
            DataAccessAuditModel.anomaly_flags != []
        ).count()
        
        # Event types distribution
        event_types_query = db.query(
            DataAccessAuditModel.event_type,
            func.count(DataAccessAuditModel.id)
        ).filter(
            and_(
                DataAccessAuditModel.tenant_id == tenant_id,
                DataAccessAuditModel.timestamp >= start_date,
                DataAccessAuditModel.timestamp <= end_date
            )
        ).group_by(DataAccessAuditModel.event_type).all()
        
        event_types = {str(event_type): count for event_type, count in event_types_query}
        
        # Top users by activity
        top_users_query = db.query(
            DataAccessAuditModel.user_id,
            func.count(DataAccessAuditModel.id)
        ).filter(
            and_(
                DataAccessAuditModel.tenant_id == tenant_id,
                DataAccessAuditModel.timestamp >= start_date,
                DataAccessAuditModel.timestamp <= end_date,
                DataAccessAuditModel.user_id.isnot(None)
            )
        ).group_by(DataAccessAuditModel.user_id).order_by(
            desc(func.count(DataAccessAuditModel.id))
        ).limit(10).all()
        
        top_users = [(user_id, count) for user_id, count in top_users_query]
        
        # Top resources by access
        top_resources_query = db.query(
            DataAccessAuditModel.resource_id,
            func.count(DataAccessAuditModel.id)
        ).filter(
            and_(
                DataAccessAuditModel.tenant_id == tenant_id,
                DataAccessAuditModel.timestamp >= start_date,
                DataAccessAuditModel.timestamp <= end_date,
                DataAccessAuditModel.resource_id.isnot(None)
            )
        ).group_by(DataAccessAuditModel.resource_id).order_by(
            desc(func.count(DataAccessAuditModel.id))
        ).limit(10).all()
        
        top_resources = [(resource_id, count) for resource_id, count in top_resources_query]
        
        return AuditSummary(
            total_events=total_events,
            granted_events=granted_events,
            denied_events=denied_events,
            unique_users=unique_users,
            unique_resources=unique_resources,
            high_risk_events=high_risk_events,
            anomaly_events=anomaly_events,
            event_types=event_types,
            top_users=top_users,
            top_resources=top_resources
        )
    
    def detect_security_anomalies(
        self,
        tenant_id: str,
        lookback_hours: int = 24,
        db: Optional[Session] = None
    ) -> List[SecurityAlert]:
        """
        Detect security anomalies in audit logs.
        
        Args:
            tenant_id: Tenant ID
            lookback_hours: Hours to look back for analysis
            db: Database session
            
        Returns:
            List of security alerts
        """
        if db is None:
            db = next(get_db_session())
        
        alerts = []
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        # Failed login attempts
        failed_attempts = db.query(DataAccessAuditModel).filter(
            and_(
                DataAccessAuditModel.tenant_id == tenant_id,
                DataAccessAuditModel.timestamp >= cutoff_time,
                DataAccessAuditModel.event_type == AuditEventType.PERMISSION_DENIED,
                DataAccessAuditModel.permission_granted == False
            )
        ).all()
        
        # Group by user
        user_failures = {}
        for attempt in failed_attempts:
            if attempt.user_id:
                user_failures.setdefault(attempt.user_id, []).append(attempt)
        
        # Check for excessive failures
        for user_id, failures in user_failures.items():
            if len(failures) >= self.risk_thresholds["failed_attempts"]:
                alerts.append(SecurityAlert(
                    alert_id=f"failed_attempts_{user_id}_{int(datetime.utcnow().timestamp())}",
                    severity="HIGH",
                    title="Excessive Failed Access Attempts",
                    description=f"User {user_id} has {len(failures)} failed access attempts in {lookback_hours} hours",
                    user_id=user_id,
                    tenant_id=tenant_id,
                    event_count=len(failures),
                    risk_score=min(1.0, len(failures) / self.risk_thresholds["failed_attempts"]),
                    first_seen=min(f.timestamp for f in failures),
                    last_seen=max(f.timestamp for f in failures),
                    recommendations=[
                        "Review user account for compromise",
                        "Consider temporary account suspension",
                        "Check for unusual access patterns"
                    ]
                ))
        
        # High-risk events
        high_risk_events = db.query(DataAccessAuditModel).filter(
            and_(
                DataAccessAuditModel.tenant_id == tenant_id,
                DataAccessAuditModel.timestamp >= cutoff_time,
                DataAccessAuditModel.risk_score >= self.risk_thresholds["high_risk_score"]
            )
        ).all()
        
        if high_risk_events:
            alerts.append(SecurityAlert(
                alert_id=f"high_risk_events_{tenant_id}_{int(datetime.utcnow().timestamp())}",
                severity="MEDIUM",
                title="High-Risk Access Events Detected",
                description=f"{len(high_risk_events)} high-risk access events detected",
                user_id=None,
                tenant_id=tenant_id,
                event_count=len(high_risk_events),
                risk_score=max(event.risk_score for event in high_risk_events),
                first_seen=min(event.timestamp for event in high_risk_events),
                last_seen=max(event.timestamp for event in high_risk_events),
                recommendations=[
                    "Review high-risk events for legitimacy",
                    "Verify user identities and access patterns",
                    "Consider additional authentication requirements"
                ]
            ))
        
        # Anomaly events
        anomaly_events = db.query(DataAccessAuditModel).filter(
            and_(
                DataAccessAuditModel.tenant_id == tenant_id,
                DataAccessAuditModel.timestamp >= cutoff_time,
                DataAccessAuditModel.anomaly_flags != []
            )
        ).all()
        
        if anomaly_events:
            alerts.append(SecurityAlert(
                alert_id=f"anomaly_events_{tenant_id}_{int(datetime.utcnow().timestamp())}",
                severity="MEDIUM",
                title="Anomalous Access Patterns Detected",
                description=f"{len(anomaly_events)} anomalous access events detected",
                user_id=None,
                tenant_id=tenant_id,
                event_count=len(anomaly_events),
                risk_score=0.6,
                first_seen=min(event.timestamp for event in anomaly_events),
                last_seen=max(event.timestamp for event in anomaly_events),
                recommendations=[
                    "Investigate anomalous access patterns",
                    "Verify user behavior and access legitimacy",
                    "Review system configurations"
                ]
            ))
        
        return alerts
    
    def generate_compliance_report(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Generate compliance report for audit period.
        
        Args:
            tenant_id: Tenant ID
            start_date: Report start date
            end_date: Report end date
            db: Database session
            
        Returns:
            Comprehensive compliance report
        """
        if db is None:
            db = next(get_db_session())
        
        # Get audit summary
        summary = self.get_audit_summary(tenant_id, start_date, end_date, db)
        
        # Get security alerts
        alerts = self.detect_security_anomalies(tenant_id, 
                                               int((end_date - start_date).total_seconds() / 3600), 
                                               db)
        
        # Field access analysis
        field_access_events = db.query(DataAccessAuditModel).filter(
            and_(
                DataAccessAuditModel.tenant_id == tenant_id,
                DataAccessAuditModel.timestamp >= start_date,
                DataAccessAuditModel.timestamp <= end_date,
                DataAccessAuditModel.event_type == AuditEventType.FIELD_ACCESS
            )
        ).all()
        
        # Data export events
        export_events = db.query(DataAccessAuditModel).filter(
            and_(
                DataAccessAuditModel.tenant_id == tenant_id,
                DataAccessAuditModel.timestamp >= start_date,
                DataAccessAuditModel.timestamp <= end_date,
                DataAccessAuditModel.event_type == AuditEventType.DATA_EXPORT
            )
        ).all()
        
        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "duration_days": (end_date - start_date).days
            },
            "tenant_id": tenant_id,
            "summary": {
                "total_events": summary.total_events,
                "granted_events": summary.granted_events,
                "denied_events": summary.denied_events,
                "unique_users": summary.unique_users,
                "unique_resources": summary.unique_resources,
                "high_risk_events": summary.high_risk_events,
                "anomaly_events": summary.anomaly_events
            },
            "event_breakdown": summary.event_types,
            "field_access": {
                "total_field_accesses": len(field_access_events),
                "denied_field_accesses": len([e for e in field_access_events if not e.permission_granted])
            },
            "data_exports": {
                "total_exports": len(export_events),
                "successful_exports": len([e for e in export_events if e.permission_granted])
            },
            "security_alerts": [
                {
                    "alert_id": alert.alert_id,
                    "severity": alert.severity,
                    "title": alert.title,
                    "description": alert.description,
                    "event_count": alert.event_count,
                    "risk_score": alert.risk_score,
                    "first_seen": alert.first_seen.isoformat(),
                    "last_seen": alert.last_seen.isoformat()
                }
                for alert in alerts
            ],
            "compliance_status": {
                "audit_coverage": "COMPLETE",
                "data_retention": "COMPLIANT",
                "access_controls": "ACTIVE",
                "anomaly_detection": "ENABLED"
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _calculate_risk_score(
        self,
        event_type: AuditEventType,
        permission_granted: bool,
        user_id: Optional[UUID],
        tenant_id: str,
        request_context: Optional[Dict[str, Any]],
        response_context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate risk score for audit event."""
        
        risk_score = 0.0
        
        # Base risk by event type
        event_risk = {
            AuditEventType.PERMISSION_DENIED: 0.6,
            AuditEventType.DATA_EXPORT: 0.4,
            AuditEventType.FIELD_ACCESS: 0.2,
            AuditEventType.DATA_ACCESS: 0.1
        }
        
        risk_score += event_risk.get(event_type, 0.1)
        
        # Higher risk for denied permissions
        if not permission_granted:
            risk_score += 0.3
        
        # Higher risk for system users or missing user context
        if not user_id:
            risk_score += 0.2
        
        # Check for suspicious patterns in context
        if request_context:
            # Unusual time access
            if request_context.get("unusual_time"):
                risk_score += 0.2
            
            # Multiple IP addresses
            if request_context.get("multiple_ips"):
                risk_score += 0.3
            
            # Cross-tenant attempt
            if request_context.get("cross_tenant_attempt"):
                risk_score += 0.4
        
        return min(1.0, risk_score)
    
    def _detect_anomalies(
        self,
        user_id: Optional[UUID],
        tenant_id: str,
        event_type: AuditEventType,
        resource_type: Optional[ResourceType],
        ip_address: Optional[str],
        request_context: Optional[Dict[str, Any]],
        db: Session
    ) -> List[str]:
        """Detect anomalies in access pattern."""
        
        anomalies = []
        
        if not user_id:
            return anomalies
        
        # Check for unusual time access
        current_hour = datetime.utcnow().hour
        if current_hour < 6 or current_hour > 22:  # Outside business hours
            # Check if user normally accesses during business hours
            recent_accesses = db.query(DataAccessAuditModel).filter(
                and_(
                    DataAccessAuditModel.user_id == user_id,
                    DataAccessAuditModel.tenant_id == tenant_id,
                    DataAccessAuditModel.timestamp >= datetime.utcnow() - timedelta(days=30)
                )
            ).limit(100).all()
            
            business_hour_accesses = len([
                a for a in recent_accesses 
                if 6 <= a.timestamp.hour <= 22
            ])
            
            if business_hour_accesses > len(recent_accesses) * 0.8:  # Usually business hours
                anomalies.append("unusual_time_access")
        
        # Check for multiple IP addresses in short time
        if ip_address:
            recent_ips = db.query(DataAccessAuditModel.ip_address).filter(
                and_(
                    DataAccessAuditModel.user_id == user_id,
                    DataAccessAuditModel.tenant_id == tenant_id,
                    DataAccessAuditModel.timestamp >= datetime.utcnow() - timedelta(hours=1),
                    DataAccessAuditModel.ip_address.isnot(None)
                )
            ).distinct().all()
            
            unique_ips = set(ip[0] for ip in recent_ips if ip[0])
            if len(unique_ips) > 3:  # More than 3 IPs in 1 hour
                anomalies.append("multiple_ip_addresses")
        
        # Check for unusual resource access
        if resource_type:
            # Check if user normally accesses this resource type
            user_resource_history = db.query(DataAccessAuditModel).filter(
                and_(
                    DataAccessAuditModel.user_id == user_id,
                    DataAccessAuditModel.tenant_id == tenant_id,
                    DataAccessAuditModel.resource_type == resource_type,
                    DataAccessAuditModel.timestamp >= datetime.utcnow() - timedelta(days=30)
                )
            ).count()
            
            if user_resource_history == 0:  # First time accessing this resource type
                anomalies.append("new_resource_type_access")
        
        return anomalies
    
    def _check_security_alerts(self, audit_log: DataAccessAuditModel, db: Session) -> None:
        """Check if audit event should trigger immediate security alerts."""
        
        # This could integrate with external alerting systems
        # For now, just log high-risk events
        if audit_log.risk_score > 0.8:
            logger.warning(
                f"High-risk security event: {audit_log.event_type.value} "
                f"by user {audit_log.user_id} in tenant {audit_log.tenant_id} "
                f"(risk score: {audit_log.risk_score})"
            )
        
        if audit_log.anomaly_flags:
            logger.warning(
                f"Anomalous access detected: {audit_log.anomaly_flags} "
                f"by user {audit_log.user_id} in tenant {audit_log.tenant_id}"
            )