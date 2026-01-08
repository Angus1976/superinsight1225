"""
Resource Usage Optimization for SuperInsight Platform.

Provides comprehensive resource optimization including:
- CPU, memory, and disk monitoring with intelligent analysis
- Resource usage prediction and capacity planning
- Automated scaling recommendations and cost optimization
- Resource bottleneck detection and resolution suggestions
- Performance-based resource allocation optimization
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
import statistics
import numpy as np

from src.config.settings import settings


logger = logging.getLogger(__name__)


@dataclass
class ResourceMetrics:
    """Resource usage metrics snapshot."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    memory_used_gb: float
    disk_percent: float
    disk_free_gb: float
    disk_total_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    load_average: Optional[Tuple[float, float, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_available_gb": self.memory_available_gb,
            "memory_used_gb": self.memory_used_gb,
            "disk_percent": self.disk_percent,
            "disk_free_gb": self.disk_free_gb,
            "disk_total_gb": self.disk_total_gb,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_recv": self.network_bytes_recv,
            "process_count": self.process_count,
            "load_average": self.load_average
        }


@dataclass
class ResourcePrediction:
    """Resource usage prediction."""
    resource_type: str
    current_usage: float
    predicted_1h: float
    predicted_6h: float
    predicted_24h: float
    predicted_7d: float
    confidence: float
    trend: str  # increasing, decreasing, stable
    recommendation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resource_type": self.resource_type,
            "current_usage": self.current_usage,
            "predicted_1h": self.predicted_1h,
            "predicted_6h": self.predicted_6h,
            "predicted_24h": self.predicted_24h,
            "predicted_7d": self.predicted_7d,
            "confidence": self.confidence,
            "trend": self.trend,
            "recommendation": self.recommendation
        }


@dataclass
class ScalingRecommendation:
    """Scaling recommendation."""
    resource_type: str
    current_allocation: float
    recommended_allocation: float
    scaling_factor: float
    reason: str
    priority: str  # low, medium, high, critical
    estimated_cost_impact: float
    estimated_performance_impact: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resource_type": self.resource_type,
            "current_allocation": self.current_allocation,
            "recommended_allocation": self.recommended_allocation,
            "scaling_factor": self.scaling_factor,
            "reason": self.reason,
            "priority": self.priority,
            "estimated_cost_impact": self.estimated_cost_impact,
            "estimated_performance_impact": self.estimated_performance_impact
        }


@dataclass
class ResourceBottleneck:
    """Resource bottleneck analysis."""
    resource_type: str
    severity: str  # low, medium, high, critical
    current_usage: float
    threshold: float
    impact: str
    root_causes: List[str]
    recommendations: List[str]
    estimated_resolution_time: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resource_type": self.resource_type,
            "severity": self.severity,
            "current_usage": self.current_usage,
            "threshold": self.threshold,
            "impact": self.impact,
            "root_causes": self.root_causes,
            "recommendations": self.recommendations,
            "estimated_resolution_time": self.estimated_resolution_time
        }


class ResourceMonitor:
    """
    Real-time resource monitoring with intelligent analysis.
    
    Collects and analyzes system resource usage patterns to provide
    insights, predictions, and optimization recommendations.
    """
    
    def __init__(self, collection_interval: int = 30):
        self.collection_interval = collection_interval
        self.metrics_history: deque = deque(maxlen=2880)  # 24 hours at 30s intervals
        self.is_monitoring = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        
        # Thresholds for alerts
        self.cpu_warning_threshold = 70.0
        self.cpu_critical_threshold = 90.0
        self.memory_warning_threshold = 80.0
        self.memory_critical_threshold = 95.0
        self.disk_warning_threshold = 85.0
        self.disk_critical_threshold = 95.0
        
        # Alert handlers
        self.alert_handlers: List[Callable] = []
    
    def register_alert_handler(self, handler: Callable):
        """Register an alert handler."""
        self.alert_handlers.append(handler)
    
    async def start_monitoring(self):
        """Start resource monitoring."""
        if self.is_monitoring:
            logger.warning("Resource monitoring is already running")
            return
        
        self.is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started resource monitoring")
    
    async def stop_monitoring(self):
        """Stop resource monitoring."""
        self.is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped resource monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                metrics = await self._collect_metrics()
                
                with self._lock:
                    self.metrics_history.append(metrics)
                
                # Check for alerts
                await self._check_resource_alerts(metrics)
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(5)  # Short delay before retrying
    
    async def _collect_metrics(self) -> ResourceMetrics:
        """Collect current resource metrics."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)
        memory_used_gb = memory.used / (1024**3)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        disk_free_gb = disk.free / (1024**3)
        disk_total_gb = disk.total / (1024**3)
        
        # Network usage
        network = psutil.net_io_counters()
        network_bytes_sent = network.bytes_sent if network else 0
        network_bytes_recv = network.bytes_recv if network else 0
        
        # Process count
        process_count = len(psutil.pids())
        
        # Load average (if available)
        load_average = None
        try:
            load_average = psutil.getloadavg()
        except AttributeError:
            pass  # Not available on all platforms
        
        return ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_available_gb=memory_available_gb,
            memory_used_gb=memory_used_gb,
            disk_percent=disk_percent,
            disk_free_gb=disk_free_gb,
            disk_total_gb=disk_total_gb,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            process_count=process_count,
            load_average=load_average
        )
    
    async def _check_resource_alerts(self, metrics: ResourceMetrics):
        """Check resource metrics against thresholds and trigger alerts."""
        alerts = []
        
        # CPU alerts
        if metrics.cpu_percent >= self.cpu_critical_threshold:
            alerts.append({
                "type": "resource_alert",
                "resource": "cpu",
                "severity": "critical",
                "current_value": metrics.cpu_percent,
                "threshold": self.cpu_critical_threshold,
                "message": f"Critical CPU usage: {metrics.cpu_percent:.1f}%"
            })
        elif metrics.cpu_percent >= self.cpu_warning_threshold:
            alerts.append({
                "type": "resource_alert",
                "resource": "cpu",
                "severity": "warning",
                "current_value": metrics.cpu_percent,
                "threshold": self.cpu_warning_threshold,
                "message": f"High CPU usage: {metrics.cpu_percent:.1f}%"
            })
        
        # Memory alerts
        if metrics.memory_percent >= self.memory_critical_threshold:
            alerts.append({
                "type": "resource_alert",
                "resource": "memory",
                "severity": "critical",
                "current_value": metrics.memory_percent,
                "threshold": self.memory_critical_threshold,
                "message": f"Critical memory usage: {metrics.memory_percent:.1f}%"
            })
        elif metrics.memory_percent >= self.memory_warning_threshold:
            alerts.append({
                "type": "resource_alert",
                "resource": "memory",
                "severity": "warning",
                "current_value": metrics.memory_percent,
                "threshold": self.memory_warning_threshold,
                "message": f"High memory usage: {metrics.memory_percent:.1f}%"
            })
        
        # Disk alerts
        if metrics.disk_percent >= self.disk_critical_threshold:
            alerts.append({
                "type": "resource_alert",
                "resource": "disk",
                "severity": "critical",
                "current_value": metrics.disk_percent,
                "threshold": self.disk_critical_threshold,
                "message": f"Critical disk usage: {metrics.disk_percent:.1f}%"
            })
        elif metrics.disk_percent >= self.disk_warning_threshold:
            alerts.append({
                "type": "resource_alert",
                "resource": "disk",
                "severity": "warning",
                "current_value": metrics.disk_percent,
                "threshold": self.disk_warning_threshold,
                "message": f"High disk usage: {metrics.disk_percent:.1f}%"
            })
        
        # Send alerts
        for alert in alerts:
            await self._send_alert(alert)
    
    async def _send_alert(self, alert: Dict[str, Any]):
        """Send resource alert to handlers."""
        alert["timestamp"] = time.time()
        
        logger.warning(f"Resource Alert: {alert['message']}")
        
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """Get the most recent resource metrics."""
        with self._lock:
            return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, hours: int = 24) -> List[ResourceMetrics]:
        """Get resource metrics history."""
        cutoff_time = time.time() - (hours * 3600)
        
        with self._lock:
            return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def get_resource_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get resource usage statistics."""
        history = self.get_metrics_history(hours)
        
        if not history:
            return {"error": "No metrics available"}
        
        cpu_values = [m.cpu_percent for m in history]
        memory_values = [m.memory_percent for m in history]
        disk_values = [m.disk_percent for m in history]
        
        return {
            "period_hours": hours,
            "data_points": len(history),
            "cpu": {
                "current": cpu_values[-1] if cpu_values else 0,
                "average": statistics.mean(cpu_values),
                "min": min(cpu_values),
                "max": max(cpu_values),
                "p95": self._percentile(cpu_values, 95),
                "trend": self._calculate_trend(cpu_values)
            },
            "memory": {
                "current": memory_values[-1] if memory_values else 0,
                "average": statistics.mean(memory_values),
                "min": min(memory_values),
                "max": max(memory_values),
                "p95": self._percentile(memory_values, 95),
                "trend": self._calculate_trend(memory_values)
            },
            "disk": {
                "current": disk_values[-1] if disk_values else 0,
                "average": statistics.mean(disk_values),
                "min": min(disk_values),
                "max": max(disk_values),
                "p95": self._percentile(disk_values, 95),
                "trend": self._calculate_trend(disk_values)
            }
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for values."""
        if len(values) < 10:
            return "insufficient_data"
        
        # Use linear regression to determine trend
        n = len(values)
        x_values = list(range(n))
        
        # Calculate slope
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Classify trend based on slope
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"


class ResourcePredictor:
    """
    Resource usage prediction and capacity planning.
    
    Uses historical data to predict future resource usage and
    provide capacity planning recommendations.
    """
    
    def __init__(self, monitor: ResourceMonitor):
        self.monitor = monitor
    
    def predict_resource_usage(self, resource_type: str, hours_ahead: int = 24) -> Optional[ResourcePrediction]:
        """Predict future resource usage."""
        history = self.monitor.get_metrics_history(hours=72)  # Use 3 days of history
        
        if len(history) < 50:  # Need sufficient data
            return None
        
        # Extract values for the specified resource
        if resource_type == "cpu":
            values = [m.cpu_percent for m in history]
        elif resource_type == "memory":
            values = [m.memory_percent for m in history]
        elif resource_type == "disk":
            values = [m.disk_percent for m in history]
        else:
            return None
        
        # Simple linear prediction
        current_usage = values[-1]
        trend = self.monitor._calculate_trend(values[-50:])  # Use recent trend
        
        # Calculate prediction based on trend
        if trend == "increasing":
            # Estimate growth rate
            recent_values = values[-20:]
            growth_rate = (recent_values[-1] - recent_values[0]) / len(recent_values)
            
            predicted_1h = min(100, current_usage + growth_rate * 2)  # 2 intervals per hour
            predicted_6h = min(100, current_usage + growth_rate * 12)
            predicted_24h = min(100, current_usage + growth_rate * 48)
            predicted_7d = min(100, current_usage + growth_rate * 336)
            
        elif trend == "decreasing":
            # Estimate decline rate
            recent_values = values[-20:]
            decline_rate = (recent_values[0] - recent_values[-1]) / len(recent_values)
            
            predicted_1h = max(0, current_usage - decline_rate * 2)
            predicted_6h = max(0, current_usage - decline_rate * 12)
            predicted_24h = max(0, current_usage - decline_rate * 48)
            predicted_7d = max(0, current_usage - decline_rate * 336)
            
        else:  # stable
            predicted_1h = current_usage
            predicted_6h = current_usage
            predicted_24h = current_usage
            predicted_7d = current_usage
        
        # Calculate confidence based on trend consistency
        confidence = self._calculate_prediction_confidence(values, trend)
        
        # Generate recommendation
        recommendation = self._generate_prediction_recommendation(
            resource_type, current_usage, predicted_24h, trend
        )
        
        return ResourcePrediction(
            resource_type=resource_type,
            current_usage=current_usage,
            predicted_1h=predicted_1h,
            predicted_6h=predicted_6h,
            predicted_24h=predicted_24h,
            predicted_7d=predicted_7d,
            confidence=confidence,
            trend=trend,
            recommendation=recommendation
        )
    
    def _calculate_prediction_confidence(self, values: List[float], trend: str) -> float:
        """Calculate confidence in prediction based on data consistency."""
        if len(values) < 20:
            return 0.3  # Low confidence with insufficient data
        
        # Calculate variance in recent values
        recent_values = values[-20:]
        variance = statistics.variance(recent_values)
        
        # Lower variance = higher confidence
        if variance < 10:
            base_confidence = 0.9
        elif variance < 50:
            base_confidence = 0.7
        elif variance < 100:
            base_confidence = 0.5
        else:
            base_confidence = 0.3
        
        # Adjust based on trend consistency
        if trend == "stable":
            return min(0.95, base_confidence + 0.1)
        else:
            return base_confidence
    
    def _generate_prediction_recommendation(
        self,
        resource_type: str,
        current: float,
        predicted_24h: float,
        trend: str
    ) -> str:
        """Generate recommendation based on prediction."""
        if predicted_24h > 90:
            return f"Critical: {resource_type} usage predicted to exceed 90% within 24h. Immediate scaling required."
        elif predicted_24h > 80:
            return f"Warning: {resource_type} usage predicted to exceed 80% within 24h. Consider scaling soon."
        elif trend == "increasing" and predicted_24h > current + 20:
            return f"Monitor: {resource_type} usage is trending upward. Plan for potential scaling."
        elif current > 70 and trend == "stable":
            return f"Optimize: {resource_type} usage is consistently high. Consider optimization."
        else:
            return f"Normal: {resource_type} usage is within acceptable ranges."


class ResourceOptimizer:
    """
    Resource optimization and scaling recommendations.
    
    Analyzes resource usage patterns and provides intelligent
    recommendations for optimization and scaling.
    """
    
    def __init__(self, monitor: ResourceMonitor, predictor: ResourcePredictor):
        self.monitor = monitor
        self.predictor = predictor
        
        # Cost factors (relative units)
        self.cost_factors = {
            "cpu": 1.0,      # Base cost
            "memory": 0.8,   # Slightly cheaper than CPU
            "disk": 0.3,     # Much cheaper than CPU/memory
            "network": 0.1   # Cheapest
        }
    
    def analyze_bottlenecks(self) -> List[ResourceBottleneck]:
        """Analyze current resource bottlenecks."""
        bottlenecks = []
        current_metrics = self.monitor.get_current_metrics()
        
        if not current_metrics:
            return bottlenecks
        
        # CPU bottleneck analysis
        if current_metrics.cpu_percent > 80:
            severity = "critical" if current_metrics.cpu_percent > 95 else "high"
            
            bottleneck = ResourceBottleneck(
                resource_type="cpu",
                severity=severity,
                current_usage=current_metrics.cpu_percent,
                threshold=80.0,
                impact="Slow response times, request queuing, potential timeouts",
                root_causes=self._analyze_cpu_bottleneck_causes(current_metrics),
                recommendations=self._get_cpu_optimization_recommendations(),
                estimated_resolution_time="15-30 minutes with scaling, 2-4 hours with optimization"
            )
            bottlenecks.append(bottleneck)
        
        # Memory bottleneck analysis
        if current_metrics.memory_percent > 85:
            severity = "critical" if current_metrics.memory_percent > 95 else "high"
            
            bottleneck = ResourceBottleneck(
                resource_type="memory",
                severity=severity,
                current_usage=current_metrics.memory_percent,
                threshold=85.0,
                impact="Memory pressure, potential swapping, application instability",
                root_causes=self._analyze_memory_bottleneck_causes(current_metrics),
                recommendations=self._get_memory_optimization_recommendations(),
                estimated_resolution_time="10-20 minutes with scaling, 1-3 hours with optimization"
            )
            bottlenecks.append(bottleneck)
        
        # Disk bottleneck analysis
        if current_metrics.disk_percent > 90:
            severity = "critical" if current_metrics.disk_percent > 95 else "high"
            
            bottleneck = ResourceBottleneck(
                resource_type="disk",
                severity=severity,
                current_usage=current_metrics.disk_percent,
                threshold=90.0,
                impact="Storage full, application failures, data loss risk",
                root_causes=self._analyze_disk_bottleneck_causes(current_metrics),
                recommendations=self._get_disk_optimization_recommendations(),
                estimated_resolution_time="5-15 minutes with cleanup, 30-60 minutes with scaling"
            )
            bottlenecks.append(bottleneck)
        
        return bottlenecks
    
    def _analyze_cpu_bottleneck_causes(self, metrics: ResourceMetrics) -> List[str]:
        """Analyze potential CPU bottleneck causes."""
        causes = []
        
        if metrics.process_count > 200:
            causes.append("High number of processes running")
        
        if metrics.load_average and metrics.load_average[0] > psutil.cpu_count():
            causes.append("System load exceeds CPU core count")
        
        causes.extend([
            "CPU-intensive operations or algorithms",
            "Inefficient database queries causing high CPU usage",
            "Insufficient CPU resources for current workload",
            "Background processes consuming CPU cycles"
        ])
        
        return causes
    
    def _analyze_memory_bottleneck_causes(self, metrics: ResourceMetrics) -> List[str]:
        """Analyze potential memory bottleneck causes."""
        causes = []
        
        if metrics.memory_available_gb < 1.0:
            causes.append("Very low available memory")
        
        causes.extend([
            "Memory leaks in application code",
            "Large datasets loaded into memory",
            "Insufficient memory allocation for workload",
            "Memory-intensive operations without proper cleanup",
            "Caching strategies using too much memory"
        ])
        
        return causes
    
    def _analyze_disk_bottleneck_causes(self, metrics: ResourceMetrics) -> List[str]:
        """Analyze potential disk bottleneck causes."""
        causes = []
        
        if metrics.disk_free_gb < 5.0:
            causes.append("Very low free disk space")
        
        causes.extend([
            "Log files growing without rotation",
            "Temporary files not being cleaned up",
            "Database files growing rapidly",
            "Backup files consuming space",
            "Insufficient disk allocation for data growth"
        ])
        
        return causes
    
    def _get_cpu_optimization_recommendations(self) -> List[str]:
        """Get CPU optimization recommendations."""
        return [
            "Scale up CPU resources (add more cores or faster processors)",
            "Optimize CPU-intensive algorithms and operations",
            "Implement caching to reduce computational overhead",
            "Use asynchronous processing for I/O-bound operations",
            "Profile application to identify CPU hotspots",
            "Consider horizontal scaling to distribute load",
            "Optimize database queries to reduce CPU usage",
            "Implement request queuing and rate limiting"
        ]
    
    def _get_memory_optimization_recommendations(self) -> List[str]:
        """Get memory optimization recommendations."""
        return [
            "Scale up memory resources (add more RAM)",
            "Implement memory profiling to identify leaks",
            "Optimize data structures and algorithms",
            "Implement proper caching strategies with TTL",
            "Use streaming for large dataset processing",
            "Implement garbage collection tuning",
            "Consider memory-mapped files for large data",
            "Optimize object lifecycle management"
        ]
    
    def _get_disk_optimization_recommendations(self) -> List[str]:
        """Get disk optimization recommendations."""
        return [
            "Clean up temporary and log files",
            "Implement log rotation policies",
            "Archive or compress old data",
            "Scale up disk storage capacity",
            "Implement data lifecycle management",
            "Use external storage for backups",
            "Optimize database storage efficiency",
            "Monitor and alert on disk usage growth"
        ]
    
    def generate_scaling_recommendations(self) -> List[ScalingRecommendation]:
        """Generate intelligent scaling recommendations."""
        recommendations = []
        
        # Get predictions for key resources
        cpu_prediction = self.predictor.predict_resource_usage("cpu")
        memory_prediction = self.predictor.predict_resource_usage("memory")
        disk_prediction = self.predictor.predict_resource_usage("disk")
        
        # CPU scaling recommendations
        if cpu_prediction:
            cpu_rec = self._generate_cpu_scaling_recommendation(cpu_prediction)
            if cpu_rec:
                recommendations.append(cpu_rec)
        
        # Memory scaling recommendations
        if memory_prediction:
            memory_rec = self._generate_memory_scaling_recommendation(memory_prediction)
            if memory_rec:
                recommendations.append(memory_rec)
        
        # Disk scaling recommendations
        if disk_prediction:
            disk_rec = self._generate_disk_scaling_recommendation(disk_prediction)
            if disk_rec:
                recommendations.append(disk_rec)
        
        return recommendations
    
    def _generate_cpu_scaling_recommendation(self, prediction: ResourcePrediction) -> Optional[ScalingRecommendation]:
        """Generate CPU scaling recommendation."""
        current_cores = psutil.cpu_count()
        
        if prediction.predicted_24h > 85:
            # Recommend scaling up
            scaling_factor = 1.5 if prediction.predicted_24h > 95 else 1.25
            recommended_cores = int(current_cores * scaling_factor)
            
            return ScalingRecommendation(
                resource_type="cpu",
                current_allocation=current_cores,
                recommended_allocation=recommended_cores,
                scaling_factor=scaling_factor,
                reason=f"CPU usage predicted to reach {prediction.predicted_24h:.1f}% within 24h",
                priority="critical" if prediction.predicted_24h > 95 else "high",
                estimated_cost_impact=self.cost_factors["cpu"] * (scaling_factor - 1) * 100,
                estimated_performance_impact="20-40% improvement in response times"
            )
        
        elif prediction.current_usage < 30 and prediction.trend == "decreasing":
            # Recommend scaling down
            scaling_factor = 0.8
            recommended_cores = max(2, int(current_cores * scaling_factor))
            
            return ScalingRecommendation(
                resource_type="cpu",
                current_allocation=current_cores,
                recommended_allocation=recommended_cores,
                scaling_factor=scaling_factor,
                reason=f"CPU usage is low ({prediction.current_usage:.1f}%) and decreasing",
                priority="low",
                estimated_cost_impact=-self.cost_factors["cpu"] * (1 - scaling_factor) * 100,
                estimated_performance_impact="Minimal impact on performance"
            )
        
        return None
    
    def _generate_memory_scaling_recommendation(self, prediction: ResourcePrediction) -> Optional[ScalingRecommendation]:
        """Generate memory scaling recommendation."""
        current_metrics = self.monitor.get_current_metrics()
        if not current_metrics:
            return None
        
        current_memory_gb = current_metrics.memory_used_gb + current_metrics.memory_available_gb
        
        if prediction.predicted_24h > 90:
            # Recommend scaling up
            scaling_factor = 1.5 if prediction.predicted_24h > 95 else 1.3
            recommended_memory = current_memory_gb * scaling_factor
            
            return ScalingRecommendation(
                resource_type="memory",
                current_allocation=current_memory_gb,
                recommended_allocation=recommended_memory,
                scaling_factor=scaling_factor,
                reason=f"Memory usage predicted to reach {prediction.predicted_24h:.1f}% within 24h",
                priority="critical" if prediction.predicted_24h > 95 else "high",
                estimated_cost_impact=self.cost_factors["memory"] * (scaling_factor - 1) * 100,
                estimated_performance_impact="Eliminate memory pressure and improve stability"
            )
        
        elif prediction.current_usage < 40 and prediction.trend == "stable":
            # Recommend scaling down
            scaling_factor = 0.8
            recommended_memory = current_memory_gb * scaling_factor
            
            return ScalingRecommendation(
                resource_type="memory",
                current_allocation=current_memory_gb,
                recommended_allocation=recommended_memory,
                scaling_factor=scaling_factor,
                reason=f"Memory usage is consistently low ({prediction.current_usage:.1f}%)",
                priority="low",
                estimated_cost_impact=-self.cost_factors["memory"] * (1 - scaling_factor) * 100,
                estimated_performance_impact="No significant impact on performance"
            )
        
        return None
    
    def _generate_disk_scaling_recommendation(self, prediction: ResourcePrediction) -> Optional[ScalingRecommendation]:
        """Generate disk scaling recommendation."""
        current_metrics = self.monitor.get_current_metrics()
        if not current_metrics:
            return None
        
        current_disk_gb = current_metrics.disk_total_gb
        
        if prediction.predicted_7d > 85:  # Use 7-day prediction for disk
            # Recommend scaling up
            scaling_factor = 1.5 if prediction.predicted_7d > 95 else 1.3
            recommended_disk = current_disk_gb * scaling_factor
            
            return ScalingRecommendation(
                resource_type="disk",
                current_allocation=current_disk_gb,
                recommended_allocation=recommended_disk,
                scaling_factor=scaling_factor,
                reason=f"Disk usage predicted to reach {prediction.predicted_7d:.1f}% within 7 days",
                priority="high" if prediction.predicted_7d > 95 else "medium",
                estimated_cost_impact=self.cost_factors["disk"] * (scaling_factor - 1) * 100,
                estimated_performance_impact="Prevent storage full conditions"
            )
        
        return None
    
    def get_cost_optimization_analysis(self) -> Dict[str, Any]:
        """Analyze cost optimization opportunities."""
        current_metrics = self.monitor.get_current_metrics()
        statistics = self.monitor.get_resource_statistics(hours=168)  # 1 week
        
        if not current_metrics or "error" in statistics:
            return {"error": "Insufficient data for cost analysis"}
        
        opportunities = []
        total_potential_savings = 0
        
        # CPU cost optimization
        if statistics["cpu"]["average"] < 30 and statistics["cpu"]["p95"] < 60:
            cpu_savings = self.cost_factors["cpu"] * 20  # 20% savings
            opportunities.append({
                "resource": "cpu",
                "opportunity": "Downsize CPU allocation",
                "current_utilization": statistics["cpu"]["average"],
                "potential_savings_percent": 20,
                "estimated_cost_savings": cpu_savings,
                "risk": "low",
                "recommendation": "Reduce CPU allocation by 20% during low-traffic periods"
            })
            total_potential_savings += cpu_savings
        
        # Memory cost optimization
        if statistics["memory"]["average"] < 50 and statistics["memory"]["p95"] < 70:
            memory_savings = self.cost_factors["memory"] * 15  # 15% savings
            opportunities.append({
                "resource": "memory",
                "opportunity": "Optimize memory allocation",
                "current_utilization": statistics["memory"]["average"],
                "potential_savings_percent": 15,
                "estimated_cost_savings": memory_savings,
                "risk": "medium",
                "recommendation": "Implement memory optimization and reduce allocation by 15%"
            })
            total_potential_savings += memory_savings
        
        # Disk cost optimization
        if current_metrics.disk_percent < 60:
            disk_savings = self.cost_factors["disk"] * 10  # 10% savings
            opportunities.append({
                "resource": "disk",
                "opportunity": "Implement data lifecycle management",
                "current_utilization": current_metrics.disk_percent,
                "potential_savings_percent": 10,
                "estimated_cost_savings": disk_savings,
                "risk": "low",
                "recommendation": "Archive old data and implement automated cleanup"
            })
            total_potential_savings += disk_savings
        
        return {
            "analysis_period": "7 days",
            "total_opportunities": len(opportunities),
            "total_potential_savings": total_potential_savings,
            "opportunities": opportunities,
            "recommendations": [
                "Implement auto-scaling based on demand patterns",
                "Use reserved instances for predictable workloads",
                "Implement resource tagging for cost tracking",
                "Regular review of resource utilization patterns"
            ]
        }


# Global resource management instances
resource_monitor = ResourceMonitor()
resource_predictor = ResourcePredictor(resource_monitor)
resource_optimizer = ResourceOptimizer(resource_monitor, resource_predictor)