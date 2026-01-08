"""
Enhanced Fault Detection System for SuperInsight Platform.

Provides comprehensive fault detection capabilities including:
- Multi-level fault detection (service, system, business)
- Intelligent fault classification and root cause analysis
- Proactive fault prediction using ML techniques
- Service dependency mapping and cascade failure detection
- Automated recovery coordination with recovery systems
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import numpy as np
from datetime import datetime, timedelta

from src.system.health_monitor import health_monitor, HealthStatus, HealthMetric
from src.system.enhanced_recovery import recovery_coordinator
from src.system.error_handler import error_handler, ErrorCategory, ErrorSeverity
from src.system.notification import notification_system, NotificationPriority, NotificationChannel
from src.utils.degradation import degradation_manager

logger = logging.getLogger(__name__)


class FaultType(Enum):
    """Types of faults that can be detected."""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CASCADE_FAILURE = "cascade_failure"
    DATA_CORRUPTION = "data_corruption"
    SECURITY_BREACH = "security_breach"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_PARTITION = "network_partition"
    DEPENDENCY_FAILURE = "dependency_failure"


class FaultSeverity(Enum):
    """Severity levels for detected faults."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ServiceDependency:
    """Service dependency definition."""
    service_name: str
    dependency_name: str
    dependency_type: str  # "hard", "soft", "optional"
    timeout_threshold: float = 30.0
    failure_threshold: int = 3


@dataclass
class FaultEvent:
    """Fault event information."""
    fault_id: str
    fault_type: FaultType
    severity: FaultSeverity
    service_name: str
    description: str
    detected_at: datetime
    root_cause: Optional[str] = None
    affected_services: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    recovery_actions: List[str] = field(default_factory=list)
    resolved_at: Optional[datetime] = None
    resolution_time: Optional[float] = None


@dataclass
class FaultPattern:
    """Fault pattern for ML-based detection."""
    pattern_id: str
    pattern_type: str
    features: List[str]
    threshold: float
    confidence: float = 0.0
    occurrences: int = 0
    last_seen: Optional[datetime] = None


class FaultDetectionSystem:
    """
    Enhanced fault detection system with ML-based prediction and root cause analysis.
    
    Features:
    - Multi-dimensional fault detection
    - Service dependency tracking
    - Cascade failure detection
    - ML-based fault prediction
    - Root cause analysis
    - Automated recovery coordination
    """
    
    def __init__(self):
        self.active_faults: Dict[str, FaultEvent] = {}
        self.fault_history: deque = deque(maxlen=1000)
        self.service_dependencies: Dict[str, List[ServiceDependency]] = {}
        self.fault_patterns: Dict[str, FaultPattern] = {}
        
        # Detection thresholds
        self.performance_thresholds = {
            "response_time_ms": 5000,
            "error_rate_percent": 5.0,
            "cpu_usage_percent": 90.0,
            "memory_usage_percent": 90.0,
            "disk_usage_percent": 95.0
        }
        
        # ML-based detection
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.anomaly_scores: Dict[str, float] = {}
        self.baseline_metrics: Dict[str, Dict[str, float]] = {}
        
        # Detection state
        self.detection_active = False
        self.detection_task: Optional[asyncio.Task] = None
        self.fault_callbacks: List[Callable[[FaultEvent], None]] = []
        
        # Initialize default service dependencies
        self._setup_default_dependencies()
        self._setup_fault_patterns()
    
    def _setup_default_dependencies(self):
        """Setup default service dependencies."""
        # Database dependencies
        self.service_dependencies["annotation_service"] = [
            ServiceDependency("annotation_service", "database", "hard", 10.0, 2),
            ServiceDependency("annotation_service", "ai_services", "soft", 30.0, 3),
            ServiceDependency("annotation_service", "label_studio", "soft", 15.0, 2)
        ]
        
        self.service_dependencies["quality_service"] = [
            ServiceDependency("quality_service", "database", "hard", 10.0, 2),
            ServiceDependency("quality_service", "annotation_service", "soft", 20.0, 3)
        ]
        
        self.service_dependencies["export_service"] = [
            ServiceDependency("export_service", "database", "hard", 10.0, 2),
            ServiceDependency("export_service", "storage", "hard", 15.0, 2),
            ServiceDependency("export_service", "quality_service", "soft", 30.0, 3)
        ]
        
        logger.info("Default service dependencies configured")
    
    def _setup_fault_patterns(self):
        """Setup ML-based fault detection patterns."""
        # Performance degradation pattern
        self.fault_patterns["perf_degradation"] = FaultPattern(
            pattern_id="perf_degradation",
            pattern_type="performance",
            features=["response_time_ms", "cpu_usage_percent", "memory_usage_percent"],
            threshold=0.8
        )
        
        # Resource exhaustion pattern
        self.fault_patterns["resource_exhaustion"] = FaultPattern(
            pattern_id="resource_exhaustion",
            pattern_type="resource",
            features=["memory_usage_percent", "disk_usage_percent", "cpu_usage_percent"],
            threshold=0.9
        )
        
        # Cascade failure pattern
        self.fault_patterns["cascade_failure"] = FaultPattern(
            pattern_id="cascade_failure",
            pattern_type="cascade",
            features=["error_rate_percent", "dependency_failures", "service_unavailable"],
            threshold=0.7
        )
        
        logger.info("Fault detection patterns initialized")
    
    async def start_detection(self):
        """Start the fault detection system."""
        if self.detection_active:
            logger.warning("Fault detection is already active")
            return
        
        self.detection_active = True
        self.detection_task = asyncio.create_task(self._detection_loop())
        
        # Start baseline metric collection
        await self._collect_baseline_metrics()
        
        logger.info("Fault detection system started")
    
    async def stop_detection(self):
        """Stop the fault detection system."""
        self.detection_active = False
        
        if self.detection_task:
            self.detection_task.cancel()
            try:
                await self.detection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Fault detection system stopped")
    
    def add_fault_callback(self, callback: Callable[[FaultEvent], None]):
        """Add callback for fault events."""
        self.fault_callbacks.append(callback)
    
    def register_service_dependency(self, dependency: ServiceDependency):
        """Register a service dependency."""
        if dependency.service_name not in self.service_dependencies:
            self.service_dependencies[dependency.service_name] = []
        
        self.service_dependencies[dependency.service_name].append(dependency)
        logger.info(f"Registered dependency: {dependency.service_name} -> {dependency.dependency_name}")
    
    async def _detection_loop(self):
        """Main fault detection loop."""
        while self.detection_active:
            try:
                # Collect current metrics
                await self._collect_metrics()
                
                # Perform multi-level fault detection
                await self._detect_service_faults()
                await self._detect_system_faults()
                await self._detect_cascade_failures()
                await self._detect_ml_based_faults()
                
                # Update fault patterns
                self._update_fault_patterns()
                
                # Check for fault resolution
                await self._check_fault_resolution()
                
                # Sleep before next detection cycle
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in fault detection loop: {e}")
                await asyncio.sleep(10)
    
    async def _collect_metrics(self):
        """Collect metrics from various sources."""
        try:
            # Get health metrics from health monitor
            health_summary = health_monitor.get_metrics_summary()
            
            for metric_name, metric_data in health_summary.get("metrics", {}).items():
                value = metric_data.get("value", 0)
                self.metric_history[metric_name].append({
                    "timestamp": time.time(),
                    "value": value,
                    "status": metric_data.get("status", "unknown")
                })
            
            # Get error statistics
            error_stats = error_handler.get_error_statistics()
            self.metric_history["error_rate_percent"].append({
                "timestamp": time.time(),
                "value": error_stats.get("error_rate", 0) * 100,
                "status": "healthy" if error_stats.get("error_rate", 0) < 0.05 else "warning"
            })
            
            # Get service health from degradation manager
            service_health = degradation_manager.get_all_service_health()
            for service_name, health in service_health.items():
                self.metric_history[f"{service_name}_health"].append({
                    "timestamp": time.time(),
                    "value": 1.0 if health.is_healthy else 0.0,
                    "status": "healthy" if health.is_healthy else "unhealthy"
                })
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    async def _collect_baseline_metrics(self):
        """Collect baseline metrics for anomaly detection."""
        try:
            # Wait for some metrics to accumulate
            await asyncio.sleep(30)
            
            for metric_name, history in self.metric_history.items():
                if len(history) >= 10:  # Need at least 10 data points
                    values = [entry["value"] for entry in history]
                    
                    self.baseline_metrics[metric_name] = {
                        "mean": np.mean(values),
                        "std": np.std(values),
                        "min": np.min(values),
                        "max": np.max(values),
                        "p95": np.percentile(values, 95)
                    }
            
            logger.info(f"Collected baseline metrics for {len(self.baseline_metrics)} metrics")
            
        except Exception as e:
            logger.error(f"Error collecting baseline metrics: {e}")
    
    async def _detect_service_faults(self):
        """Detect service-level faults."""
        try:
            health_summary = health_monitor.get_metrics_summary()
            
            for metric_name, metric_data in health_summary.get("metrics", {}).items():
                status = metric_data.get("status", "unknown")
                value = metric_data.get("value", 0)
                
                # Check for service unavailability
                if status == "unhealthy":
                    await self._create_fault_event(
                        fault_type=FaultType.SERVICE_UNAVAILABLE,
                        severity=FaultSeverity.HIGH,
                        service_name=metric_name,
                        description=f"Service {metric_name} is unhealthy",
                        metrics={"current_value": value, "status": status}
                    )
                
                # Check for performance degradation
                elif status == "warning":
                    # Check if this is performance-related
                    if any(perf_key in metric_name.lower() for perf_key in ["cpu", "memory", "response_time"]):
                        await self._create_fault_event(
                            fault_type=FaultType.PERFORMANCE_DEGRADATION,
                            severity=FaultSeverity.MEDIUM,
                            service_name=metric_name,
                            description=f"Performance degradation detected in {metric_name}",
                            metrics={"current_value": value, "status": status}
                        )
            
        except Exception as e:
            logger.error(f"Error detecting service faults: {e}")
    
    async def _detect_system_faults(self):
        """Detect system-level faults."""
        try:
            # Check resource exhaustion
            for metric_name, threshold in self.performance_thresholds.items():
                if metric_name in self.metric_history:
                    history = self.metric_history[metric_name]
                    if history:
                        latest_value = history[-1]["value"]
                        
                        if latest_value >= threshold:
                            await self._create_fault_event(
                                fault_type=FaultType.RESOURCE_EXHAUSTION,
                                severity=FaultSeverity.HIGH,
                                service_name="system",
                                description=f"Resource exhaustion: {metric_name} = {latest_value}",
                                metrics={"current_value": latest_value, "threshold": threshold}
                            )
            
            # Check for configuration errors (based on error patterns)
            error_stats = error_handler.get_error_statistics()
            config_errors = error_stats.get("categories", {}).get("configuration", 0)
            
            if config_errors > 5:  # More than 5 config errors
                await self._create_fault_event(
                    fault_type=FaultType.CONFIGURATION_ERROR,
                    severity=FaultSeverity.MEDIUM,
                    service_name="system",
                    description=f"Multiple configuration errors detected: {config_errors}",
                    metrics={"error_count": config_errors}
                )
            
        except Exception as e:
            logger.error(f"Error detecting system faults: {e}")
    
    async def _detect_cascade_failures(self):
        """Detect cascade failures based on service dependencies."""
        try:
            for service_name, dependencies in self.service_dependencies.items():
                failed_dependencies = []
                
                for dep in dependencies:
                    # Check if dependency is healthy
                    dep_health_key = f"{dep.dependency_name}_health"
                    if dep_health_key in self.metric_history:
                        history = self.metric_history[dep_health_key]
                        if history:
                            latest_health = history[-1]["value"]
                            if latest_health < 1.0:  # Not healthy
                                failed_dependencies.append(dep.dependency_name)
                
                # Check if enough dependencies failed to cause cascade
                hard_deps_failed = sum(1 for dep in dependencies 
                                     if dep.dependency_type == "hard" and dep.dependency_name in failed_dependencies)
                
                if hard_deps_failed > 0 or len(failed_dependencies) >= len(dependencies) * 0.5:
                    await self._create_fault_event(
                        fault_type=FaultType.CASCADE_FAILURE,
                        severity=FaultSeverity.CRITICAL,
                        service_name=service_name,
                        description=f"Cascade failure detected: {len(failed_dependencies)} dependencies failed",
                        metrics={"failed_dependencies": failed_dependencies, "hard_failures": hard_deps_failed},
                        affected_services=failed_dependencies
                    )
            
        except Exception as e:
            logger.error(f"Error detecting cascade failures: {e}")
    
    async def _detect_ml_based_faults(self):
        """Detect faults using ML-based anomaly detection."""
        try:
            for pattern_id, pattern in self.fault_patterns.items():
                anomaly_score = await self._calculate_anomaly_score(pattern)
                
                if anomaly_score > pattern.threshold:
                    # Determine fault type and severity based on pattern
                    fault_type = self._pattern_to_fault_type(pattern.pattern_type)
                    severity = self._anomaly_score_to_severity(anomaly_score)
                    
                    await self._create_fault_event(
                        fault_type=fault_type,
                        severity=severity,
                        service_name="system",
                        description=f"ML-based fault detected: {pattern.pattern_type} (score: {anomaly_score:.2f})",
                        metrics={"anomaly_score": anomaly_score, "pattern_id": pattern_id}
                    )
                    
                    # Update pattern statistics
                    pattern.confidence = anomaly_score
                    pattern.occurrences += 1
                    pattern.last_seen = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error in ML-based fault detection: {e}")
    
    async def _calculate_anomaly_score(self, pattern: FaultPattern) -> float:
        """Calculate anomaly score for a fault pattern."""
        try:
            scores = []
            
            for feature in pattern.features:
                if feature in self.metric_history and feature in self.baseline_metrics:
                    history = self.metric_history[feature]
                    baseline = self.baseline_metrics[feature]
                    
                    if history:
                        current_value = history[-1]["value"]
                        
                        # Calculate z-score
                        if baseline["std"] > 0:
                            z_score = abs(current_value - baseline["mean"]) / baseline["std"]
                            # Normalize to 0-1 range
                            anomaly_score = min(z_score / 3.0, 1.0)  # 3-sigma rule
                            scores.append(anomaly_score)
            
            # Return average anomaly score
            return np.mean(scores) if scores else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating anomaly score: {e}")
            return 0.0
    
    def _pattern_to_fault_type(self, pattern_type: str) -> FaultType:
        """Convert pattern type to fault type."""
        mapping = {
            "performance": FaultType.PERFORMANCE_DEGRADATION,
            "resource": FaultType.RESOURCE_EXHAUSTION,
            "cascade": FaultType.CASCADE_FAILURE
        }
        return mapping.get(pattern_type, FaultType.PERFORMANCE_DEGRADATION)
    
    def _anomaly_score_to_severity(self, score: float) -> FaultSeverity:
        """Convert anomaly score to fault severity."""
        if score >= 0.9:
            return FaultSeverity.CRITICAL
        elif score >= 0.7:
            return FaultSeverity.HIGH
        elif score >= 0.5:
            return FaultSeverity.MEDIUM
        else:
            return FaultSeverity.LOW
    
    async def _create_fault_event(self, fault_type: FaultType, severity: FaultSeverity,
                                service_name: str, description: str,
                                metrics: Dict[str, Any] = None,
                                affected_services: List[str] = None):
        """Create and process a fault event."""
        try:
            fault_id = f"fault_{int(time.time() * 1000)}"
            
            # Check if similar fault already exists
            existing_fault = self._find_similar_fault(fault_type, service_name)
            if existing_fault:
                logger.debug(f"Similar fault already exists: {existing_fault.fault_id}")
                return
            
            # Create fault event
            fault_event = FaultEvent(
                fault_id=fault_id,
                fault_type=fault_type,
                severity=severity,
                service_name=service_name,
                description=description,
                detected_at=datetime.utcnow(),
                metrics=metrics or {},
                affected_services=affected_services or []
            )
            
            # Perform root cause analysis
            fault_event.root_cause = await self._analyze_root_cause(fault_event)
            
            # Generate recovery actions
            fault_event.recovery_actions = await self._generate_recovery_actions(fault_event)
            
            # Store fault
            self.active_faults[fault_id] = fault_event
            self.fault_history.append(fault_event)
            
            # Send notifications
            await self._send_fault_notification(fault_event)
            
            # Trigger automatic recovery if configured
            if fault_event.recovery_actions:
                await self._trigger_automatic_recovery(fault_event)
            
            # Notify callbacks
            for callback in self.fault_callbacks:
                try:
                    callback(fault_event)
                except Exception as e:
                    logger.error(f"Error in fault callback: {e}")
            
            logger.info(f"Fault detected: {fault_id} - {description}")
            
        except Exception as e:
            logger.error(f"Error creating fault event: {e}")
    
    def _find_similar_fault(self, fault_type: FaultType, service_name: str) -> Optional[FaultEvent]:
        """Find similar active fault to avoid duplicates."""
        for fault in self.active_faults.values():
            if (fault.fault_type == fault_type and 
                fault.service_name == service_name and
                fault.resolved_at is None):
                return fault
        return None
    
    async def _analyze_root_cause(self, fault_event: FaultEvent) -> str:
        """Analyze root cause of the fault."""
        try:
            root_causes = []
            
            # Check dependency failures
            if fault_event.service_name in self.service_dependencies:
                for dep in self.service_dependencies[fault_event.service_name]:
                    dep_health_key = f"{dep.dependency_name}_health"
                    if dep_health_key in self.metric_history:
                        history = self.metric_history[dep_health_key]
                        if history and history[-1]["value"] < 1.0:
                            root_causes.append(f"Dependency failure: {dep.dependency_name}")
            
            # Check resource constraints
            for metric_name, threshold in self.performance_thresholds.items():
                if metric_name in self.metric_history:
                    history = self.metric_history[metric_name]
                    if history and history[-1]["value"] >= threshold * 0.8:  # 80% of threshold
                        root_causes.append(f"Resource constraint: {metric_name}")
            
            # Check error patterns
            error_stats = error_handler.get_error_statistics()
            if error_stats.get("error_rate", 0) > 0.1:  # 10% error rate
                root_causes.append("High error rate")
            
            # Default root cause
            if not root_causes:
                root_causes.append("Unknown - requires investigation")
            
            return "; ".join(root_causes)
            
        except Exception as e:
            logger.error(f"Error analyzing root cause: {e}")
            return "Analysis failed"
    
    async def _generate_recovery_actions(self, fault_event: FaultEvent) -> List[str]:
        """Generate recovery actions for the fault."""
        try:
            actions = []
            
            # Actions based on fault type
            if fault_event.fault_type == FaultType.SERVICE_UNAVAILABLE:
                actions.extend([
                    "restart_service",
                    "check_service_dependencies",
                    "enable_circuit_breaker"
                ])
            
            elif fault_event.fault_type == FaultType.PERFORMANCE_DEGRADATION:
                actions.extend([
                    "scale_up_service",
                    "clear_caches",
                    "optimize_queries"
                ])
            
            elif fault_event.fault_type == FaultType.RESOURCE_EXHAUSTION:
                actions.extend([
                    "scale_up_resources",
                    "clear_temporary_files",
                    "restart_memory_intensive_services"
                ])
            
            elif fault_event.fault_type == FaultType.CASCADE_FAILURE:
                actions.extend([
                    "enable_circuit_breakers",
                    "isolate_failed_services",
                    "activate_fallback_services"
                ])
            
            elif fault_event.fault_type == FaultType.CONFIGURATION_ERROR:
                actions.extend([
                    "validate_configuration",
                    "restore_backup_configuration",
                    "restart_affected_services"
                ])
            
            # Actions based on severity
            if fault_event.severity == FaultSeverity.CRITICAL:
                actions.insert(0, "alert_operations_team")
                actions.append("prepare_manual_intervention")
            
            return actions
            
        except Exception as e:
            logger.error(f"Error generating recovery actions: {e}")
            return []
    
    async def _send_fault_notification(self, fault_event: FaultEvent):
        """Send notification about the fault."""
        try:
            # Determine notification priority
            priority_map = {
                FaultSeverity.LOW: NotificationPriority.NORMAL,
                FaultSeverity.MEDIUM: NotificationPriority.HIGH,
                FaultSeverity.HIGH: NotificationPriority.HIGH,
                FaultSeverity.CRITICAL: NotificationPriority.CRITICAL
            }
            
            priority = priority_map.get(fault_event.severity, NotificationPriority.NORMAL)
            
            # Determine notification channels
            channels = [NotificationChannel.LOG]
            if fault_event.severity in [FaultSeverity.HIGH, FaultSeverity.CRITICAL]:
                channels.extend([NotificationChannel.SLACK, NotificationChannel.EMAIL])
            
            # Send notification
            notification_system.send_notification(
                title=f"Fault Detected - {fault_event.fault_type.value}",
                message=f"Service: {fault_event.service_name}\n"
                       f"Severity: {fault_event.severity.value}\n"
                       f"Description: {fault_event.description}\n"
                       f"Root Cause: {fault_event.root_cause}\n"
                       f"Recovery Actions: {', '.join(fault_event.recovery_actions)}",
                priority=priority,
                channels=channels
            )
            
        except Exception as e:
            logger.error(f"Error sending fault notification: {e}")
    
    async def _trigger_automatic_recovery(self, fault_event: FaultEvent):
        """Trigger automatic recovery for the fault."""
        try:
            # Map fault type to error category for recovery coordinator
            fault_to_category = {
                FaultType.SERVICE_UNAVAILABLE: "external_api",
                FaultType.PERFORMANCE_DEGRADATION: "system",
                FaultType.RESOURCE_EXHAUSTION: "system",
                FaultType.CASCADE_FAILURE: "system",
                FaultType.CONFIGURATION_ERROR: "system"
            }
            
            error_category = fault_to_category.get(fault_event.fault_type, "system")
            
            # Trigger manual recovery through recovery coordinator
            from src.system.enhanced_recovery import trigger_manual_recovery
            
            success = trigger_manual_recovery(
                error_category=error_category,
                service_name=fault_event.service_name
            )
            
            if success:
                logger.info(f"Automatic recovery triggered for fault {fault_event.fault_id}")
            else:
                logger.warning(f"Automatic recovery failed for fault {fault_event.fault_id}")
            
        except Exception as e:
            logger.error(f"Error triggering automatic recovery: {e}")
    
    async def _check_fault_resolution(self):
        """Check if active faults have been resolved."""
        try:
            resolved_faults = []
            
            for fault_id, fault_event in self.active_faults.items():
                if await self._is_fault_resolved(fault_event):
                    fault_event.resolved_at = datetime.utcnow()
                    fault_event.resolution_time = (
                        fault_event.resolved_at - fault_event.detected_at
                    ).total_seconds()
                    
                    resolved_faults.append(fault_id)
                    
                    # Send resolution notification
                    notification_system.send_notification(
                        title=f"Fault Resolved - {fault_event.fault_type.value}",
                        message=f"Service: {fault_event.service_name}\n"
                               f"Resolution Time: {fault_event.resolution_time:.1f}s\n"
                               f"Root Cause: {fault_event.root_cause}",
                        priority=NotificationPriority.NORMAL,
                        channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
                    )
                    
                    logger.info(f"Fault resolved: {fault_id} (resolution time: {fault_event.resolution_time:.1f}s)")
            
            # Remove resolved faults from active list
            for fault_id in resolved_faults:
                del self.active_faults[fault_id]
            
        except Exception as e:
            logger.error(f"Error checking fault resolution: {e}")
    
    async def _is_fault_resolved(self, fault_event: FaultEvent) -> bool:
        """Check if a fault has been resolved."""
        try:
            # Check based on fault type
            if fault_event.fault_type == FaultType.SERVICE_UNAVAILABLE:
                # Check if service is healthy again
                service_health_key = f"{fault_event.service_name}_health"
                if service_health_key in self.metric_history:
                    history = self.metric_history[service_health_key]
                    if history:
                        # Check if healthy for at least 3 consecutive checks
                        recent_values = [entry["value"] for entry in list(history)[-3:]]
                        return all(value >= 1.0 for value in recent_values)
            
            elif fault_event.fault_type == FaultType.PERFORMANCE_DEGRADATION:
                # Check if performance metrics are back to normal
                for metric_name in ["cpu_usage", "memory_usage", "response_time"]:
                    if metric_name in fault_event.service_name.lower():
                        if metric_name in self.metric_history:
                            history = self.metric_history[metric_name]
                            if history:
                                current_value = history[-1]["value"]
                                threshold = self.performance_thresholds.get(f"{metric_name}_percent", 
                                                                          self.performance_thresholds.get(f"{metric_name}_ms", 100))
                                if current_value < threshold * 0.8:  # 80% of threshold
                                    return True
            
            elif fault_event.fault_type == FaultType.RESOURCE_EXHAUSTION:
                # Check if resource usage is back to normal
                metrics_to_check = fault_event.metrics
                for metric_name, threshold in self.performance_thresholds.items():
                    if metric_name in self.metric_history:
                        history = self.metric_history[metric_name]
                        if history:
                            current_value = history[-1]["value"]
                            if current_value < threshold * 0.7:  # 70% of threshold
                                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking fault resolution: {e}")
            return False
    
    def _update_fault_patterns(self):
        """Update fault patterns based on recent detections."""
        try:
            # Update pattern confidence based on recent fault history
            recent_faults = [f for f in list(self.fault_history)[-50:] if f.resolved_at is not None]
            
            for pattern in self.fault_patterns.values():
                # Count pattern matches in recent faults
                matches = 0
                for fault in recent_faults:
                    if self._fault_matches_pattern(fault, pattern):
                        matches += 1
                
                # Update confidence (exponential moving average)
                if len(recent_faults) > 0:
                    match_rate = matches / len(recent_faults)
                    alpha = 0.1  # Learning rate
                    pattern.confidence = alpha * match_rate + (1 - alpha) * pattern.confidence
            
        except Exception as e:
            logger.error(f"Error updating fault patterns: {e}")
    
    def _fault_matches_pattern(self, fault: FaultEvent, pattern: FaultPattern) -> bool:
        """Check if a fault matches a pattern."""
        try:
            # Simple pattern matching based on fault type
            if pattern.pattern_type == "performance" and fault.fault_type == FaultType.PERFORMANCE_DEGRADATION:
                return True
            elif pattern.pattern_type == "resource" and fault.fault_type == FaultType.RESOURCE_EXHAUSTION:
                return True
            elif pattern.pattern_type == "cascade" and fault.fault_type == FaultType.CASCADE_FAILURE:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error matching fault to pattern: {e}")
            return False
    
    def get_fault_statistics(self) -> Dict[str, Any]:
        """Get comprehensive fault detection statistics."""
        try:
            total_faults = len(self.fault_history)
            resolved_faults = [f for f in self.fault_history if f.resolved_at is not None]
            
            if total_faults == 0:
                return {
                    "total_faults": 0,
                    "active_faults": 0,
                    "resolution_rate": 0.0,
                    "avg_resolution_time": 0.0,
                    "fault_types": {},
                    "severity_distribution": {}
                }
            
            # Calculate statistics
            resolution_rate = len(resolved_faults) / total_faults
            avg_resolution_time = np.mean([f.resolution_time for f in resolved_faults if f.resolution_time])
            
            # Fault type distribution
            fault_types = {}
            for fault in self.fault_history:
                fault_type = fault.fault_type.value
                fault_types[fault_type] = fault_types.get(fault_type, 0) + 1
            
            # Severity distribution
            severity_distribution = {}
            for fault in self.fault_history:
                severity = fault.severity.value
                severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
            
            return {
                "total_faults": total_faults,
                "active_faults": len(self.active_faults),
                "resolved_faults": len(resolved_faults),
                "resolution_rate": resolution_rate,
                "avg_resolution_time": avg_resolution_time,
                "fault_types": fault_types,
                "severity_distribution": severity_distribution,
                "recent_faults": [
                    {
                        "fault_id": f.fault_id,
                        "fault_type": f.fault_type.value,
                        "severity": f.severity.value,
                        "service_name": f.service_name,
                        "description": f.description,
                        "detected_at": f.detected_at.isoformat(),
                        "resolved_at": f.resolved_at.isoformat() if f.resolved_at else None,
                        "resolution_time": f.resolution_time
                    }
                    for f in list(self.fault_history)[-10:]  # Last 10 faults
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting fault statistics: {e}")
            return {}
    
    def get_active_faults(self) -> List[Dict[str, Any]]:
        """Get list of active faults."""
        return [
            {
                "fault_id": fault.fault_id,
                "fault_type": fault.fault_type.value,
                "severity": fault.severity.value,
                "service_name": fault.service_name,
                "description": fault.description,
                "root_cause": fault.root_cause,
                "detected_at": fault.detected_at.isoformat(),
                "recovery_actions": fault.recovery_actions,
                "affected_services": fault.affected_services
            }
            for fault in self.active_faults.values()
        ]


# Global fault detection system instance
fault_detection_system = FaultDetectionSystem()


# Convenience functions
async def start_fault_detection():
    """Start the global fault detection system."""
    await fault_detection_system.start_detection()


async def stop_fault_detection():
    """Stop the global fault detection system."""
    await fault_detection_system.stop_detection()


def get_fault_status() -> Dict[str, Any]:
    """Get current fault detection status."""
    return {
        "detection_active": fault_detection_system.detection_active,
        "active_faults": len(fault_detection_system.active_faults),
        "total_patterns": len(fault_detection_system.fault_patterns),
        "service_dependencies": len(fault_detection_system.service_dependencies),
        "statistics": fault_detection_system.get_fault_statistics()
    }


def register_fault_callback(callback: Callable[[FaultEvent], None]):
    """Register a callback for fault events."""
    fault_detection_system.add_fault_callback(callback)