"""
Quality Anomaly Detector for SuperInsight Platform.

Provides comprehensive anomaly detection for quality issues:
- Statistical anomaly detection
- Pattern-based detection
- ML-assisted detection
- Rule-based detection
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics
import math

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    """Types of quality anomalies."""
    STATISTICAL = "statistical"
    PATTERN = "pattern"
    THRESHOLD = "threshold"
    TREND = "trend"
    DISTRIBUTION = "distribution"
    TEMPORAL = "temporal"


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyStatus(str, Enum):
    """Status of detected anomalies."""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"


@dataclass
class QualityAnomaly:
    """Represents a detected quality anomaly."""
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    status: AnomalyStatus
    description: str
    affected_entity: str  # task_id, annotator_id, project_id
    entity_type: str  # task, annotator, project
    metric_name: str
    metric_value: float
    expected_range: Tuple[float, float]
    confidence: float
    detection_method: str
    context: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_id": self.anomaly_id,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "description": self.description,
            "affected_entity": self.affected_entity,
            "entity_type": self.entity_type,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "expected_range": list(self.expected_range),
            "confidence": self.confidence,
            "detection_method": self.detection_method,
            "context": self.context,
            "recommendations": self.recommendations,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class DetectionRule:
    """Rule for anomaly detection."""
    rule_id: str
    name: str
    description: str
    metric_name: str
    condition: str  # gt, lt, eq, range, std_dev
    threshold: float
    secondary_threshold: Optional[float] = None
    severity: AnomalySeverity = AnomalySeverity.MEDIUM
    enabled: bool = True
    cooldown_minutes: int = 60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "metric_name": self.metric_name,
            "condition": self.condition,
            "threshold": self.threshold,
            "secondary_threshold": self.secondary_threshold,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "cooldown_minutes": self.cooldown_minutes
        }


class StatisticalDetector:
    """Statistical anomaly detection methods."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.data_windows: Dict[str, List[float]] = defaultdict(list)

    def add_value(self, metric_name: str, value: float):
        """Add a value to the data window."""
        self.data_windows[metric_name].append(value)
        if len(self.data_windows[metric_name]) > self.window_size:
            self.data_windows[metric_name] = self.data_windows[metric_name][-self.window_size:]

    def detect_zscore_anomaly(
        self,
        metric_name: str,
        value: float,
        threshold: float = 3.0
    ) -> Optional[Tuple[bool, float, Tuple[float, float]]]:
        """
        Detect anomaly using Z-score method.
        
        Returns:
            Tuple of (is_anomaly, z_score, expected_range) or None
        """
        data = self.data_windows.get(metric_name, [])
        if len(data) < 10:
            return None

        mean = statistics.mean(data)
        std = statistics.stdev(data) if len(data) > 1 else 0

        if std == 0:
            return None

        z_score = abs(value - mean) / std
        is_anomaly = z_score > threshold
        expected_range = (mean - threshold * std, mean + threshold * std)

        return (is_anomaly, z_score, expected_range)

    def detect_iqr_anomaly(
        self,
        metric_name: str,
        value: float,
        multiplier: float = 1.5
    ) -> Optional[Tuple[bool, float, Tuple[float, float]]]:
        """
        Detect anomaly using IQR method.
        
        Returns:
            Tuple of (is_anomaly, deviation, expected_range) or None
        """
        data = self.data_windows.get(metric_name, [])
        if len(data) < 10:
            return None

        sorted_data = sorted(data)
        n = len(sorted_data)
        q1 = sorted_data[n // 4]
        q3 = sorted_data[3 * n // 4]
        iqr = q3 - q1

        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        is_anomaly = value < lower_bound or value > upper_bound
        deviation = max(lower_bound - value, value - upper_bound, 0)

        return (is_anomaly, deviation, (lower_bound, upper_bound))

    def detect_moving_average_anomaly(
        self,
        metric_name: str,
        value: float,
        window: int = 10,
        threshold: float = 0.3
    ) -> Optional[Tuple[bool, float, Tuple[float, float]]]:
        """
        Detect anomaly using moving average deviation.
        
        Returns:
            Tuple of (is_anomaly, deviation_percent, expected_range) or None
        """
        data = self.data_windows.get(metric_name, [])
        if len(data) < window:
            return None

        recent = data[-window:]
        ma = statistics.mean(recent)

        if ma == 0:
            return None

        deviation_percent = abs(value - ma) / ma
        is_anomaly = deviation_percent > threshold
        expected_range = (ma * (1 - threshold), ma * (1 + threshold))

        return (is_anomaly, deviation_percent, expected_range)


class QualityAnomalyDetector:
    """
    Comprehensive quality anomaly detector.
    
    Combines multiple detection methods for robust anomaly detection.
    """

    def __init__(self):
        self.statistical_detector = StatisticalDetector()
        self.detection_rules: Dict[str, DetectionRule] = {}
        self.detected_anomalies: Dict[str, QualityAnomaly] = {}
        self.anomaly_history: List[QualityAnomaly] = []
        self.rule_last_triggered: Dict[str, datetime] = {}
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default detection rules."""
        default_rules = [
            DetectionRule(
                rule_id="low_accuracy",
                name="低准确率检测",
                description="检测标注准确率异常下降",
                metric_name="accuracy",
                condition="lt",
                threshold=0.8,
                severity=AnomalySeverity.HIGH
            ),
            DetectionRule(
                rule_id="low_agreement",
                name="低一致性检测",
                description="检测标注员一致性异常下降",
                metric_name="agreement",
                condition="lt",
                threshold=0.7,
                severity=AnomalySeverity.MEDIUM
            ),
            DetectionRule(
                rule_id="high_rejection_rate",
                name="高拒绝率检测",
                description="检测任务拒绝率异常升高",
                metric_name="rejection_rate",
                condition="gt",
                threshold=0.2,
                severity=AnomalySeverity.HIGH
            ),
            DetectionRule(
                rule_id="slow_completion",
                name="慢完成检测",
                description="检测任务完成时间异常延长",
                metric_name="completion_time",
                condition="gt",
                threshold=300,  # seconds
                severity=AnomalySeverity.LOW
            ),
            DetectionRule(
                rule_id="confidence_drop",
                name="置信度下降检测",
                description="检测标注置信度异常下降",
                metric_name="confidence",
                condition="lt",
                threshold=0.6,
                severity=AnomalySeverity.MEDIUM
            ),
            DetectionRule(
                rule_id="std_dev_anomaly",
                name="统计异常检测",
                description="检测超出3个标准差的异常值",
                metric_name="*",  # Applies to all metrics
                condition="std_dev",
                threshold=3.0,
                severity=AnomalySeverity.MEDIUM
            )
        ]

        for rule in default_rules:
            self.detection_rules[rule.rule_id] = rule

    def add_rule(self, rule: DetectionRule):
        """Add a detection rule."""
        self.detection_rules[rule.rule_id] = rule
        logger.info(f"Added detection rule: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a detection rule."""
        if rule_id in self.detection_rules:
            del self.detection_rules[rule_id]
            return True
        return False

    def detect_anomalies(
        self,
        entity_id: str,
        entity_type: str,
        metrics: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> List[QualityAnomaly]:
        """
        Detect anomalies in provided metrics.
        
        Args:
            entity_id: ID of the entity (task, annotator, project)
            entity_type: Type of entity
            metrics: Dictionary of metric_name -> value
            context: Additional context information
            
        Returns:
            List of detected anomalies
        """
        detected = []

        for metric_name, value in metrics.items():
            # Add to statistical detector
            self.statistical_detector.add_value(metric_name, value)

            # Check rule-based detection
            rule_anomalies = self._check_rules(
                entity_id, entity_type, metric_name, value, context
            )
            detected.extend(rule_anomalies)

            # Check statistical detection
            stat_anomalies = self._check_statistical(
                entity_id, entity_type, metric_name, value, context
            )
            detected.extend(stat_anomalies)

        # Store detected anomalies
        for anomaly in detected:
            self.detected_anomalies[anomaly.anomaly_id] = anomaly
            self.anomaly_history.append(anomaly)

        # Trim history
        if len(self.anomaly_history) > 10000:
            self.anomaly_history = self.anomaly_history[-10000:]

        return detected

    def _check_rules(
        self,
        entity_id: str,
        entity_type: str,
        metric_name: str,
        value: float,
        context: Optional[Dict[str, Any]]
    ) -> List[QualityAnomaly]:
        """Check rule-based detection."""
        anomalies = []

        for rule in self.detection_rules.values():
            if not rule.enabled:
                continue

            # Check if rule applies to this metric
            if rule.metric_name != "*" and rule.metric_name != metric_name:
                continue

            # Check cooldown
            last_triggered = self.rule_last_triggered.get(rule.rule_id)
            if last_triggered:
                cooldown = timedelta(minutes=rule.cooldown_minutes)
                if datetime.now() - last_triggered < cooldown:
                    continue

            # Evaluate condition
            is_anomaly = False
            expected_range = (0.0, 1.0)

            if rule.condition == "lt":
                is_anomaly = value < rule.threshold
                expected_range = (rule.threshold, float('inf'))
            elif rule.condition == "gt":
                is_anomaly = value > rule.threshold
                expected_range = (float('-inf'), rule.threshold)
            elif rule.condition == "eq":
                is_anomaly = abs(value - rule.threshold) < 0.001
                expected_range = (rule.threshold, rule.threshold)
            elif rule.condition == "range":
                if rule.secondary_threshold:
                    is_anomaly = value < rule.threshold or value > rule.secondary_threshold
                    expected_range = (rule.threshold, rule.secondary_threshold)
            elif rule.condition == "std_dev":
                result = self.statistical_detector.detect_zscore_anomaly(
                    metric_name, value, rule.threshold
                )
                if result:
                    is_anomaly, _, expected_range = result

            if is_anomaly:
                import uuid
                anomaly = QualityAnomaly(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.THRESHOLD,
                    severity=rule.severity,
                    status=AnomalyStatus.DETECTED,
                    description=f"{rule.name}: {metric_name}={value:.3f}",
                    affected_entity=entity_id,
                    entity_type=entity_type,
                    metric_name=metric_name,
                    metric_value=value,
                    expected_range=expected_range,
                    confidence=0.9,
                    detection_method=f"rule:{rule.rule_id}",
                    context=context or {},
                    recommendations=self._generate_recommendations(rule, metric_name, value)
                )
                anomalies.append(anomaly)
                self.rule_last_triggered[rule.rule_id] = datetime.now()

        return anomalies

    def _check_statistical(
        self,
        entity_id: str,
        entity_type: str,
        metric_name: str,
        value: float,
        context: Optional[Dict[str, Any]]
    ) -> List[QualityAnomaly]:
        """Check statistical anomaly detection."""
        anomalies = []

        # Z-score detection
        zscore_result = self.statistical_detector.detect_zscore_anomaly(
            metric_name, value
        )
        if zscore_result and zscore_result[0]:
            is_anomaly, z_score, expected_range = zscore_result
            import uuid
            anomaly = QualityAnomaly(
                anomaly_id=str(uuid.uuid4()),
                anomaly_type=AnomalyType.STATISTICAL,
                severity=self._severity_from_zscore(z_score),
                status=AnomalyStatus.DETECTED,
                description=f"统计异常: {metric_name}={value:.3f} (z-score={z_score:.2f})",
                affected_entity=entity_id,
                entity_type=entity_type,
                metric_name=metric_name,
                metric_value=value,
                expected_range=expected_range,
                confidence=min(0.99, 0.5 + z_score * 0.1),
                detection_method="statistical:zscore",
                context=context or {},
                recommendations=["检查数据质量", "分析异常原因"]
            )
            anomalies.append(anomaly)

        # IQR detection
        iqr_result = self.statistical_detector.detect_iqr_anomaly(
            metric_name, value
        )
        if iqr_result and iqr_result[0]:
            is_anomaly, deviation, expected_range = iqr_result
            # Only add if not already detected by z-score
            if not any(a.detection_method == "statistical:zscore" for a in anomalies):
                import uuid
                anomaly = QualityAnomaly(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.STATISTICAL,
                    severity=AnomalySeverity.MEDIUM,
                    status=AnomalyStatus.DETECTED,
                    description=f"IQR异常: {metric_name}={value:.3f}",
                    affected_entity=entity_id,
                    entity_type=entity_type,
                    metric_name=metric_name,
                    metric_value=value,
                    expected_range=expected_range,
                    confidence=0.8,
                    detection_method="statistical:iqr",
                    context=context or {},
                    recommendations=["验证数据有效性"]
                )
                anomalies.append(anomaly)

        return anomalies

    def _severity_from_zscore(self, z_score: float) -> AnomalySeverity:
        """Determine severity from z-score."""
        if z_score > 4:
            return AnomalySeverity.CRITICAL
        elif z_score > 3.5:
            return AnomalySeverity.HIGH
        elif z_score > 3:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW

    def _generate_recommendations(
        self,
        rule: DetectionRule,
        metric_name: str,
        value: float
    ) -> List[str]:
        """Generate recommendations for detected anomaly."""
        recommendations = []

        if "accuracy" in metric_name.lower():
            recommendations.append("审查相关标注任务")
            recommendations.append("检查标注指南是否清晰")
        elif "agreement" in metric_name.lower():
            recommendations.append("组织标注员校准会议")
            recommendations.append("更新标注指南")
        elif "rejection" in metric_name.lower():
            recommendations.append("分析拒绝原因")
            recommendations.append("检查数据质量")
        elif "time" in metric_name.lower():
            recommendations.append("检查任务复杂度")
            recommendations.append("评估标注员工作负载")
        else:
            recommendations.append("分析异常原因")
            recommendations.append("检查相关数据")

        return recommendations

    def update_anomaly_status(
        self,
        anomaly_id: str,
        status: AnomalyStatus,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """Update anomaly status."""
        anomaly = self.detected_anomalies.get(anomaly_id)
        if not anomaly:
            return False

        anomaly.status = status
        if status == AnomalyStatus.RESOLVED:
            anomaly.resolved_at = datetime.now()
        if resolution_notes:
            anomaly.context["resolution_notes"] = resolution_notes

        return True

    def get_active_anomalies(
        self,
        entity_type: Optional[str] = None,
        severity: Optional[AnomalySeverity] = None
    ) -> List[QualityAnomaly]:
        """Get active (unresolved) anomalies."""
        active = [
            a for a in self.detected_anomalies.values()
            if a.status not in [AnomalyStatus.RESOLVED, AnomalyStatus.FALSE_POSITIVE]
        ]

        if entity_type:
            active = [a for a in active if a.entity_type == entity_type]
        if severity:
            active = [a for a in active if a.severity == severity]

        return sorted(active, key=lambda a: a.detected_at, reverse=True)

    def get_anomaly_statistics(
        self,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get anomaly statistics for a period."""
        cutoff = datetime.now() - timedelta(days=period_days)
        recent = [a for a in self.anomaly_history if a.detected_at >= cutoff]

        if not recent:
            return {
                "period_days": period_days,
                "total_anomalies": 0
            }

        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        by_status = defaultdict(int)

        for a in recent:
            by_type[a.anomaly_type.value] += 1
            by_severity[a.severity.value] += 1
            by_status[a.status.value] += 1

        return {
            "period_days": period_days,
            "total_anomalies": len(recent),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "by_status": dict(by_status),
            "detection_rate": len(recent) / period_days
        }


# Global instance
quality_anomaly_detector = QualityAnomalyDetector()
