"""
Failure Detector for High Availability System.

Provides intelligent failure detection, pattern analysis, and early warning
capabilities for the SuperInsight platform.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of system failures."""
    SERVICE_DOWN = "service_down"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    DATABASE_FAILURE = "database_failure"
    EXTERNAL_DEPENDENCY = "external_dependency"
    CONFIGURATION_ERROR = "configuration_error"
    SECURITY_BREACH = "security_breach"
    DATA_CORRUPTION = "data_corruption"
    UNKNOWN = "unknown"


class FailureSeverity(Enum):
    """Severity levels for failures."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FailureEvent:
    """Represents a detected failure event."""
    failure_id: str
    failure_type: FailureType
    severity: FailureSeverity
    service_name: str
    description: str
    timestamp: float = field(default_factory=time.time)
    metrics: Dict[str, Any] = field(default_factory=dict)
    root_cause: Optional[str] = None
    affected_services: List[str] = field(default_factory=list)
    recovery_suggestions: List[str] = field(default_factory=list)


@dataclass
class FailureAnalysis:
    """Analysis result from failure detection."""
    has_critical_failures: bool
    failures: List[FailureEvent]
    system_health_score: float
    risk_assessment: Dict[str, float]
    recommendations: List[str]
    timestamp: float = field(default_factory=time.time)


@dataclass
class ServiceHealth:
    """Health status of a service."""
    service_name: str
    is_healthy: bool
    health_score: float
    last_check: float
    failure_count: int
    response_time_ms: float
    error_rate: float
    metrics: Dict[str, Any] = field(default_factory=dict)


class FailureDetector:
    """
    Intelligent failure detection system.
    
    Features:
    - Multi-dimensional health monitoring
    - Pattern-based failure detection
    - Predictive failure analysis
    - Root cause identification
    - Cascading failure prevention
    """
    
    def __init__(self):
        self.service_health: Dict[str, ServiceHealth] = {}
        self.failure_history: deque = deque(maxlen=1000)
        self.detection_rules: List[Dict[str, Any]] = []
        self.health_thresholds: Dict[str, float] = {
            "cpu_critical": 95.0,
            "cpu_warning": 80.0,
            "memory_critical": 95.0,
            "memory_warning": 85.0,
            "disk_critical": 95.0,
            "disk_warning": 85.0,
            "error_rate_critical": 0.1,
            "error_rate_warning": 0.05,
            "response_time_critical": 5000,
            "response_time_warning": 2000,
        }
        self.monitored_services: Set[str] = set()
        self._setup_default_rules()
        
        logger.info("FailureDetector initialized")
    
    def _setup_default_rules(self):
        """Setup default failure detection rules."""
        self.detection_rules = [
            {
                "name": "high_cpu_usage",
                "condition": lambda m: m.get("cpu_percent", 0) > self.health_thresholds["cpu_critical"],
                "failure_type": FailureType.RESOURCE_EXHAUSTION,
                "severity": FailureSeverity.CRITICAL,
                "description": "CPU usage exceeds critical threshold"
            },
            {
                "name": "high_memory_usage",
                "condition": lambda m: m.get("memory_percent", 0) > self.health_thresholds["memory_critical"],
                "failure_type": FailureType.RESOURCE_EXHAUSTION,
                "severity": FailureSeverity.CRITICAL,
                "description": "Memory usage exceeds critical threshold"
            },
            {
                "name": "high_disk_usage",
                "condition": lambda m: m.get("disk_percent", 0) > self.health_thresholds["disk_critical"],
                "failure_type": FailureType.RESOURCE_EXHAUSTION,
                "severity": FailureSeverity.HIGH,
                "description": "Disk usage exceeds critical threshold"
            },
            {
                "name": "high_error_rate",
                "condition": lambda m: m.get("error_rate", 0) > self.health_thresholds["error_rate_critical"],
                "failure_type": FailureType.SERVICE_DOWN,
                "severity": FailureSeverity.CRITICAL,
                "description": "Error rate exceeds critical threshold"
            },
            {
                "name": "slow_response",
                "condition": lambda m: m.get("response_time_ms", 0) > self.health_thresholds["response_time_critical"],
                "failure_type": FailureType.PERFORMANCE_DEGRADATION,
                "severity": FailureSeverity.HIGH,
                "description": "Response time exceeds critical threshold"
            },
            {
                "name": "service_unavailable",
                "condition": lambda m: not m.get("is_available", True),
                "failure_type": FailureType.SERVICE_DOWN,
                "severity": FailureSeverity.CRITICAL,
                "description": "Service is unavailable"
            },
            {
                "name": "database_connection_failed",
                "condition": lambda m: not m.get("db_connected", True),
                "failure_type": FailureType.DATABASE_FAILURE,
                "severity": FailureSeverity.CRITICAL,
                "description": "Database connection failed"
            },
        ]
    
    async def analyze_system_state(self) -> FailureAnalysis:
        """Analyze current system state and detect failures."""
        failures = []
        risk_assessment = {}
        recommendations = []
        
        # Collect system metrics
        system_metrics = await self._collect_system_metrics()
        
        # Check each monitored service
        for service_name in self.monitored_services:
            service_failures = await self._detect_service_failures(service_name, system_metrics)
            failures.extend(service_failures)
        
        # Check system-wide metrics
        system_failures = await self._detect_system_failures(system_metrics)
        failures.extend(system_failures)
        
        # Analyze failure patterns
        pattern_failures = await self._analyze_failure_patterns()
        failures.extend(pattern_failures)
        
        # Calculate system health score
        health_score = self._calculate_health_score(failures, system_metrics)
        
        # Assess risks
        risk_assessment = self._assess_risks(failures, system_metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(failures, risk_assessment)
        
        # Determine if there are critical failures
        has_critical = any(f.severity == FailureSeverity.CRITICAL for f in failures)
        
        # Record failures in history
        for failure in failures:
            self.failure_history.append(failure)
        
        return FailureAnalysis(
            has_critical_failures=has_critical,
            failures=failures,
            system_health_score=health_score,
            risk_assessment=risk_assessment,
            recommendations=recommendations
        )
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        metrics = {
            "timestamp": time.time(),
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0,
            "is_available": True,
            "db_connected": True,
            "error_rate": 0.0,
            "response_time_ms": 0.0,
        }
        
        try:
            import psutil
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            metrics["memory_percent"] = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/')
            metrics["disk_percent"] = (disk.used / disk.total) * 100
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")
        
        return metrics
    
    async def _detect_service_failures(
        self, 
        service_name: str, 
        system_metrics: Dict[str, Any]
    ) -> List[FailureEvent]:
        """Detect failures for a specific service."""
        failures = []
        
        service_health = self.service_health.get(service_name)
        if not service_health:
            return failures
        
        service_metrics = {
            **system_metrics,
            "is_available": service_health.is_healthy,
            "error_rate": service_health.error_rate,
            "response_time_ms": service_health.response_time_ms,
            **service_health.metrics
        }
        
        for rule in self.detection_rules:
            try:
                if rule["condition"](service_metrics):
                    failure = FailureEvent(
                        failure_id=f"{service_name}_{rule['name']}_{int(time.time())}",
                        failure_type=rule["failure_type"],
                        severity=rule["severity"],
                        service_name=service_name,
                        description=rule["description"],
                        metrics=service_metrics,
                        recovery_suggestions=self._get_recovery_suggestions(rule["failure_type"])
                    )
                    failures.append(failure)
            except Exception as e:
                logger.warning(f"Rule {rule['name']} evaluation failed: {e}")
        
        return failures
    
    async def _detect_system_failures(self, system_metrics: Dict[str, Any]) -> List[FailureEvent]:
        """Detect system-wide failures."""
        failures = []
        
        for rule in self.detection_rules:
            try:
                if rule["condition"](system_metrics):
                    failure = FailureEvent(
                        failure_id=f"system_{rule['name']}_{int(time.time())}",
                        failure_type=rule["failure_type"],
                        severity=rule["severity"],
                        service_name="system",
                        description=rule["description"],
                        metrics=system_metrics,
                        recovery_suggestions=self._get_recovery_suggestions(rule["failure_type"])
                    )
                    failures.append(failure)
            except Exception as e:
                logger.warning(f"System rule {rule['name']} evaluation failed: {e}")
        
        return failures
    
    async def _analyze_failure_patterns(self) -> List[FailureEvent]:
        """Analyze historical failure patterns to detect emerging issues."""
        failures = []
        
        if len(self.failure_history) < 5:
            return failures
        
        recent_failures = list(self.failure_history)[-50:]
        current_time = time.time()
        
        # Check for repeated failures (same type within short period)
        failure_counts: Dict[str, int] = {}
        for failure in recent_failures:
            if current_time - failure.timestamp < 300:  # Last 5 minutes
                key = f"{failure.service_name}_{failure.failure_type.value}"
                failure_counts[key] = failure_counts.get(key, 0) + 1
        
        for key, count in failure_counts.items():
            if count >= 3:
                service_name, failure_type = key.rsplit("_", 1)
                failure = FailureEvent(
                    failure_id=f"pattern_{key}_{int(time.time())}",
                    failure_type=FailureType.UNKNOWN,
                    severity=FailureSeverity.HIGH,
                    service_name=service_name,
                    description=f"Repeated failures detected: {count} occurrences in 5 minutes",
                    recovery_suggestions=["Investigate root cause", "Consider service restart"]
                )
                failures.append(failure)
        
        return failures
    
    def _calculate_health_score(
        self, 
        failures: List[FailureEvent], 
        metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall system health score (0-100)."""
        base_score = 100.0
        
        # Deduct points for failures
        severity_penalties = {
            FailureSeverity.LOW: 5,
            FailureSeverity.MEDIUM: 10,
            FailureSeverity.HIGH: 20,
            FailureSeverity.CRITICAL: 35,
        }
        
        for failure in failures:
            base_score -= severity_penalties.get(failure.severity, 10)
        
        # Deduct points for resource usage
        cpu_penalty = max(0, (metrics.get("cpu_percent", 0) - 70) * 0.5)
        memory_penalty = max(0, (metrics.get("memory_percent", 0) - 70) * 0.5)
        disk_penalty = max(0, (metrics.get("disk_percent", 0) - 80) * 0.3)
        
        base_score -= (cpu_penalty + memory_penalty + disk_penalty)
        
        return max(0.0, min(100.0, base_score))
    
    def _assess_risks(
        self, 
        failures: List[FailureEvent], 
        metrics: Dict[str, Any]
    ) -> Dict[str, float]:
        """Assess various risk levels."""
        risks = {
            "service_outage": 0.0,
            "data_loss": 0.0,
            "performance_degradation": 0.0,
            "security_breach": 0.0,
            "cascading_failure": 0.0,
        }
        
        for failure in failures:
            if failure.failure_type == FailureType.SERVICE_DOWN:
                risks["service_outage"] = min(1.0, risks["service_outage"] + 0.3)
            elif failure.failure_type == FailureType.DATABASE_FAILURE:
                risks["data_loss"] = min(1.0, risks["data_loss"] + 0.4)
                risks["service_outage"] = min(1.0, risks["service_outage"] + 0.2)
            elif failure.failure_type == FailureType.PERFORMANCE_DEGRADATION:
                risks["performance_degradation"] = min(1.0, risks["performance_degradation"] + 0.3)
            elif failure.failure_type == FailureType.SECURITY_BREACH:
                risks["security_breach"] = min(1.0, risks["security_breach"] + 0.5)
            elif failure.failure_type == FailureType.RESOURCE_EXHAUSTION:
                risks["cascading_failure"] = min(1.0, risks["cascading_failure"] + 0.2)
        
        # Increase cascading failure risk if multiple services affected
        affected_services = set()
        for failure in failures:
            affected_services.add(failure.service_name)
            affected_services.update(failure.affected_services)
        
        if len(affected_services) > 2:
            risks["cascading_failure"] = min(1.0, risks["cascading_failure"] + 0.3)
        
        return risks
    
    def _generate_recommendations(
        self, 
        failures: List[FailureEvent], 
        risks: Dict[str, float]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if risks.get("service_outage", 0) > 0.5:
            recommendations.append("Initiate service failover procedures")
            recommendations.append("Alert on-call team for potential outage")
        
        if risks.get("data_loss", 0) > 0.3:
            recommendations.append("Verify database backup status")
            recommendations.append("Consider enabling read-only mode")
        
        if risks.get("performance_degradation", 0) > 0.5:
            recommendations.append("Scale up resources or enable auto-scaling")
            recommendations.append("Review and optimize slow queries")
        
        if risks.get("cascading_failure", 0) > 0.4:
            recommendations.append("Enable circuit breakers for affected services")
            recommendations.append("Isolate failing components")
        
        # Add failure-specific recommendations
        for failure in failures:
            recommendations.extend(failure.recovery_suggestions)
        
        return list(set(recommendations))[:10]  # Deduplicate and limit
    
    def _get_recovery_suggestions(self, failure_type: FailureType) -> List[str]:
        """Get recovery suggestions for a failure type."""
        suggestions = {
            FailureType.SERVICE_DOWN: [
                "Restart the affected service",
                "Check service logs for errors",
                "Verify network connectivity"
            ],
            FailureType.PERFORMANCE_DEGRADATION: [
                "Scale up resources",
                "Clear caches",
                "Optimize database queries"
            ],
            FailureType.RESOURCE_EXHAUSTION: [
                "Free up system resources",
                "Scale horizontally",
                "Implement resource limits"
            ],
            FailureType.DATABASE_FAILURE: [
                "Check database connection",
                "Restart database service",
                "Failover to replica"
            ],
            FailureType.EXTERNAL_DEPENDENCY: [
                "Enable fallback mechanisms",
                "Use cached responses",
                "Contact external service provider"
            ],
        }
        return suggestions.get(failure_type, ["Investigate and resolve manually"])
    
    def register_service(self, service_name: str):
        """Register a service for monitoring."""
        self.monitored_services.add(service_name)
        logger.info(f"Registered service for monitoring: {service_name}")
    
    def update_service_health(self, service_name: str, health: ServiceHealth):
        """Update health status for a service."""
        self.service_health[service_name] = health
    
    def add_detection_rule(self, rule: Dict[str, Any]):
        """Add a custom detection rule."""
        self.detection_rules.append(rule)
        logger.info(f"Added detection rule: {rule.get('name', 'unnamed')}")
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get failure statistics."""
        if not self.failure_history:
            return {"total_failures": 0}
        
        failures = list(self.failure_history)
        current_time = time.time()
        
        # Count by severity
        severity_counts = {}
        for severity in FailureSeverity:
            severity_counts[severity.value] = sum(
                1 for f in failures if f.severity == severity
            )
        
        # Count by type
        type_counts = {}
        for ftype in FailureType:
            type_counts[ftype.value] = sum(
                1 for f in failures if f.failure_type == ftype
            )
        
        # Recent failures (last hour)
        recent_count = sum(
            1 for f in failures if current_time - f.timestamp < 3600
        )
        
        return {
            "total_failures": len(failures),
            "recent_failures_1h": recent_count,
            "by_severity": severity_counts,
            "by_type": type_counts,
            "monitored_services": len(self.monitored_services),
        }


# Global failure detector instance
failure_detector = FailureDetector()
