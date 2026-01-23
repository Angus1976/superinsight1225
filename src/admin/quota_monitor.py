"""
Quota Monitor for SuperInsight Platform.

Tracks LLM API usage and alerts when approaching quota limits.
Integrates with AlertService for notification delivery.

This module follows async-first architecture using asyncio.
All I/O operations are non-blocking to prevent event loop blocking.

Validates Requirements: 10.4
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============== Quota Models ==============

class QuotaType(str, Enum):
    """Types of quotas that can be monitored."""
    TOKENS = "tokens"
    REQUESTS = "requests"
    COST = "cost"
    RATE = "rate"  # Requests per time period


class QuotaPeriod(str, Enum):
    """Quota reset periods."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class QuotaConfig(BaseModel):
    """Quota configuration for a service."""
    id: str = Field(..., description="Quota config ID")
    config_id: str = Field(..., description="Related LLM/service config ID")
    tenant_id: str = Field(..., description="Tenant ID")
    quota_type: QuotaType = Field(..., description="Type of quota")
    limit: float = Field(..., gt=0, description="Quota limit")
    period: QuotaPeriod = Field(default=QuotaPeriod.MONTHLY, description="Reset period")
    alert_threshold_percent: float = Field(default=80.0, ge=0, le=100, description="Alert threshold %")
    critical_threshold_percent: float = Field(default=95.0, ge=0, le=100, description="Critical threshold %")
    enabled: bool = Field(default=True, description="Whether monitoring is enabled")
    provider_name: str = Field(default="", description="LLM provider name")
    cost_per_token: Optional[float] = Field(default=None, description="Cost per token (for cost quotas)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class QuotaUsage(BaseModel):
    """Current quota usage."""
    config_id: str = Field(..., description="Config ID")
    tenant_id: str = Field(..., description="Tenant ID")
    quota_type: QuotaType = Field(..., description="Type of quota")
    current_usage: float = Field(default=0, description="Current usage")
    limit: float = Field(..., description="Quota limit")
    usage_percent: float = Field(default=0, description="Usage percentage")
    period_start: datetime = Field(..., description="Period start time")
    period_end: datetime = Field(..., description="Period end time")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    alert_triggered: bool = Field(default=False, description="Whether alert was triggered")
    critical_alert_triggered: bool = Field(default=False, description="Whether critical alert was triggered")
    remaining: float = Field(default=0, description="Remaining quota")
    estimated_exhaustion: Optional[datetime] = Field(default=None, description="Estimated exhaustion time")
    usage_history: List[Dict[str, Any]] = Field(default_factory=list, description="Recent usage history")


class UsageRecord(BaseModel):
    """Single usage record."""
    config_id: str = Field(..., description="Config ID")
    tenant_id: str = Field(..., description="Tenant ID")
    quota_type: QuotaType = Field(..., description="Type of quota")
    amount: float = Field(..., description="Usage amount")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class QuotaAlert(BaseModel):
    """Quota alert."""
    id: str = Field(..., description="Alert ID")
    config_id: str = Field(..., description="Config ID")
    tenant_id: str = Field(..., description="Tenant ID")
    quota_type: QuotaType = Field(..., description="Type of quota")
    usage_percent: float = Field(..., description="Usage percentage when alert triggered")
    threshold_percent: float = Field(..., description="Threshold that was exceeded")
    is_critical: bool = Field(default=False, description="Whether this is a critical alert")
    message: str = Field(..., description="Alert message")
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = Field(default=False, description="Whether alert was acknowledged")


# ============== Quota Monitor ==============

class QuotaMonitor:
    """
    Monitors LLM API quota usage and triggers alerts.

    Features:
    - Track token, request, and cost usage
    - Configurable alert thresholds
    - Automatic period-based reset
    - Usage trend estimation
    - Integration with AlertService

    Validates Requirements: 10.4
    """

    def __init__(self):
        """Initialize the quota monitor."""
        self._configs: Dict[str, QuotaConfig] = {}
        self._usage: Dict[str, QuotaUsage] = {}
        self._usage_records: Dict[str, List[UsageRecord]] = {}
        self._alert_history: List[QuotaAlert] = []
        self._alert_callbacks: List[Callable[[QuotaAlert], None]] = []
        self._lock = asyncio.Lock()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._check_interval_seconds: int = 60
        self._max_history_records: int = 1000
        logger.info("QuotaMonitor initialized")

    async def register_quota(self, config: QuotaConfig) -> QuotaUsage:
        """
        Register a quota configuration for monitoring.

        Args:
            config: Quota configuration

        Returns:
            Initial quota usage

        Validates Requirements: 10.4
        """
        async with self._lock:
            self._configs[config.id] = config

            # Calculate period boundaries
            period_start, period_end = self._calculate_period_boundaries(
                config.period, datetime.utcnow()
            )

            usage = QuotaUsage(
                config_id=config.config_id,
                tenant_id=config.tenant_id,
                quota_type=config.quota_type,
                current_usage=0,
                limit=config.limit,
                usage_percent=0,
                period_start=period_start,
                period_end=period_end,
                remaining=config.limit
            )

            self._usage[config.id] = usage
            self._usage_records[config.id] = []

            logger.info(
                f"Registered quota: {config.id} "
                f"(type: {config.quota_type.value}, limit: {config.limit})"
            )

            return usage

    async def unregister_quota(self, quota_id: str) -> bool:
        """Unregister a quota configuration."""
        async with self._lock:
            if quota_id not in self._configs:
                return False

            del self._configs[quota_id]
            if quota_id in self._usage:
                del self._usage[quota_id]
            if quota_id in self._usage_records:
                del self._usage_records[quota_id]

            logger.info(f"Unregistered quota: {quota_id}")
            return True

    def _calculate_period_boundaries(
        self,
        period: QuotaPeriod,
        reference_time: datetime
    ) -> tuple:
        """Calculate period start and end times."""
        now = reference_time

        if period == QuotaPeriod.HOURLY:
            start = now.replace(minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1)

        elif period == QuotaPeriod.DAILY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)

        elif period == QuotaPeriod.WEEKLY:
            # Start from Monday
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start = start - timedelta(days=now.weekday())
            end = start + timedelta(weeks=1)

        elif period == QuotaPeriod.MONTHLY:
            # Start from first of month
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # End at first of next month
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1)
            else:
                end = start.replace(month=now.month + 1)

        else:  # CUSTOM - default to monthly
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1)
            else:
                end = start.replace(month=now.month + 1)

        return start, end

    async def record_usage(
        self,
        quota_id: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[QuotaUsage]:
        """
        Record usage against a quota.

        Args:
            quota_id: Quota configuration ID
            amount: Usage amount
            metadata: Optional metadata

        Returns:
            Updated quota usage or None if quota not found

        Validates Requirements: 10.4
        """
        async with self._lock:
            if quota_id not in self._configs:
                logger.warning(f"Quota {quota_id} not found")
                return None

            config = self._configs[quota_id]
            usage = self._usage.get(quota_id)

            if not usage:
                logger.warning(f"No usage tracking for quota {quota_id}")
                return None

            # Check if period has reset
            now = datetime.utcnow()
            if now >= usage.period_end:
                # Reset usage for new period
                period_start, period_end = self._calculate_period_boundaries(
                    config.period, now
                )
                usage.current_usage = 0
                usage.period_start = period_start
                usage.period_end = period_end
                usage.alert_triggered = False
                usage.critical_alert_triggered = False
                logger.info(f"Quota {quota_id} reset for new period")

            # Record usage
            usage.current_usage += amount
            usage.usage_percent = (usage.current_usage / usage.limit) * 100
            usage.remaining = max(0, usage.limit - usage.current_usage)
            usage.last_updated = now

            # Update usage history
            record = UsageRecord(
                config_id=config.config_id,
                tenant_id=config.tenant_id,
                quota_type=config.quota_type,
                amount=amount,
                timestamp=now,
                metadata=metadata or {}
            )

            records = self._usage_records[quota_id]
            records.append(record)

            # Keep history limited
            if len(records) > self._max_history_records:
                self._usage_records[quota_id] = records[-self._max_history_records:]

            # Update usage history summary
            usage.usage_history = self._summarize_usage_history(records)

            # Estimate exhaustion time
            usage.estimated_exhaustion = self._estimate_exhaustion(
                usage, records, config.period
            )

        # Check thresholds (outside lock for alert handling)
        await self._check_thresholds(quota_id, config, usage)

        return usage

    def _summarize_usage_history(
        self,
        records: List[UsageRecord]
    ) -> List[Dict[str, Any]]:
        """Summarize usage history into hourly buckets."""
        if not records:
            return []

        # Group by hour
        hourly: Dict[str, float] = {}
        for record in records:
            hour_key = record.timestamp.strftime("%Y-%m-%d %H:00")
            hourly[hour_key] = hourly.get(hour_key, 0) + record.amount

        # Convert to list format
        summary = [
            {"timestamp": k, "usage": v}
            for k, v in sorted(hourly.items())[-24:]  # Last 24 hours
        ]

        return summary

    def _estimate_exhaustion(
        self,
        usage: QuotaUsage,
        records: List[UsageRecord],
        period: QuotaPeriod
    ) -> Optional[datetime]:
        """Estimate when quota will be exhausted."""
        if usage.remaining <= 0:
            return datetime.utcnow()

        if len(records) < 2:
            return None

        # Calculate average usage rate from recent records
        recent_records = [r for r in records if r.timestamp >= usage.period_start]

        if len(recent_records) < 2:
            return None

        first_record = recent_records[0]
        last_record = recent_records[-1]

        time_span = (last_record.timestamp - first_record.timestamp).total_seconds()
        if time_span <= 0:
            return None

        total_usage = sum(r.amount for r in recent_records)
        usage_rate_per_second = total_usage / time_span

        if usage_rate_per_second <= 0:
            return None

        seconds_until_exhaustion = usage.remaining / usage_rate_per_second
        estimated_time = datetime.utcnow() + timedelta(seconds=seconds_until_exhaustion)

        # Cap at period end
        if estimated_time > usage.period_end:
            return None  # Won't exhaust before reset

        return estimated_time

    async def _check_thresholds(
        self,
        quota_id: str,
        config: QuotaConfig,
        usage: QuotaUsage
    ) -> None:
        """
        Check if thresholds are exceeded and trigger alerts.

        Validates Requirements: 10.4
        """
        if not config.enabled:
            return

        alerts_to_send: List[QuotaAlert] = []

        # Check critical threshold
        if (usage.usage_percent >= config.critical_threshold_percent
                and not usage.critical_alert_triggered):

            alert = QuotaAlert(
                id=f"{quota_id}_critical_{datetime.utcnow().timestamp()}",
                config_id=config.config_id,
                tenant_id=config.tenant_id,
                quota_type=config.quota_type,
                usage_percent=usage.usage_percent,
                threshold_percent=config.critical_threshold_percent,
                is_critical=True,
                message=(
                    f"CRITICAL: {config.quota_type.value} quota at {usage.usage_percent:.1f}% "
                    f"({usage.current_usage}/{usage.limit})"
                )
            )

            usage.critical_alert_triggered = True
            usage.alert_triggered = True
            alerts_to_send.append(alert)

            logger.warning(
                f"Critical quota alert: {config.config_id} "
                f"at {usage.usage_percent:.1f}%"
            )

        # Check warning threshold
        elif (usage.usage_percent >= config.alert_threshold_percent
              and not usage.alert_triggered):

            alert = QuotaAlert(
                id=f"{quota_id}_warning_{datetime.utcnow().timestamp()}",
                config_id=config.config_id,
                tenant_id=config.tenant_id,
                quota_type=config.quota_type,
                usage_percent=usage.usage_percent,
                threshold_percent=config.alert_threshold_percent,
                is_critical=False,
                message=(
                    f"WARNING: {config.quota_type.value} quota at {usage.usage_percent:.1f}% "
                    f"({usage.current_usage}/{usage.limit})"
                )
            )

            usage.alert_triggered = True
            alerts_to_send.append(alert)

            logger.warning(
                f"Quota warning alert: {config.config_id} "
                f"at {usage.usage_percent:.1f}%"
            )

        # Store and send alerts
        for alert in alerts_to_send:
            self._alert_history.append(alert)
            await self._trigger_alert(alert)

    async def _trigger_alert(self, alert: QuotaAlert) -> None:
        """Trigger alert callbacks."""
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Quota alert callback error: {e}")

    def add_alert_callback(self, callback: Callable[[QuotaAlert], None]) -> None:
        """Add a callback for quota alerts."""
        self._alert_callbacks.append(callback)
        logger.info(f"Added quota alert callback: {callback.__name__}")

    def remove_alert_callback(self, callback: Callable[[QuotaAlert], None]) -> None:
        """Remove an alert callback."""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)

    async def get_usage(self, quota_id: str) -> Optional[QuotaUsage]:
        """Get current usage for a quota."""
        async with self._lock:
            return self._usage.get(quota_id)

    async def get_tenant_usage(self, tenant_id: str) -> List[QuotaUsage]:
        """Get all quota usage for a tenant."""
        async with self._lock:
            return [
                u for u in self._usage.values()
                if u.tenant_id == tenant_id
            ]

    async def get_config_usage(self, config_id: str) -> List[QuotaUsage]:
        """Get all quota usage for a specific config."""
        async with self._lock:
            return [
                u for u in self._usage.values()
                if u.config_id == config_id
            ]

    async def get_quota_config(self, quota_id: str) -> Optional[QuotaConfig]:
        """Get quota configuration."""
        async with self._lock:
            return self._configs.get(quota_id)

    async def update_quota_config(
        self,
        quota_id: str,
        updates: Dict[str, Any]
    ) -> Optional[QuotaConfig]:
        """Update quota configuration."""
        async with self._lock:
            if quota_id not in self._configs:
                return None

            config = self._configs[quota_id]

            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)

            config.updated_at = datetime.utcnow()

            # Update usage limit if changed
            if "limit" in updates and quota_id in self._usage:
                usage = self._usage[quota_id]
                usage.limit = updates["limit"]
                usage.usage_percent = (usage.current_usage / usage.limit) * 100
                usage.remaining = max(0, usage.limit - usage.current_usage)

            logger.info(f"Updated quota config: {quota_id}")
            return config

    async def reset_usage(self, quota_id: str) -> Optional[QuotaUsage]:
        """Manually reset usage for a quota."""
        async with self._lock:
            if quota_id not in self._configs:
                return None

            config = self._configs[quota_id]
            usage = self._usage.get(quota_id)

            if not usage:
                return None

            now = datetime.utcnow()
            period_start, period_end = self._calculate_period_boundaries(
                config.period, now
            )

            usage.current_usage = 0
            usage.usage_percent = 0
            usage.remaining = config.limit
            usage.period_start = period_start
            usage.period_end = period_end
            usage.alert_triggered = False
            usage.critical_alert_triggered = False
            usage.last_updated = now

            # Clear usage records
            self._usage_records[quota_id] = []
            usage.usage_history = []

            logger.info(f"Reset usage for quota: {quota_id}")
            return usage

    async def get_alert_history(
        self,
        tenant_id: str,
        limit: int = 100
    ) -> List[QuotaAlert]:
        """Get quota alert history for a tenant."""
        async with self._lock:
            alerts = [a for a in self._alert_history if a.tenant_id == tenant_id]
            alerts.sort(key=lambda a: a.triggered_at, reverse=True)
            return alerts[:limit]

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a quota alert."""
        async with self._lock:
            for alert in self._alert_history:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    logger.info(f"Acknowledged quota alert: {alert_id}")
                    return True
            return False

    async def get_quota_summary(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get quota summary for a tenant.

        Validates Requirements: 10.4
        """
        async with self._lock:
            tenant_configs = [
                c for c in self._configs.values()
                if c.tenant_id == tenant_id
            ]

            tenant_usage = [
                u for u in self._usage.values()
                if u.tenant_id == tenant_id
            ]

            active_alerts = [
                a for a in self._alert_history
                if a.tenant_id == tenant_id and not a.acknowledged
            ]

            # Count by status
            healthy = sum(1 for u in tenant_usage if u.usage_percent < 80)
            warning = sum(1 for u in tenant_usage if 80 <= u.usage_percent < 95)
            critical = sum(1 for u in tenant_usage if u.usage_percent >= 95)

            # Summarize by quota type
            by_type: Dict[str, Dict[str, Any]] = {}
            for quota_type in QuotaType:
                type_usage = [u for u in tenant_usage if u.quota_type == quota_type]
                if type_usage:
                    total_limit = sum(u.limit for u in type_usage)
                    total_used = sum(u.current_usage for u in type_usage)
                    by_type[quota_type.value] = {
                        "count": len(type_usage),
                        "total_limit": total_limit,
                        "total_used": total_used,
                        "usage_percent": (total_used / total_limit * 100) if total_limit > 0 else 0
                    }

            return {
                "total_quotas": len(tenant_configs),
                "healthy": healthy,
                "warning": warning,
                "critical": critical,
                "active_alerts": len(active_alerts),
                "by_type": by_type,
                "quotas": [
                    {
                        "config_id": u.config_id,
                        "quota_type": u.quota_type.value,
                        "usage_percent": u.usage_percent,
                        "remaining": u.remaining,
                        "period_end": u.period_end.isoformat(),
                        "estimated_exhaustion": (
                            u.estimated_exhaustion.isoformat()
                            if u.estimated_exhaustion else None
                        )
                    }
                    for u in tenant_usage
                ]
            }

    async def start_monitoring(self, interval: int = 60) -> None:
        """
        Start background quota monitoring.

        Args:
            interval: Check interval in seconds

        Validates Requirements: 10.4
        """
        if self._running:
            logger.warning("Quota monitoring already running")
            return

        self._check_interval_seconds = interval
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started quota monitoring with {interval}s interval")

    async def stop_monitoring(self) -> None:
        """Stop background quota monitoring."""
        if not self._running:
            return

        self._running = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

        logger.info("Stopped quota monitoring")

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        logger.info("Quota monitoring loop started")

        while self._running:
            try:
                await self._check_all_quotas()
                await asyncio.sleep(self._check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in quota monitoring loop: {e}")
                await asyncio.sleep(self._check_interval_seconds)

        logger.info("Quota monitoring loop stopped")

    async def _check_all_quotas(self) -> None:
        """Check all quotas for period resets and threshold violations."""
        now = datetime.utcnow()

        async with self._lock:
            quotas_to_check = list(self._configs.items())

        for quota_id, config in quotas_to_check:
            try:
                usage = self._usage.get(quota_id)
                if not usage:
                    continue

                # Check for period reset
                if now >= usage.period_end:
                    async with self._lock:
                        period_start, period_end = self._calculate_period_boundaries(
                            config.period, now
                        )
                        usage.current_usage = 0
                        usage.usage_percent = 0
                        usage.remaining = config.limit
                        usage.period_start = period_start
                        usage.period_end = period_end
                        usage.alert_triggered = False
                        usage.critical_alert_triggered = False
                        usage.last_updated = now

                        # Clear old records
                        self._usage_records[quota_id] = []
                        usage.usage_history = []

                        logger.info(f"Auto-reset quota {quota_id} for new period")

                # Re-check thresholds (in case they were changed)
                if config.enabled:
                    await self._check_thresholds(quota_id, config, usage)

            except Exception as e:
                logger.error(f"Error checking quota {quota_id}: {e}")

    async def cleanup_old_alerts(self, days: int = 30) -> int:
        """Clean up old alerts."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        async with self._lock:
            old_count = len(self._alert_history)
            self._alert_history = [
                a for a in self._alert_history
                if a.triggered_at > cutoff
            ]
            cleaned = old_count - len(self._alert_history)

            logger.info(f"Cleaned up {cleaned} old quota alerts")
            return cleaned

    async def get_usage_trend(
        self,
        quota_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get usage trend for a quota over specified hours."""
        async with self._lock:
            records = self._usage_records.get(quota_id, [])

            if not records:
                return []

            cutoff = datetime.utcnow() - timedelta(hours=hours)
            recent_records = [r for r in records if r.timestamp >= cutoff]

            # Group by hour
            hourly: Dict[str, float] = {}
            for record in recent_records:
                hour_key = record.timestamp.strftime("%Y-%m-%d %H:00")
                hourly[hour_key] = hourly.get(hour_key, 0) + record.amount

            return [
                {"timestamp": k, "usage": v}
                for k, v in sorted(hourly.items())
            ]

    async def get_quota_status_for_dashboard(
        self,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get quota status formatted for dashboard display.

        Validates Requirements: 10.6
        """
        async with self._lock:
            tenant_usage = [
                u for u in self._usage.values()
                if u.tenant_id == tenant_id
            ]

            configs = {
                c.id: c for c in self._configs.values()
                if c.tenant_id == tenant_id
            }

            dashboard_items = []
            for usage in tenant_usage:
                config = configs.get(f"{usage.config_id}_{usage.quota_type.value}")

                dashboard_items.append({
                    "config_id": usage.config_id,
                    "quota_type": usage.quota_type.value,
                    "provider_name": config.provider_name if config else "",
                    "current_usage": usage.current_usage,
                    "limit": usage.limit,
                    "usage_percent": round(usage.usage_percent, 1),
                    "remaining": usage.remaining,
                    "status": (
                        "critical" if usage.usage_percent >= 95
                        else "warning" if usage.usage_percent >= 80
                        else "healthy"
                    ),
                    "period_end": usage.period_end.isoformat(),
                    "estimated_exhaustion": (
                        usage.estimated_exhaustion.isoformat()
                        if usage.estimated_exhaustion else None
                    ),
                    "last_updated": usage.last_updated.isoformat()
                })

            return {
                "tenant_id": tenant_id,
                "quotas": dashboard_items,
                "summary": {
                    "total": len(dashboard_items),
                    "healthy": sum(1 for i in dashboard_items if i["status"] == "healthy"),
                    "warning": sum(1 for i in dashboard_items if i["status"] == "warning"),
                    "critical": sum(1 for i in dashboard_items if i["status"] == "critical")
                },
                "last_updated": datetime.utcnow().isoformat()
            }
