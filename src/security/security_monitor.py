"""
Security Monitor for SuperInsight Platform.

Implements real-time security monitoring and alerting functionality.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4
from dataclasses import dataclass, field
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from src.models.security import SecurityEventModel, AuditLogModel
from src.security.audit_logger import AuditLogger


@dataclass
class SecurityEvent:
    """Security event data structure."""
    id: str
    event_type: str
    severity: str  # low, medium, high, critical
    user_id: str
    details: Dict[str, Any]
    status: str = "open"  # open, investigating, resolved
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "severity": self.severity,
            "user_id": self.user_id,
            "details": self.details,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes
        }


@dataclass
class SecurityPostureReport:
    """Security posture report."""
    risk_score: float
    events_by_type: Dict[str, int]
    trend: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "events_by_type": self.events_by_type,
            "trend": self.trend,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat()
        }


class NotificationService:
    """Mock notification service for sending alerts."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.NotificationService")
    
    async def send(
        self,
        user_id: str,
        channel: str,
        title: str,
        message: str,
        priority: str = "normal"
    ) -> bool:
        """
        Send notification to user.
        
        Args:
            user_id: Target user ID
            channel: Notification channel (email, sms, slack, etc.)
            title: Notification title
            message: Notification message
            priority: Priority level
            
        Returns:
            True if sent successfully
        """
        self.logger.info(f"Sending {channel} notification to {user_id}: {title}")
        # In a real implementation, this would integrate with email/SMS/Slack APIs
        return True


class SecurityMonitor:
    """
    Real-time security monitor with threat detection and alerting.
    
    Monitors various security events and generates alerts for suspicious activities.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        audit_logger: AuditLogger,
        notification_service: Optional[NotificationService] = None
    ):
        self.db = db
        self.audit_logger = audit_logger
        self.notification_service = notification_service or NotificationService()
        self.logger = logging.getLogger(__name__)
        
        # Thresholds for various security events
        self.thresholds = {
            "failed_login_attempts": 5,
            "failed_login_window_minutes": 30,
            "mass_download_threshold": 100,
            "mass_download_window_minutes": 60,
            "unusual_location_threshold": 0.8,  # Confidence threshold
            "high_privilege_roles": ["admin", "superuser", "security_admin"]
        }
    
    async def monitor_login_attempts(
        self,
        user_id: str,
        ip_address: str,
        success: bool,
        user_agent: Optional[str] = None
    ) -> Optional[SecurityEvent]:
        """
        Monitor login attempts for suspicious patterns.
        
        Args:
            user_id: User attempting login
            ip_address: Source IP address
            success: Whether login was successful
            user_agent: User agent string (optional)
            
        Returns:
            SecurityEvent if suspicious activity detected, None otherwise
        """
        # Log the login attempt
        await self.audit_logger.log(
            event_type="login_attempt",
            user_id=user_id,
            ip_address=ip_address,
            result=success,
            details={
                "user_agent": user_agent,
                "success": success
            }
        )
        
        if not success:
            # Check for brute force attempts
            failed_count = await self._get_failed_login_count(
                user_id,
                minutes=self.thresholds["failed_login_window_minutes"]
            )
            
            if failed_count >= self.thresholds["failed_login_attempts"]:
                event = await self._create_security_event(
                    event_type="brute_force_attempt",
                    severity="high",
                    user_id=user_id,
                    details={
                        "failed_count": failed_count,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "window_minutes": self.thresholds["failed_login_window_minutes"]
                    }
                )
                await self._send_alert(event)
                return event
        else:
            # Check for unusual location login
            if await self._is_unusual_location(user_id, ip_address):
                event = await self._create_security_event(
                    event_type="unusual_location_login",
                    severity="medium",
                    user_id=user_id,
                    details={
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "location_analysis": "IP address not seen in recent history"
                    }
                )
                await self._send_alert(event)
                return event
        
        return None
    
    async def monitor_data_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[SecurityEvent]:
        """
        Monitor data access for suspicious patterns.
        
        Args:
            user_id: User accessing data
            resource: Resource being accessed
            action: Action being performed
            ip_address: Source IP address (optional)
            session_id: Session ID (optional)
            
        Returns:
            SecurityEvent if suspicious activity detected, None otherwise
        """
        # Log the data access
        await self.audit_logger.log(
            event_type="data_access",
            user_id=user_id,
            resource=resource,
            action=action,
            ip_address=ip_address,
            session_id=session_id,
            result=True
        )
        
        # Check for mass download
        if action in ["download", "export", "read"]:
            access_count = await self._get_access_count(
                user_id,
                action,
                minutes=self.thresholds["mass_download_window_minutes"]
            )
            
            if access_count >= self.thresholds["mass_download_threshold"]:
                event = await self._create_security_event(
                    event_type="mass_download",
                    severity="high",
                    user_id=user_id,
                    details={
                        "access_count": access_count,
                        "action": action,
                        "resource": resource,
                        "ip_address": ip_address,
                        "window_minutes": self.thresholds["mass_download_window_minutes"]
                    }
                )
                await self._send_alert(event)
                return event
        
        # Check for sensitive data access
        if await self._is_sensitive_resource(resource):
            event = await self._create_security_event(
                event_type="sensitive_data_access",
                severity="medium",
                user_id=user_id,
                details={
                    "resource": resource,
                    "action": action,
                    "ip_address": ip_address,
                    "sensitivity_level": "high"
                }
            )
            # Log but don't necessarily alert for all sensitive access
            return event
        
        return None
    
    async def monitor_permission_escalation(
        self,
        user_id: str,
        target_user_id: str,
        new_role: str,
        previous_role: Optional[str] = None
    ) -> Optional[SecurityEvent]:
        """
        Monitor permission escalation for suspicious patterns.
        
        Args:
            user_id: User making the change
            target_user_id: User whose permissions are being changed
            new_role: New role being assigned
            previous_role: Previous role (optional)
            
        Returns:
            SecurityEvent if suspicious activity detected, None otherwise
        """
        # Log the permission change
        await self.audit_logger.log(
            event_type="permission_change",
            user_id=user_id,
            resource=f"user:{target_user_id}",
            action="role_assignment",
            result=True,
            details={
                "target_user_id": target_user_id,
                "new_role": new_role,
                "previous_role": previous_role,
                "change_type": "role"
            }
        )
        
        # Check for self-privilege escalation
        if user_id == target_user_id:
            event = await self._create_security_event(
                event_type="self_privilege_escalation",
                severity="critical",
                user_id=user_id,
                details={
                    "new_role": new_role,
                    "previous_role": previous_role,
                    "escalation_type": "self"
                }
            )
            await self._send_alert(event)
            return event
        
        # Check for high privilege role assignment
        if await self._is_high_privilege_role(new_role):
            event = await self._create_security_event(
                event_type="high_privilege_grant",
                severity="high",
                user_id=user_id,
                details={
                    "target_user_id": target_user_id,
                    "new_role": new_role,
                    "previous_role": previous_role,
                    "privilege_level": "high"
                }
            )
            await self._send_alert(event)
            return event
        
        return None
    
    async def _create_security_event(
        self,
        event_type: str,
        severity: str,
        user_id: str,
        details: Dict[str, Any]
    ) -> SecurityEvent:
        """
        Create and persist a security event.
        
        Args:
            event_type: Type of security event
            severity: Severity level (low, medium, high, critical)
            user_id: Associated user ID
            details: Event details
            
        Returns:
            Created SecurityEvent
        """
        event_id = str(uuid4())
        
        # Create database record
        db_event = SecurityEventModel(
            id=event_id,
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            details=details,
            status="open",
            created_at=datetime.utcnow()
        )
        
        self.db.add(db_event)
        await self.db.commit()
        
        # Create event object
        event = SecurityEvent(
            id=event_id,
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            details=details
        )
        
        self.logger.warning(f"Security event created: {event_type} (severity: {severity}) for user {user_id}")
        
        return event
    
    async def _send_alert(self, event: SecurityEvent) -> None:
        """
        Send security alert to administrators.
        
        Args:
            event: Security event to alert about
        """
        # Get security administrators
        admins = await self._get_security_admins()
        
        # Determine alert priority based on severity
        priority_map = {
            "low": "normal",
            "medium": "high",
            "high": "urgent",
            "critical": "emergency"
        }
        priority = priority_map.get(event.severity, "normal")
        
        # Send alerts
        for admin in admins:
            try:
                await self.notification_service.send(
                    user_id=admin["id"],
                    channel="email",
                    title=f"Security Alert - {event.severity.upper()}",
                    message=f"Security event detected: {event.event_type}\n"
                           f"User: {event.user_id}\n"
                           f"Details: {event.details}",
                    priority=priority
                )
            except Exception as e:
                self.logger.error(f"Failed to send alert to admin {admin['id']}: {e}")
    
    async def generate_security_posture_report(
        self,
        days: int = 30
    ) -> SecurityPostureReport:
        """
        Generate security posture report.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            SecurityPostureReport with current security posture
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Get security events by type
        events_by_type = await self._get_events_by_type(start_time, end_time)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(events_by_type)
        
        # Get security trend
        trend = await self._get_security_trend(start_time, end_time)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(events_by_type, risk_score)
        
        return SecurityPostureReport(
            risk_score=risk_score,
            events_by_type=events_by_type,
            trend=trend,
            recommendations=recommendations
        )
    
    async def _get_failed_login_count(self, user_id: str, minutes: int) -> int:
        """Get count of failed login attempts in time window."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        failed_logins = await self.audit_logger.query_logs(
            user_id=user_id,
            event_type="login_attempt",
            result=False,
            start_time=cutoff_time,
            limit=1000
        )
        
        return len(failed_logins)
    
    async def _get_access_count(self, user_id: str, action: str, minutes: int) -> int:
        """Get count of data access attempts in time window."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        accesses = await self.audit_logger.query_logs(
            user_id=user_id,
            event_type="data_access",
            action=action,
            start_time=cutoff_time,
            limit=1000
        )
        
        return len(accesses)
    
    async def _is_unusual_location(self, user_id: str, ip_address: str) -> bool:
        """Check if IP address is unusual for user."""
        # Get recent login history
        recent_logins = await self.audit_logger.query_logs(
            user_id=user_id,
            event_type="login_attempt",
            result=True,
            start_time=datetime.utcnow() - timedelta(days=30),
            limit=100
        )
        
        # Check if IP has been seen before
        seen_ips = set()
        for login in recent_logins:
            if login.ip_address:
                seen_ips.add(login.ip_address)
        
        # Simple check - in production, you'd use geolocation services
        return ip_address not in seen_ips and len(seen_ips) > 0
    
    async def _is_sensitive_resource(self, resource: str) -> bool:
        """Check if resource is considered sensitive."""
        sensitive_patterns = [
            "personal_data",
            "financial",
            "medical",
            "confidential",
            "secret",
            "private"
        ]
        
        resource_lower = resource.lower()
        return any(pattern in resource_lower for pattern in sensitive_patterns)
    
    async def _is_high_privilege_role(self, role: str) -> bool:
        """Check if role is considered high privilege."""
        return role.lower() in [r.lower() for r in self.thresholds["high_privilege_roles"]]
    
    async def _get_security_admins(self) -> List[Dict[str, str]]:
        """Get list of security administrators."""
        # In a real implementation, this would query the user/role database
        return [
            {"id": "admin1", "email": "security@company.com"},
            {"id": "admin2", "email": "admin@company.com"}
        ]
    
    async def _get_events_by_type(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, int]:
        """Get security events grouped by type."""
        stmt = select(
            SecurityEventModel.event_type,
            func.count(SecurityEventModel.id).label('count')
        ).where(
            and_(
                SecurityEventModel.created_at >= start_time,
                SecurityEventModel.created_at <= end_time
            )
        ).group_by(SecurityEventModel.event_type)
        
        result = await self.db.execute(stmt)
        return {row.event_type: row.count for row in result}
    
    def _calculate_risk_score(self, events_by_type: Dict[str, int]) -> float:
        """Calculate overall risk score based on security events."""
        # Risk weights for different event types
        risk_weights = {
            "brute_force_attempt": 10,
            "self_privilege_escalation": 20,
            "mass_download": 8,
            "unusual_location_login": 5,
            "high_privilege_grant": 7,
            "sensitive_data_access": 3,
            "data_breach": 25
        }
        
        total_risk = 0
        for event_type, count in events_by_type.items():
            weight = risk_weights.get(event_type, 1)
            total_risk += count * weight
        
        # Normalize to 0-100 scale
        max_possible_risk = 1000  # Arbitrary maximum
        risk_score = min(100, (total_risk / max_possible_risk) * 100)
        
        return round(risk_score, 1)
    
    async def _get_security_trend(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Get security event trend over time."""
        # Group events by day
        trend_data = []
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())
            
            # Count events for this day
            stmt = select(func.count(SecurityEventModel.id)).where(
                and_(
                    SecurityEventModel.created_at >= day_start,
                    SecurityEventModel.created_at <= day_end
                )
            )
            
            result = await self.db.execute(stmt)
            count = result.scalar()
            
            trend_data.append({
                "date": current_date.isoformat(),
                "count": count
            })
            
            current_date += timedelta(days=1)
        
        return trend_data
    
    def _generate_recommendations(
        self,
        events_by_type: Dict[str, int],
        risk_score: float
    ) -> List[str]:
        """Generate security recommendations based on events."""
        recommendations = []
        
        if events_by_type.get("brute_force_attempt", 0) > 0:
            recommendations.append("Consider implementing account lockout policies")
            recommendations.append("Enable multi-factor authentication for all users")
        
        if events_by_type.get("unusual_location_login", 0) > 5:
            recommendations.append("Review and update IP whitelist policies")
            recommendations.append("Consider implementing geo-blocking for high-risk regions")
        
        if events_by_type.get("mass_download", 0) > 0:
            recommendations.append("Review data access patterns and implement rate limiting")
            recommendations.append("Consider data loss prevention (DLP) solutions")
        
        if events_by_type.get("self_privilege_escalation", 0) > 0:
            recommendations.append("Implement approval workflows for privilege changes")
            recommendations.append("Review and audit administrative access regularly")
        
        if risk_score > 70:
            recommendations.append("Immediate security review recommended")
            recommendations.append("Consider engaging external security consultants")
        elif risk_score > 40:
            recommendations.append("Increase security monitoring frequency")
            recommendations.append("Review and update security policies")
        
        if not recommendations:
            recommendations.append("Security posture is good - maintain current practices")
            recommendations.append("Continue regular security monitoring and reviews")
        
        return recommendations