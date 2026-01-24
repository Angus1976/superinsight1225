"""
Text-to-SQL Quality Monitoring and Alerting Service.

This module provides real-time quality monitoring and alerting for Text-to-SQL:
- Real-time quality metrics tracking
- Threshold-based alerting
- Quality trend analysis
- Prometheus metrics integration
- Quality degradation detection
- Execution correctness validation

Extends the base quality_assessment.py with monitoring capabilities.
"""

import asyncio
import logging
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of quality alerts."""
    LOW_QUALITY = "low_quality"
    QUALITY_DEGRADATION = "quality_degradation"
    HIGH_ERROR_RATE = "high_error_rate"
    EXECUTION_FAILURE = "execution_failure"
    THRESHOLD_BREACH = "threshold_breach"
    ANOMALY_DETECTED = "anomaly_detected"


class MetricType(str, Enum):
    """Quality metric types."""
    OVERALL_SCORE = "overall_score"
    SYNTAX_SCORE = "syntax_score"
    FAITHFULNESS_SCORE = "faithfulness_score"
    RELEVANCE_SCORE = "relevance_score"
    CORRECTNESS_SCORE = "correctness_score"
    EXECUTION_SCORE = "execution_score"
    ERROR_RATE = "error_rate"
    LATENCY = "latency"


# Default thresholds
DEFAULT_QUALITY_THRESHOLD = 0.75
DEFAULT_ERROR_RATE_THRESHOLD = 0.15
DEFAULT_DEGRADATION_WINDOW = 100  # Number of queries
DEFAULT_DEGRADATION_THRESHOLD = 0.10  # 10% drop


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class QualityThreshold:
    """Quality threshold configuration."""
    metric_type: MetricType
    min_value: float = 0.0
    max_value: float = 1.0
    warning_threshold: float = 0.70
    critical_threshold: float = 0.50
    enabled: bool = True


@dataclass
class QualityAlert:
    """Quality alert."""
    id: UUID = field(default_factory=uuid4)
    alert_type: AlertType = AlertType.LOW_QUALITY
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str = ""
    metric_type: Optional[MetricType] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None

    # Context
    query: Optional[str] = None
    generated_sql: Optional[str] = None
    method_used: Optional[str] = None
    database_type: Optional[str] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    correlation_id: Optional[str] = None


@dataclass
class QualityMetric:
    """Quality metric data point."""
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendAnalysis:
    """Quality trend analysis result."""
    metric_type: MetricType
    period_start: datetime
    period_end: datetime
    current_average: float
    previous_average: float
    change_percent: float
    trend_direction: str  # "improving", "stable", "degrading"
    data_points: int
    is_significant: bool = False


class ExecutionResult(BaseModel):
    """Result of SQL execution for correctness validation."""
    success: bool
    row_count: Optional[int] = None
    columns: List[str] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None
    error: Optional[str] = None
    result_hash: Optional[str] = None


class CorrectnessAssessment(BaseModel):
    """Assessment of SQL correctness through execution."""
    execution_successful: bool
    result_matches_expected: Optional[bool] = None
    row_count_match: Optional[bool] = None
    schema_match: Optional[bool] = None
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    details: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Quality Monitoring Service
# =============================================================================

class QualityMonitoringService:
    """
    Real-time quality monitoring and alerting service.

    Features:
    - Continuous quality metrics tracking
    - Threshold-based alerting
    - Trend analysis and anomaly detection
    - Execution correctness validation
    - Prometheus metrics integration
    """

    def __init__(
        self,
        alert_callback: Optional[Callable[[QualityAlert], None]] = None,
        enable_prometheus: bool = False,
    ):
        """
        Initialize quality monitoring service.

        Args:
            alert_callback: Optional callback for alert notifications
            enable_prometheus: Enable Prometheus metrics
        """
        self._alert_callback = alert_callback
        self._enable_prometheus = enable_prometheus
        self._lock = asyncio.Lock()

        # Thresholds
        self._thresholds: Dict[MetricType, QualityThreshold] = {
            MetricType.OVERALL_SCORE: QualityThreshold(
                metric_type=MetricType.OVERALL_SCORE,
                warning_threshold=0.70,
                critical_threshold=0.50,
            ),
            MetricType.SYNTAX_SCORE: QualityThreshold(
                metric_type=MetricType.SYNTAX_SCORE,
                warning_threshold=0.90,
                critical_threshold=0.70,
            ),
            MetricType.EXECUTION_SCORE: QualityThreshold(
                metric_type=MetricType.EXECUTION_SCORE,
                warning_threshold=0.80,
                critical_threshold=0.60,
            ),
            MetricType.ERROR_RATE: QualityThreshold(
                metric_type=MetricType.ERROR_RATE,
                warning_threshold=0.10,
                critical_threshold=0.20,
                min_value=0.0,
                max_value=1.0,
            ),
        }

        # Metrics storage (time-series data)
        self._metrics: Dict[MetricType, Deque[QualityMetric]] = defaultdict(
            lambda: deque(maxlen=1000)
        )

        # Alerts
        self._alerts: Deque[QualityAlert] = deque(maxlen=500)
        self._active_alerts: Set[UUID] = set()

        # Statistics
        self._stats = {
            "total_assessments": 0,
            "total_alerts": 0,
            "alerts_by_type": defaultdict(int),
            "alerts_by_severity": defaultdict(int),
        }

        logger.info("QualityMonitoringService initialized")

    # =========================================================================
    # Metric Recording
    # =========================================================================

    async def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a quality metric.

        Args:
            metric_type: Type of metric
            value: Metric value
            metadata: Optional metadata
        """
        metric = QualityMetric(
            metric_type=metric_type,
            value=value,
            metadata=metadata or {},
        )

        async with self._lock:
            self._metrics[metric_type].append(metric)
            self._stats["total_assessments"] += 1

            # Check thresholds
            await self._check_thresholds(metric)

            # Update Prometheus if enabled
            if self._enable_prometheus:
                await self._update_prometheus_metrics(metric)

    async def record_assessment_metrics(
        self,
        overall_score: float,
        syntax_score: Optional[float] = None,
        faithfulness_score: Optional[float] = None,
        relevance_score: Optional[float] = None,
        correctness_score: Optional[float] = None,
        execution_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record multiple metrics from a quality assessment.

        Args:
            overall_score: Overall quality score
            syntax_score: Syntax score
            faithfulness_score: Faithfulness score
            relevance_score: Relevance score
            correctness_score: Correctness score
            execution_score: Execution score
            metadata: Optional metadata
        """
        await self.record_metric(MetricType.OVERALL_SCORE, overall_score, metadata)

        if syntax_score is not None:
            await self.record_metric(MetricType.SYNTAX_SCORE, syntax_score, metadata)

        if faithfulness_score is not None:
            await self.record_metric(MetricType.FAITHFULNESS_SCORE, faithfulness_score, metadata)

        if relevance_score is not None:
            await self.record_metric(MetricType.RELEVANCE_SCORE, relevance_score, metadata)

        if correctness_score is not None:
            await self.record_metric(MetricType.CORRECTNESS_SCORE, correctness_score, metadata)

        if execution_score is not None:
            await self.record_metric(MetricType.EXECUTION_SCORE, execution_score, metadata)

    # =========================================================================
    # Threshold Checking and Alerting
    # =========================================================================

    async def _check_thresholds(self, metric: QualityMetric) -> None:
        """Check if metric breaches thresholds and generate alerts."""
        threshold = self._thresholds.get(metric.metric_type)
        if not threshold or not threshold.enabled:
            return

        severity = None
        threshold_value = None

        # Check critical threshold
        if metric.value <= threshold.critical_threshold:
            severity = AlertSeverity.CRITICAL
            threshold_value = threshold.critical_threshold
        # Check warning threshold
        elif metric.value <= threshold.warning_threshold:
            severity = AlertSeverity.WARNING
            threshold_value = threshold.warning_threshold

        if severity:
            await self._create_alert(
                alert_type=AlertType.THRESHOLD_BREACH,
                severity=severity,
                message=f"{metric.metric_type.value} below {severity.value} threshold: {metric.value:.3f} <= {threshold_value:.3f}",
                metric_type=metric.metric_type,
                current_value=metric.value,
                threshold_value=threshold_value,
                metadata=metric.metadata,
            )

    async def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        metric_type: Optional[MetricType] = None,
        current_value: Optional[float] = None,
        threshold_value: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QualityAlert:
        """Create and notify alert."""
        metadata = metadata or {}

        alert = QualityAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            metric_type=metric_type,
            current_value=current_value,
            threshold_value=threshold_value,
            query=metadata.get("query"),
            generated_sql=metadata.get("generated_sql"),
            method_used=metadata.get("method_used"),
            database_type=metadata.get("database_type"),
            correlation_id=metadata.get("correlation_id"),
        )

        async with self._lock:
            self._alerts.append(alert)
            self._active_alerts.add(alert.id)
            self._stats["total_alerts"] += 1
            self._stats["alerts_by_type"][alert_type.value] += 1
            self._stats["alerts_by_severity"][severity.value] += 1

        # Notify callback
        if self._alert_callback:
            try:
                await asyncio.create_task(
                    asyncio.to_thread(self._alert_callback, alert)
                )
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        logger.warning(
            f"Quality alert created: {alert_type.value} ({severity.value}) - {message}"
        )

        return alert

    async def resolve_alert(self, alert_id: UUID) -> bool:
        """Resolve an active alert."""
        async with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = datetime.utcnow()
                    self._active_alerts.discard(alert_id)
                    return True
        return False

    async def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        alert_type: Optional[AlertType] = None,
    ) -> List[QualityAlert]:
        """Get active alerts with optional filtering."""
        alerts = [
            alert for alert in self._alerts
            if alert.id in self._active_alerts
        ]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]

        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)

    # =========================================================================
    # Trend Analysis
    # =========================================================================

    async def analyze_trend(
        self,
        metric_type: MetricType,
        period_minutes: int = 60,
        comparison_period_minutes: int = 60,
    ) -> TrendAnalysis:
        """
        Analyze quality trend for a metric.

        Args:
            metric_type: Metric to analyze
            period_minutes: Current period length
            comparison_period_minutes: Comparison period length

        Returns:
            Trend analysis result
        """
        now = datetime.utcnow()
        current_start = now - timedelta(minutes=period_minutes)
        previous_start = current_start - timedelta(minutes=comparison_period_minutes)
        previous_end = current_start

        metrics = self._metrics.get(metric_type, deque())

        # Filter metrics for current period
        current_metrics = [
            m for m in metrics
            if current_start <= m.timestamp <= now
        ]

        # Filter metrics for comparison period
        previous_metrics = [
            m for m in metrics
            if previous_start <= m.timestamp < previous_end
        ]

        # Calculate averages
        current_avg = (
            sum(m.value for m in current_metrics) / len(current_metrics)
            if current_metrics else 0.0
        )
        previous_avg = (
            sum(m.value for m in previous_metrics) / len(previous_metrics)
            if previous_metrics else 0.0
        )

        # Calculate change
        if previous_avg > 0:
            change_percent = ((current_avg - previous_avg) / previous_avg) * 100
        else:
            change_percent = 0.0

        # Determine trend direction
        if abs(change_percent) < 2.0:  # Less than 2% change
            trend_direction = "stable"
        elif change_percent > 0:
            trend_direction = "improving"
        else:
            trend_direction = "degrading"

        # Check if degradation is significant
        is_significant = (
            trend_direction == "degrading" and
            abs(change_percent) >= 10.0  # 10% degradation
        )

        analysis = TrendAnalysis(
            metric_type=metric_type,
            period_start=current_start,
            period_end=now,
            current_average=current_avg,
            previous_average=previous_avg,
            change_percent=change_percent,
            trend_direction=trend_direction,
            data_points=len(current_metrics),
            is_significant=is_significant,
        )

        # Generate alert for significant degradation
        if is_significant:
            await self._create_alert(
                alert_type=AlertType.QUALITY_DEGRADATION,
                severity=AlertSeverity.WARNING,
                message=f"{metric_type.value} degraded by {abs(change_percent):.1f}%: {current_avg:.3f} (was {previous_avg:.3f})",
                metric_type=metric_type,
                current_value=current_avg,
                threshold_value=previous_avg,
            )

        return analysis

    async def detect_anomalies(
        self,
        metric_type: MetricType,
        window_size: int = 100,
        std_threshold: float = 2.0,
    ) -> List[QualityMetric]:
        """
        Detect anomalies in quality metrics using statistical analysis.

        Args:
            metric_type: Metric type to analyze
            window_size: Number of recent metrics to analyze
            std_threshold: Standard deviation threshold for anomaly

        Returns:
            List of anomalous metrics
        """
        metrics_list = list(self._metrics.get(metric_type, deque()))

        if len(metrics_list) < window_size:
            return []

        # Get recent window
        recent_metrics = metrics_list[-window_size:]
        values = [m.value for m in recent_metrics]

        # Calculate statistics
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5

        # Detect anomalies
        anomalies = []
        for metric in recent_metrics[-10:]:  # Check last 10
            z_score = abs((metric.value - mean) / std_dev) if std_dev > 0 else 0
            if z_score > std_threshold:
                anomalies.append(metric)

        # Generate alerts for anomalies
        if anomalies:
            await self._create_alert(
                alert_type=AlertType.ANOMALY_DETECTED,
                severity=AlertSeverity.INFO,
                message=f"Detected {len(anomalies)} anomalies in {metric_type.value}",
                metric_type=metric_type,
            )

        return anomalies

    # =========================================================================
    # Execution Correctness Validation
    # =========================================================================

    async def validate_execution(
        self,
        generated_sql: str,
        expected_sql: Optional[str] = None,
        database_executor: Optional[Callable] = None,
        schema_context: Optional[str] = None,
    ) -> CorrectnessAssessment:
        """
        Validate SQL correctness through execution.

        Args:
            generated_sql: Generated SQL to validate
            expected_sql: Optional expected SQL for comparison
            database_executor: Function to execute SQL
            schema_context: Optional schema context

        Returns:
            Correctness assessment
        """
        assessment = CorrectnessAssessment(
            execution_successful=False,
        )

        if not database_executor:
            logger.warning("No database executor provided for execution validation")
            return assessment

        # Execute generated SQL
        try:
            generated_result = await database_executor(generated_sql)
            assessment.execution_successful = generated_result.success

            if not generated_result.success:
                assessment.score = 0.0
                assessment.details["error"] = generated_result.error
                return assessment

            # Base score for successful execution
            assessment.score = 0.5

            # If expected SQL provided, compare results
            if expected_sql:
                try:
                    expected_result = await database_executor(expected_sql)

                    if expected_result.success:
                        # Compare row counts
                        if (generated_result.row_count is not None and
                            expected_result.row_count is not None):
                            row_match = generated_result.row_count == expected_result.row_count
                            assessment.row_count_match = row_match
                            if row_match:
                                assessment.score += 0.25

                        # Compare schemas
                        if generated_result.columns and expected_result.columns:
                            schema_match = generated_result.columns == expected_result.columns
                            assessment.schema_match = schema_match
                            if schema_match:
                                assessment.score += 0.15

                        # Compare result hashes
                        if (generated_result.result_hash and
                            expected_result.result_hash):
                            result_match = generated_result.result_hash == expected_result.result_hash
                            assessment.result_matches_expected = result_match
                            if result_match:
                                assessment.score = 1.0  # Perfect match

                except Exception as e:
                    logger.error(f"Expected SQL execution error: {e}")
                    assessment.details["expected_sql_error"] = str(e)

        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            assessment.execution_successful = False
            assessment.score = 0.0
            assessment.details["execution_error"] = str(e)

        return assessment

    # =========================================================================
    # Metrics and Reporting
    # =========================================================================

    async def get_metrics_summary(
        self,
        period_minutes: int = 60,
    ) -> Dict[str, Any]:
        """
        Get summary of quality metrics.

        Args:
            period_minutes: Period to summarize

        Returns:
            Metrics summary
        """
        cutoff = datetime.utcnow() - timedelta(minutes=period_minutes)

        summary = {
            "period_minutes": period_minutes,
            "generated_at": datetime.utcnow().isoformat(),
            "metrics": {},
        }

        for metric_type, metrics_deque in self._metrics.items():
            recent = [m for m in metrics_deque if m.timestamp >= cutoff]

            if recent:
                values = [m.value for m in recent]
                summary["metrics"][metric_type.value] = {
                    "count": len(values),
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "latest": values[-1],
                }

        return summary

    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alerts."""
        return {
            "total_alerts": self._stats["total_alerts"],
            "active_alerts": len(self._active_alerts),
            "by_type": dict(self._stats["alerts_by_type"]),
            "by_severity": dict(self._stats["alerts_by_severity"]),
        }

    async def _update_prometheus_metrics(self, metric: QualityMetric) -> None:
        """Update Prometheus metrics (placeholder)."""
        # In production, integrate with actual Prometheus client
        # Example:
        # quality_score_gauge.labels(
        #     metric_type=metric.metric_type.value
        # ).set(metric.value)
        pass

    # =========================================================================
    # Configuration
    # =========================================================================

    async def set_threshold(
        self,
        metric_type: MetricType,
        warning_threshold: Optional[float] = None,
        critical_threshold: Optional[float] = None,
    ) -> None:
        """Update threshold configuration."""
        async with self._lock:
            if metric_type in self._thresholds:
                threshold = self._thresholds[metric_type]
                if warning_threshold is not None:
                    threshold.warning_threshold = warning_threshold
                if critical_threshold is not None:
                    threshold.critical_threshold = critical_threshold

    async def get_threshold(self, metric_type: MetricType) -> Optional[QualityThreshold]:
        """Get threshold configuration."""
        return self._thresholds.get(metric_type)


# =============================================================================
# Global Instance
# =============================================================================

_quality_monitoring_service: Optional[QualityMonitoringService] = None
_monitoring_lock = asyncio.Lock()


async def get_quality_monitoring_service(
    alert_callback: Optional[Callable[[QualityAlert], None]] = None,
    enable_prometheus: bool = False,
) -> QualityMonitoringService:
    """
    Get or create the global quality monitoring service.

    Args:
        alert_callback: Optional callback for alerts
        enable_prometheus: Enable Prometheus metrics

    Returns:
        Quality monitoring service instance
    """
    global _quality_monitoring_service

    async with _monitoring_lock:
        if _quality_monitoring_service is None:
            _quality_monitoring_service = QualityMonitoringService(
                alert_callback=alert_callback,
                enable_prometheus=enable_prometheus,
            )
        return _quality_monitoring_service


async def reset_quality_monitoring_service():
    """Reset the global quality monitoring service (for testing)."""
    global _quality_monitoring_service

    async with _monitoring_lock:
        _quality_monitoring_service = None
