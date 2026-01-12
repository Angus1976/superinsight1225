"""
Alert Manager for High Availability System.

Provides intelligent alert management, notification routing,
alert deduplication, and escalation handling.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import hashlib

logger = logging.getLogger(__name__)


class AlertChannel(Enum):
    """Alert notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"
    LOG = "log"


class AlertPriority(Enum):
    """Alert priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class AlertStatus(Enum):
    """Alert lifecycle status."""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    SILENCED = "silenced"
    ESCALATED = "escalated"


@dataclass
class Alert:
    """Represents an alert instance."""
    alert_id: str
    name: str
    message: str
    priority: AlertPriority
    status: AlertStatus = AlertStatus.NEW
    source: str = "system"
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    acknowledged_by: Optional[str] = None
    fingerprint: Optional[str] = None
    occurrence_count: int = 1
    last_occurrence: float = field(default_factory=time.time)


@dataclass
class SilenceRule:
    """Rule for silencing alerts."""
    silence_id: str
    matchers: Dict[str, str]  # label -> value
    starts_at: float
    ends_at: float
    created_by: str
    comment: str = ""


@dataclass
class EscalationPolicy:
    """Policy for alert escalation."""
    policy_id: str
    name: str
    levels: List[Dict[str, Any]]  # List of escalation levels
    enabled: bool = True


@dataclass
class AlertManagerConfig:
    """Configuration for alert manager."""
    dedup_window_seconds: int = 300
    resolve_timeout_seconds: int = 3600
    max_alerts: int = 10000
    default_channels: List[AlertChannel] = field(default_factory=lambda: [AlertChannel.LOG])
    enable_deduplication: bool = True
    enable_escalation: bool = True


class AlertManager:
    """
    Intelligent alert management system.
    
    Features:
    - Alert deduplication
    - Priority-based routing
    - Silence rules
    - Escalation policies
    - Multi-channel notifications
    - Alert lifecycle management
    """
    
    def __init__(self, config: Optional[AlertManagerConfig] = None):
        self.config = config or AlertManagerConfig()
        self.alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=10000)
        self.silence_rules: Dict[str, SilenceRule] = {}
        self.escalation_policies: Dict[str, EscalationPolicy] = {}
        self.notification_handlers: Dict[AlertChannel, Callable] = {}
        self.fingerprint_map: Dict[str, str] = {}  # fingerprint -> alert_id
        
        # Register default handlers
        self._register_default_handlers()
        
        # Setup default escalation policy
        self._setup_default_escalation()
        
        logger.info("AlertManager initialized")
    
    def _register_default_handlers(self):
        """Register default notification handlers."""
        self.register_handler(AlertChannel.LOG, self._log_notification)
        self.register_handler(AlertChannel.WEBHOOK, self._webhook_notification)
    
    def _setup_default_escalation(self):
        """Setup default escalation policy."""
        default_policy = EscalationPolicy(
            policy_id="default",
            name="Default Escalation Policy",
            levels=[
                {
                    "level": 1,
                    "delay_minutes": 0,
                    "channels": [AlertChannel.LOG, AlertChannel.SLACK],
                    "notify": ["on-call-primary"]
                },
                {
                    "level": 2,
                    "delay_minutes": 15,
                    "channels": [AlertChannel.EMAIL, AlertChannel.SLACK],
                    "notify": ["on-call-secondary", "team-lead"]
                },
                {
                    "level": 3,
                    "delay_minutes": 30,
                    "channels": [AlertChannel.SMS, AlertChannel.PAGERDUTY],
                    "notify": ["engineering-manager", "on-call-all"]
                }
            ]
        )
        self.escalation_policies["default"] = default_policy
    
    def register_handler(self, channel: AlertChannel, handler: Callable):
        """Register a notification handler for a channel."""
        self.notification_handlers[channel] = handler
        logger.debug(f"Registered notification handler for {channel.value}")
    
    def _generate_fingerprint(self, alert: Alert) -> str:
        """Generate a fingerprint for alert deduplication."""
        # Create fingerprint from name and key labels
        key_parts = [alert.name, alert.source]
        key_parts.extend(f"{k}={v}" for k, v in sorted(alert.labels.items()))
        
        fingerprint_str = "|".join(key_parts)
        return hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]
    
    async def create_alert(
        self,
        name: str,
        message: str,
        priority: AlertPriority,
        source: str = "system",
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None
    ) -> Alert:
        """
        Create a new alert.
        
        Args:
            name: Alert name
            message: Alert message
            priority: Alert priority
            source: Alert source
            labels: Alert labels
            annotations: Additional annotations
        
        Returns:
            Created or deduplicated Alert
        """
        alert_id = str(uuid.uuid4())[:8]
        
        alert = Alert(
            alert_id=alert_id,
            name=name,
            message=message,
            priority=priority,
            source=source,
            labels=labels or {},
            annotations=annotations or {}
        )
        
        # Generate fingerprint
        fingerprint = self._generate_fingerprint(alert)
        alert.fingerprint = fingerprint
        
        # Check for deduplication
        if self.config.enable_deduplication:
            existing_id = self.fingerprint_map.get(fingerprint)
            if existing_id and existing_id in self.alerts:
                existing = self.alerts[existing_id]
                # Check if within dedup window
                if time.time() - existing.last_occurrence < self.config.dedup_window_seconds:
                    # Update existing alert
                    existing.occurrence_count += 1
                    existing.last_occurrence = time.time()
                    existing.updated_at = time.time()
                    logger.debug(f"Deduplicated alert: {name} (count: {existing.occurrence_count})")
                    return existing
        
        # Check silence rules
        if self._is_silenced(alert):
            alert.status = AlertStatus.SILENCED
            logger.info(f"Alert silenced: {name}")
        
        # Store alert
        self.alerts[alert_id] = alert
        self.fingerprint_map[fingerprint] = alert_id
        
        # Cleanup old alerts if needed
        await self._cleanup_old_alerts()
        
        # Send notifications if not silenced
        if alert.status != AlertStatus.SILENCED:
            await self._send_notifications(alert)
        
        logger.info(f"Created alert: {name} ({alert_id}) - Priority: {priority.name}")
        return alert
    
    def _is_silenced(self, alert: Alert) -> bool:
        """Check if alert matches any silence rule."""
        current_time = time.time()
        
        for silence in self.silence_rules.values():
            # Check if silence is active
            if not (silence.starts_at <= current_time <= silence.ends_at):
                continue
            
            # Check if alert matches all matchers
            matches = True
            for label, value in silence.matchers.items():
                if alert.labels.get(label) != value:
                    matches = False
                    break
            
            if matches:
                return True
        
        return False
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert."""
        # Determine channels based on priority
        channels = self._get_channels_for_priority(alert.priority)
        
        for channel in channels:
            handler = self.notification_handlers.get(channel)
            if handler:
                try:
                    await handler(alert)
                except Exception as e:
                    logger.error(f"Failed to send {channel.value} notification: {e}")
    
    def _get_channels_for_priority(self, priority: AlertPriority) -> List[AlertChannel]:
        """Get notification channels based on priority."""
        channel_map = {
            AlertPriority.LOW: [AlertChannel.LOG],
            AlertPriority.MEDIUM: [AlertChannel.LOG, AlertChannel.SLACK],
            AlertPriority.HIGH: [AlertChannel.LOG, AlertChannel.SLACK, AlertChannel.EMAIL],
            AlertPriority.CRITICAL: [AlertChannel.LOG, AlertChannel.SLACK, AlertChannel.EMAIL, AlertChannel.WEBHOOK],
            AlertPriority.EMERGENCY: [AlertChannel.LOG, AlertChannel.SLACK, AlertChannel.EMAIL, AlertChannel.SMS, AlertChannel.PAGERDUTY],
        }
        return channel_map.get(priority, self.config.default_channels)
    
    async def _cleanup_old_alerts(self):
        """Cleanup old resolved alerts."""
        if len(self.alerts) <= self.config.max_alerts:
            return
        
        current_time = time.time()
        to_remove = []
        
        for alert_id, alert in self.alerts.items():
            if alert.status == AlertStatus.RESOLVED:
                if current_time - alert.resolved_at > 3600:  # 1 hour
                    to_remove.append(alert_id)
        
        for alert_id in to_remove:
            alert = self.alerts.pop(alert_id)
            if alert.fingerprint in self.fingerprint_map:
                del self.fingerprint_map[alert.fingerprint]
            self.alert_history.append(alert)
    
    # Default notification handlers
    async def _log_notification(self, alert: Alert):
        """Log notification handler."""
        log_level = {
            AlertPriority.LOW: logging.INFO,
            AlertPriority.MEDIUM: logging.WARNING,
            AlertPriority.HIGH: logging.WARNING,
            AlertPriority.CRITICAL: logging.ERROR,
            AlertPriority.EMERGENCY: logging.CRITICAL,
        }.get(alert.priority, logging.INFO)
        
        logger.log(log_level, f"[ALERT] {alert.name}: {alert.message}")
    
    async def _webhook_notification(self, alert: Alert):
        """Webhook notification handler."""
        # In real implementation, would send HTTP request
        logger.debug(f"Webhook notification for alert: {alert.name}")
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        alert = self.alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = time.time()
        alert.acknowledged_by = acknowledged_by
        alert.updated_at = time.time()
        
        logger.info(f"Alert acknowledged: {alert.name} by {acknowledged_by}")
        return True
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        alert = self.alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = time.time()
        alert.updated_at = time.time()
        
        logger.info(f"Alert resolved: {alert.name}")
        return True
    
    async def escalate_alert(self, alert_id: str, policy_id: str = "default") -> bool:
        """Escalate an alert."""
        alert = self.alerts.get(alert_id)
        if not alert:
            return False
        
        policy = self.escalation_policies.get(policy_id)
        if not policy or not policy.enabled:
            return False
        
        alert.status = AlertStatus.ESCALATED
        alert.updated_at = time.time()
        
        # Send escalation notifications
        for level in policy.levels:
            channels = level.get("channels", [])
            for channel in channels:
                handler = self.notification_handlers.get(channel)
                if handler:
                    try:
                        await handler(alert)
                    except Exception as e:
                        logger.error(f"Escalation notification failed: {e}")
        
        logger.warning(f"Alert escalated: {alert.name}")
        return True
    
    def add_silence(
        self,
        matchers: Dict[str, str],
        duration_minutes: int,
        created_by: str,
        comment: str = ""
    ) -> SilenceRule:
        """Add a silence rule."""
        silence_id = str(uuid.uuid4())[:8]
        current_time = time.time()
        
        silence = SilenceRule(
            silence_id=silence_id,
            matchers=matchers,
            starts_at=current_time,
            ends_at=current_time + (duration_minutes * 60),
            created_by=created_by,
            comment=comment
        )
        
        self.silence_rules[silence_id] = silence
        logger.info(f"Added silence rule: {silence_id} for {duration_minutes} minutes")
        return silence
    
    def remove_silence(self, silence_id: str) -> bool:
        """Remove a silence rule."""
        if silence_id in self.silence_rules:
            del self.silence_rules[silence_id]
            logger.info(f"Removed silence rule: {silence_id}")
            return True
        return False
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get an alert by ID."""
        return self.alerts.get(alert_id)
    
    def list_alerts(
        self,
        status: Optional[AlertStatus] = None,
        priority: Optional[AlertPriority] = None,
        source: Optional[str] = None,
        limit: int = 100
    ) -> List[Alert]:
        """List alerts with optional filtering."""
        alerts = list(self.alerts.values())
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if priority:
            alerts = [a for a in alerts if a.priority == priority]
        
        if source:
            alerts = [a for a in alerts if a.source == source]
        
        # Sort by priority (highest first) then by created_at (newest first)
        alerts.sort(key=lambda a: (-a.priority.value, -a.created_at))
        
        return alerts[:limit]
    
    def list_silences(self, active_only: bool = True) -> List[SilenceRule]:
        """List silence rules."""
        silences = list(self.silence_rules.values())
        
        if active_only:
            current_time = time.time()
            silences = [s for s in silences if s.starts_at <= current_time <= s.ends_at]
        
        return silences
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        alerts = list(self.alerts.values())
        
        return {
            "total_alerts": len(alerts),
            "by_status": {
                s.value: len([a for a in alerts if a.status == s])
                for s in AlertStatus
            },
            "by_priority": {
                p.name: len([a for a in alerts if a.priority == p])
                for p in AlertPriority
            },
            "active_silences": len([s for s in self.silence_rules.values() 
                                   if s.starts_at <= time.time() <= s.ends_at]),
            "escalation_policies": len(self.escalation_policies),
            "history_count": len(self.alert_history),
        }


# Global alert manager instance
alert_manager: Optional[AlertManager] = None


def initialize_alert_manager(config: Optional[AlertManagerConfig] = None) -> AlertManager:
    """Initialize the global alert manager."""
    global alert_manager
    alert_manager = AlertManager(config)
    return alert_manager


def get_alert_manager() -> Optional[AlertManager]:
    """Get the global alert manager instance."""
    return alert_manager


# Convenience functions
async def create_alert(
    name: str,
    message: str,
    priority: AlertPriority = AlertPriority.MEDIUM,
    **kwargs
) -> Optional[Alert]:
    """Create an alert using the global manager."""
    if alert_manager:
        return await alert_manager.create_alert(name, message, priority, **kwargs)
    return None


async def resolve_alert(alert_id: str) -> bool:
    """Resolve an alert using the global manager."""
    if alert_manager:
        return await alert_manager.resolve_alert(alert_id)
    return False
