"""
Comprehensive Sync Monitor Module.

Extends existing sync monitoring with full-pipeline monitoring capabilities:
- End-to-end sync tracking
- Performance analytics
- Health monitoring
- Alert management
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import threading

from src.sync.monitoring.sync_metrics import sync_metrics, SyncMetrics

logger = logging.getLogger(__name__)


class SyncJobStatus(str, Enum):
    """Status of a sync job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class SyncJobMetrics:
    """Metrics for a single sync job."""
    job_id: str
    source_id: str
    target_id: str
    status: SyncJobStatus = SyncJobStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_processed: int = 0
    records_succeeded: int = 0
    records_failed: int = 0
    bytes_transferred: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        if not self.started_at:
            return 0.0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        if self.records_processed == 0:
            return 1.0
        return self.records_succeeded / self.records_processed

    @property
    def throughput(self) -> float:
        """Records per second."""
        if self.duration_seconds == 0:
            return 0.0
        return self.records_processed / self.duration_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "records_processed": self.records_processed,
            "records_succeeded": self.records_succeeded,
            "records_failed": self.records_failed,
            "bytes_transferred": self.bytes_transferred,
            "duration_seconds": self.duration_seconds,
            "success_rate": self.success_rate,
            "throughput": self.throughput,
            "errors": self.errors[-10:],  # Last 10 errors
            "warnings": self.warnings[-10:],
            "checkpoints": self.checkpoints[-5:]
        }


@dataclass
class SyncAlert:
    """Represents a sync system alert."""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    job_id: Optional[str] = None
    source_id: Optional[str] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "job_id": self.job_id,
            "source_id": self.source_id,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by
        }


class PerformanceTracker:
    """Tracks sync performance metrics over time."""

    def __init__(self, window_size: int = 1000):
        self._lock = threading.Lock()
        self.window_size = window_size
        self.latency_samples: List[float] = []
        self.throughput_samples: List[Tuple[float, float]] = []  # (timestamp, value)
        self.error_timestamps: List[float] = []

    def record_latency(self, latency_ms: float):
        """Record a latency sample."""
        with self._lock:
            self.latency_samples.append(latency_ms)
            if len(self.latency_samples) > self.window_size:
                self.latency_samples = self.latency_samples[-self.window_size:]

    def record_throughput(self, records_per_second: float):
        """Record a throughput sample."""
        with self._lock:
            self.throughput_samples.append((time.time(), records_per_second))
            if len(self.throughput_samples) > self.window_size:
                self.throughput_samples = self.throughput_samples[-self.window_size:]

    def record_error(self):
        """Record an error occurrence."""
        with self._lock:
            self.error_timestamps.append(time.time())
            # Keep only last hour of errors
            cutoff = time.time() - 3600
            self.error_timestamps = [t for t in self.error_timestamps if t > cutoff]

    def get_latency_stats(self) -> Dict[str, float]:
        """Get latency statistics."""
        with self._lock:
            if not self.latency_samples:
                return {"avg": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}
            
            sorted_samples = sorted(self.latency_samples)
            n = len(sorted_samples)
            
            return {
                "avg": sum(sorted_samples) / n,
                "min": sorted_samples[0],
                "max": sorted_samples[-1],
                "p50": sorted_samples[int(n * 0.5)],
                "p95": sorted_samples[int(n * 0.95)],
                "p99": sorted_samples[int(n * 0.99)]
            }

    def get_throughput_stats(self, window_seconds: int = 60) -> Dict[str, float]:
        """Get throughput statistics for a time window."""
        with self._lock:
            cutoff = time.time() - window_seconds
            recent = [v for t, v in self.throughput_samples if t > cutoff]
            
            if not recent:
                return {"avg": 0, "min": 0, "max": 0, "current": 0}
            
            return {
                "avg": sum(recent) / len(recent),
                "min": min(recent),
                "max": max(recent),
                "current": recent[-1] if recent else 0
            }

    def get_error_rate(self, window_seconds: int = 300) -> float:
        """Get error rate (errors per minute) for a time window."""
        with self._lock:
            cutoff = time.time() - window_seconds
            recent_errors = len([t for t in self.error_timestamps if t > cutoff])
            return (recent_errors / window_seconds) * 60


class ComprehensiveSyncMonitor:
    """
    Comprehensive monitoring for the entire sync pipeline.
    
    Extends base sync monitoring with:
    - Job-level tracking
    - Performance analytics
    - Health checks
    - Alert management
    """

    def __init__(self, metrics: Optional[SyncMetrics] = None):
        self.metrics = metrics or sync_metrics
        self._lock = threading.Lock()
        
        # Job tracking
        self.active_jobs: Dict[str, SyncJobMetrics] = {}
        self.completed_jobs: List[SyncJobMetrics] = []
        self.max_completed_jobs = 1000
        
        # Performance tracking
        self.performance = PerformanceTracker()
        
        # Alerts
        self.alerts: List[SyncAlert] = []
        self.max_alerts = 500
        self.alert_handlers: List[Callable[[SyncAlert], None]] = []
        
        # Health thresholds
        self.health_thresholds = {
            "max_latency_ms": 5000,
            "min_throughput": 10,
            "max_error_rate": 5,
            "max_queue_depth": 10000,
            "max_active_jobs": 100
        }
        
        # Register metrics alert handler
        self.metrics.add_alert_handler(self._handle_metrics_alert)

    def start_job(
        self,
        job_id: str,
        source_id: str,
        target_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SyncJobMetrics:
        """Start tracking a new sync job."""
        with self._lock:
            job = SyncJobMetrics(
                job_id=job_id,
                source_id=source_id,
                target_id=target_id,
                status=SyncJobStatus.RUNNING,
                started_at=datetime.now()
            )
            self.active_jobs[job_id] = job
            
            # Update metrics
            self.metrics.update_active_jobs(len(self.active_jobs))
            
            logger.info(f"Started sync job: {job_id} ({source_id} -> {target_id})")
            return job

    def update_job_progress(
        self,
        job_id: str,
        records_processed: int = 0,
        records_succeeded: int = 0,
        records_failed: int = 0,
        bytes_transferred: int = 0
    ):
        """Update job progress."""
        with self._lock:
            job = self.active_jobs.get(job_id)
            if not job:
                return
            
            job.records_processed += records_processed
            job.records_succeeded += records_succeeded
            job.records_failed += records_failed
            job.bytes_transferred += bytes_transferred
            
            # Record performance
            if job.duration_seconds > 0:
                self.performance.record_throughput(job.throughput)
            
            # Check for issues
            if records_failed > 0:
                self.performance.record_error()

    def add_job_checkpoint(
        self,
        job_id: str,
        checkpoint_name: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """Add a checkpoint to a job."""
        with self._lock:
            job = self.active_jobs.get(job_id)
            if not job:
                return
            
            job.checkpoints.append({
                "name": checkpoint_name,
                "timestamp": datetime.now().isoformat(),
                "data": data or {}
            })

    def add_job_error(self, job_id: str, error: str):
        """Add an error to a job."""
        with self._lock:
            job = self.active_jobs.get(job_id)
            if not job:
                return
            
            job.errors.append(f"[{datetime.now().isoformat()}] {error}")
            self.performance.record_error()

    def add_job_warning(self, job_id: str, warning: str):
        """Add a warning to a job."""
        with self._lock:
            job = self.active_jobs.get(job_id)
            if not job:
                return
            
            job.warnings.append(f"[{datetime.now().isoformat()}] {warning}")

    def complete_job(
        self,
        job_id: str,
        status: SyncJobStatus = SyncJobStatus.COMPLETED
    ) -> Optional[SyncJobMetrics]:
        """Mark a job as completed."""
        with self._lock:
            job = self.active_jobs.pop(job_id, None)
            if not job:
                return None
            
            job.status = status
            job.completed_at = datetime.now()
            
            # Record final metrics
            self.metrics.record_sync_operation(
                connector_type=job.source_id,
                operation="sync",
                records=job.records_processed,
                bytes_count=job.bytes_transferred,
                duration_seconds=job.duration_seconds,
                success=(status == SyncJobStatus.COMPLETED)
            )
            
            # Store in completed jobs
            self.completed_jobs.append(job)
            if len(self.completed_jobs) > self.max_completed_jobs:
                self.completed_jobs = self.completed_jobs[-self.max_completed_jobs:]
            
            # Update active jobs count
            self.metrics.update_active_jobs(len(self.active_jobs))
            
            logger.info(
                f"Completed sync job: {job_id} "
                f"(status={status.value}, records={job.records_processed}, "
                f"duration={job.duration_seconds:.2f}s)"
            )
            
            return job

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job."""
        with self._lock:
            job = self.active_jobs.get(job_id)
            if job:
                return job.to_dict()
            
            # Check completed jobs
            for job in reversed(self.completed_jobs):
                if job.job_id == job_id:
                    return job.to_dict()
            
            return None

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get all active jobs."""
        with self._lock:
            return [job.to_dict() for job in self.active_jobs.values()]

    def get_recent_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent completed jobs."""
        with self._lock:
            return [job.to_dict() for job in self.completed_jobs[-limit:]]

    def _handle_metrics_alert(self, alert_data: Dict[str, Any]):
        """Handle alerts from metrics system."""
        alert = SyncAlert(
            id=f"metric_{int(time.time() * 1000)}",
            severity=AlertSeverity(alert_data.get("severity", "warning")),
            title=f"Metric Alert: {alert_data.get('metric', 'unknown')}",
            message=f"Metric {alert_data.get('metric')} exceeded threshold",
            metric_name=alert_data.get("metric"),
            metric_value=alert_data.get("value"),
            threshold=alert_data.get("threshold")
        )
        self._add_alert(alert)

    def _add_alert(self, alert: SyncAlert):
        """Add an alert."""
        with self._lock:
            self.alerts.append(alert)
            if len(self.alerts) > self.max_alerts:
                self.alerts = self.alerts[-self.max_alerts:]
        
        # Notify handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def create_alert(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        job_id: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> SyncAlert:
        """Create a new alert."""
        alert = SyncAlert(
            id=f"alert_{int(time.time() * 1000)}",
            severity=severity,
            title=title,
            message=message,
            job_id=job_id,
            source_id=source_id
        )
        self._add_alert(alert)
        return alert

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert."""
        with self._lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_at = datetime.now()
                    alert.acknowledged_by = user
                    return True
            return False

    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get alerts with optional filters."""
        with self._lock:
            filtered = self.alerts
            
            if severity:
                filtered = [a for a in filtered if a.severity == severity]
            
            if acknowledged is not None:
                filtered = [a for a in filtered if a.acknowledged == acknowledged]
            
            return [a.to_dict() for a in filtered[-limit:]]

    def add_alert_handler(self, handler: Callable[[SyncAlert], None]):
        """Add an alert handler."""
        self.alert_handlers.append(handler)

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall sync system health status."""
        latency_stats = self.performance.get_latency_stats()
        throughput_stats = self.performance.get_throughput_stats()
        error_rate = self.performance.get_error_rate()
        
        # Determine health status
        issues = []
        status = "healthy"
        
        if latency_stats["p95"] > self.health_thresholds["max_latency_ms"]:
            issues.append(f"High latency: p95={latency_stats['p95']:.0f}ms")
            status = "degraded"
        
        if throughput_stats["current"] < self.health_thresholds["min_throughput"]:
            issues.append(f"Low throughput: {throughput_stats['current']:.1f} rec/s")
            status = "degraded"
        
        if error_rate > self.health_thresholds["max_error_rate"]:
            issues.append(f"High error rate: {error_rate:.1f}/min")
            status = "unhealthy"
        
        active_jobs_count = len(self.active_jobs)
        if active_jobs_count > self.health_thresholds["max_active_jobs"]:
            issues.append(f"Too many active jobs: {active_jobs_count}")
            status = "degraded"
        
        # Count unacknowledged critical alerts
        critical_alerts = len([
            a for a in self.alerts
            if a.severity == AlertSeverity.CRITICAL and not a.acknowledged
        ])
        if critical_alerts > 0:
            issues.append(f"Unacknowledged critical alerts: {critical_alerts}")
            status = "unhealthy"
        
        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "active_jobs": active_jobs_count,
            "latency": latency_stats,
            "throughput": throughput_stats,
            "error_rate": error_rate,
            "issues": issues,
            "thresholds": self.health_thresholds
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard."""
        health = self.get_health_status()
        
        return {
            "health": health,
            "active_jobs": self.get_active_jobs(),
            "recent_jobs": self.get_recent_jobs(10),
            "alerts": self.get_alerts(acknowledged=False, limit=10),
            "metrics": {
                "latency": health["latency"],
                "throughput": health["throughput"],
                "error_rate": health["error_rate"]
            },
            "summary": {
                "total_active_jobs": len(self.active_jobs),
                "total_completed_jobs": len(self.completed_jobs),
                "total_alerts": len(self.alerts),
                "unacknowledged_alerts": len([a for a in self.alerts if not a.acknowledged])
            }
        }


# Global instance
comprehensive_sync_monitor = ComprehensiveSyncMonitor()
