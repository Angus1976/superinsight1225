"""
Sync Analytics and Reporting Module.

Provides comprehensive analytics for sync operations:
- Performance trend analysis
- Efficiency metrics
- Anomaly detection
- Report generation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class TrendDirection(str, Enum):
    """Direction of a metric trend."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    UNKNOWN = "unknown"


class ReportPeriod(str, Enum):
    """Report time periods."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class SyncStatistics:
    """Statistics for sync operations."""
    total_jobs: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    total_records: int = 0
    total_bytes: int = 0
    total_duration_seconds: float = 0.0
    avg_throughput: float = 0.0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_jobs": self.total_jobs,
            "successful_jobs": self.successful_jobs,
            "failed_jobs": self.failed_jobs,
            "success_rate": self.successful_jobs / self.total_jobs if self.total_jobs > 0 else 0,
            "total_records": self.total_records,
            "total_bytes": self.total_bytes,
            "total_duration_seconds": self.total_duration_seconds,
            "avg_throughput": self.avg_throughput,
            "avg_latency_ms": self.avg_latency_ms,
            "error_rate": self.error_rate
        }


@dataclass
class TrendAnalysis:
    """Analysis of metric trends."""
    metric_name: str
    direction: TrendDirection
    change_percent: float
    current_value: float
    previous_value: float
    samples: int
    confidence: float  # 0-1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "direction": self.direction.value,
            "change_percent": self.change_percent,
            "current_value": self.current_value,
            "previous_value": self.previous_value,
            "samples": self.samples,
            "confidence": self.confidence
        }


@dataclass
class AnomalyDetection:
    """Detected anomaly in sync metrics."""
    metric_name: str
    timestamp: datetime
    value: float
    expected_range: Tuple[float, float]
    severity: str  # low, medium, high
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "expected_range": list(self.expected_range),
            "severity": self.severity,
            "description": self.description
        }


class SyncAnalyzer:
    """
    Comprehensive analytics for sync operations.
    
    Provides trend analysis, anomaly detection, and report generation.
    """

    def __init__(self):
        # Historical data storage
        self.job_history: List[Dict[str, Any]] = []
        self.metric_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.max_history_size = 10000
        
        # Anomaly detection parameters
        self.anomaly_std_threshold = 2.5  # Standard deviations for anomaly
        self.min_samples_for_anomaly = 30

    def record_job_completion(self, job_data: Dict[str, Any]):
        """Record a completed sync job for analytics."""
        job_data["recorded_at"] = datetime.now().isoformat()
        self.job_history.append(job_data)
        
        # Trim history if needed
        if len(self.job_history) > self.max_history_size:
            self.job_history = self.job_history[-self.max_history_size:]
        
        # Extract and record metrics
        if "throughput" in job_data:
            self.record_metric("throughput", job_data["throughput"])
        if "duration_seconds" in job_data:
            self.record_metric("duration", job_data["duration_seconds"])
        if "success_rate" in job_data:
            self.record_metric("success_rate", job_data["success_rate"])

    def record_metric(self, metric_name: str, value: float):
        """Record a metric value."""
        self.metric_history[metric_name].append((datetime.now(), value))
        
        # Trim history
        if len(self.metric_history[metric_name]) > self.max_history_size:
            self.metric_history[metric_name] = self.metric_history[metric_name][-self.max_history_size:]

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        source_id: Optional[str] = None
    ) -> SyncStatistics:
        """Calculate statistics for sync operations."""
        # Filter jobs
        filtered_jobs = self.job_history
        
        if start_time:
            filtered_jobs = [
                j for j in filtered_jobs
                if datetime.fromisoformat(j.get("started_at", j.get("recorded_at", ""))) >= start_time
            ]
        
        if end_time:
            filtered_jobs = [
                j for j in filtered_jobs
                if datetime.fromisoformat(j.get("started_at", j.get("recorded_at", ""))) <= end_time
            ]
        
        if source_id:
            filtered_jobs = [j for j in filtered_jobs if j.get("source_id") == source_id]
        
        if not filtered_jobs:
            return SyncStatistics()
        
        # Calculate statistics
        stats = SyncStatistics(
            total_jobs=len(filtered_jobs),
            successful_jobs=len([j for j in filtered_jobs if j.get("status") == "completed"]),
            failed_jobs=len([j for j in filtered_jobs if j.get("status") == "failed"]),
            total_records=sum(j.get("records_processed", 0) for j in filtered_jobs),
            total_bytes=sum(j.get("bytes_transferred", 0) for j in filtered_jobs),
            total_duration_seconds=sum(j.get("duration_seconds", 0) for j in filtered_jobs)
        )
        
        # Calculate averages
        throughputs = [j.get("throughput", 0) for j in filtered_jobs if j.get("throughput")]
        if throughputs:
            stats.avg_throughput = statistics.mean(throughputs)
        
        latencies = [j.get("latency_ms", 0) for j in filtered_jobs if j.get("latency_ms")]
        if latencies:
            stats.avg_latency_ms = statistics.mean(latencies)
        
        if stats.total_jobs > 0:
            stats.error_rate = stats.failed_jobs / stats.total_jobs
        
        return stats

    def analyze_trend(
        self,
        metric_name: str,
        window_hours: int = 24
    ) -> TrendAnalysis:
        """Analyze trend for a specific metric."""
        history = self.metric_history.get(metric_name, [])
        
        if len(history) < 10:
            return TrendAnalysis(
                metric_name=metric_name,
                direction=TrendDirection.UNKNOWN,
                change_percent=0,
                current_value=history[-1][1] if history else 0,
                previous_value=0,
                samples=len(history),
                confidence=0
            )
        
        # Split into current and previous periods
        now = datetime.now()
        cutoff = now - timedelta(hours=window_hours)
        mid_point = now - timedelta(hours=window_hours / 2)
        
        current_values = [v for t, v in history if t >= mid_point]
        previous_values = [v for t, v in history if cutoff <= t < mid_point]
        
        if not current_values or not previous_values:
            return TrendAnalysis(
                metric_name=metric_name,
                direction=TrendDirection.UNKNOWN,
                change_percent=0,
                current_value=current_values[-1] if current_values else 0,
                previous_value=previous_values[-1] if previous_values else 0,
                samples=len(history),
                confidence=0
            )
        
        current_avg = statistics.mean(current_values)
        previous_avg = statistics.mean(previous_values)
        
        # Calculate change
        if previous_avg != 0:
            change_percent = ((current_avg - previous_avg) / previous_avg) * 100
        else:
            change_percent = 0
        
        # Determine direction
        threshold = 5  # 5% change threshold
        if change_percent > threshold:
            direction = TrendDirection.IMPROVING if metric_name in ["throughput", "success_rate"] else TrendDirection.DEGRADING
        elif change_percent < -threshold:
            direction = TrendDirection.DEGRADING if metric_name in ["throughput", "success_rate"] else TrendDirection.IMPROVING
        else:
            direction = TrendDirection.STABLE
        
        # Calculate confidence based on sample size
        confidence = min(1.0, len(history) / 100)
        
        return TrendAnalysis(
            metric_name=metric_name,
            direction=direction,
            change_percent=change_percent,
            current_value=current_avg,
            previous_value=previous_avg,
            samples=len(history),
            confidence=confidence
        )

    def detect_anomalies(
        self,
        metric_name: str,
        window_hours: int = 24
    ) -> List[AnomalyDetection]:
        """Detect anomalies in metric values."""
        history = self.metric_history.get(metric_name, [])
        
        if len(history) < self.min_samples_for_anomaly:
            return []
        
        # Calculate baseline statistics
        values = [v for _, v in history]
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0
        
        if std == 0:
            return []
        
        # Detect anomalies in recent window
        now = datetime.now()
        cutoff = now - timedelta(hours=window_hours)
        
        anomalies = []
        expected_min = mean - (self.anomaly_std_threshold * std)
        expected_max = mean + (self.anomaly_std_threshold * std)
        
        for timestamp, value in history:
            if timestamp < cutoff:
                continue
            
            if value < expected_min or value > expected_max:
                # Determine severity
                deviation = abs(value - mean) / std
                if deviation > 4:
                    severity = "high"
                elif deviation > 3:
                    severity = "medium"
                else:
                    severity = "low"
                
                anomalies.append(AnomalyDetection(
                    metric_name=metric_name,
                    timestamp=timestamp,
                    value=value,
                    expected_range=(expected_min, expected_max),
                    severity=severity,
                    description=f"{metric_name} value {value:.2f} is {deviation:.1f} standard deviations from mean"
                ))
        
        return anomalies

    def generate_report(
        self,
        period: ReportPeriod = ReportPeriod.DAILY,
        source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a comprehensive sync report."""
        # Determine time range
        now = datetime.now()
        if period == ReportPeriod.HOURLY:
            start_time = now - timedelta(hours=1)
        elif period == ReportPeriod.DAILY:
            start_time = now - timedelta(days=1)
        elif period == ReportPeriod.WEEKLY:
            start_time = now - timedelta(weeks=1)
        else:  # MONTHLY
            start_time = now - timedelta(days=30)
        
        # Get statistics
        stats = self.get_statistics(start_time=start_time, source_id=source_id)
        
        # Analyze trends
        trends = {}
        for metric in ["throughput", "duration", "success_rate"]:
            trends[metric] = self.analyze_trend(metric).to_dict()
        
        # Detect anomalies
        all_anomalies = []
        for metric in self.metric_history.keys():
            anomalies = self.detect_anomalies(metric)
            all_anomalies.extend([a.to_dict() for a in anomalies])
        
        # Top sources by volume
        source_stats = defaultdict(lambda: {"jobs": 0, "records": 0, "bytes": 0})
        for job in self.job_history:
            if job.get("started_at"):
                job_time = datetime.fromisoformat(job["started_at"])
                if job_time >= start_time:
                    src = job.get("source_id", "unknown")
                    source_stats[src]["jobs"] += 1
                    source_stats[src]["records"] += job.get("records_processed", 0)
                    source_stats[src]["bytes"] += job.get("bytes_transferred", 0)
        
        top_sources = sorted(
            source_stats.items(),
            key=lambda x: x[1]["records"],
            reverse=True
        )[:10]
        
        # Error analysis
        error_counts = defaultdict(int)
        for job in self.job_history:
            if job.get("status") == "failed":
                for error in job.get("errors", []):
                    # Extract error type
                    error_type = error.split(":")[0] if ":" in error else "Unknown"
                    error_counts[error_type] += 1
        
        return {
            "report_period": period.value,
            "generated_at": now.isoformat(),
            "time_range": {
                "start": start_time.isoformat(),
                "end": now.isoformat()
            },
            "summary": stats.to_dict(),
            "trends": trends,
            "anomalies": all_anomalies[:20],  # Top 20 anomalies
            "top_sources": [
                {"source_id": src, **data}
                for src, data in top_sources
            ],
            "error_analysis": dict(error_counts),
            "recommendations": self._generate_recommendations(stats, trends, all_anomalies)
        }

    def _generate_recommendations(
        self,
        stats: SyncStatistics,
        trends: Dict[str, Dict],
        anomalies: List[Dict]
    ) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        # Check error rate
        if stats.error_rate > 0.1:
            recommendations.append(
                f"High error rate ({stats.error_rate:.1%}). Review failed jobs and error logs."
            )
        
        # Check throughput trend
        throughput_trend = trends.get("throughput", {})
        if throughput_trend.get("direction") == "degrading":
            recommendations.append(
                f"Throughput is degrading ({throughput_trend.get('change_percent', 0):.1f}% decrease). "
                "Consider scaling resources or optimizing queries."
            )
        
        # Check for anomalies
        high_severity_anomalies = [a for a in anomalies if a.get("severity") == "high"]
        if high_severity_anomalies:
            recommendations.append(
                f"Detected {len(high_severity_anomalies)} high-severity anomalies. "
                "Investigate unusual metric values."
            )
        
        # Check success rate
        if stats.total_jobs > 0:
            success_rate = stats.successful_jobs / stats.total_jobs
            if success_rate < 0.95:
                recommendations.append(
                    f"Success rate ({success_rate:.1%}) is below target (95%). "
                    "Review job configurations and data quality."
                )
        
        if not recommendations:
            recommendations.append("System is operating within normal parameters.")
        
        return recommendations

    def get_efficiency_metrics(self) -> Dict[str, Any]:
        """Calculate sync efficiency metrics."""
        if not self.job_history:
            return {
                "data_efficiency": 0,
                "time_efficiency": 0,
                "resource_utilization": 0,
                "overall_efficiency": 0
            }
        
        # Calculate metrics
        total_records = sum(j.get("records_processed", 0) for j in self.job_history)
        total_bytes = sum(j.get("bytes_transferred", 0) for j in self.job_history)
        total_duration = sum(j.get("duration_seconds", 0) for j in self.job_history)
        successful_jobs = len([j for j in self.job_history if j.get("status") == "completed"])
        
        # Data efficiency: bytes per record
        data_efficiency = total_bytes / total_records if total_records > 0 else 0
        
        # Time efficiency: records per second
        time_efficiency = total_records / total_duration if total_duration > 0 else 0
        
        # Success rate as resource utilization proxy
        resource_utilization = successful_jobs / len(self.job_history) if self.job_history else 0
        
        # Overall efficiency (normalized)
        overall_efficiency = (
            (min(time_efficiency / 1000, 1) * 0.4) +  # Normalize to 0-1
            (resource_utilization * 0.4) +
            (min(1 / (data_efficiency / 1000 + 1), 1) * 0.2)  # Lower bytes per record is better
        )
        
        return {
            "data_efficiency": {
                "bytes_per_record": data_efficiency,
                "total_bytes": total_bytes,
                "total_records": total_records
            },
            "time_efficiency": {
                "records_per_second": time_efficiency,
                "total_duration_seconds": total_duration
            },
            "resource_utilization": {
                "success_rate": resource_utilization,
                "successful_jobs": successful_jobs,
                "total_jobs": len(self.job_history)
            },
            "overall_efficiency_score": overall_efficiency
        }

    def get_source_comparison(self) -> Dict[str, Any]:
        """Compare performance across different data sources."""
        source_metrics = defaultdict(lambda: {
            "jobs": 0,
            "records": 0,
            "bytes": 0,
            "duration": 0,
            "errors": 0,
            "throughputs": []
        })
        
        for job in self.job_history:
            source = job.get("source_id", "unknown")
            source_metrics[source]["jobs"] += 1
            source_metrics[source]["records"] += job.get("records_processed", 0)
            source_metrics[source]["bytes"] += job.get("bytes_transferred", 0)
            source_metrics[source]["duration"] += job.get("duration_seconds", 0)
            
            if job.get("status") == "failed":
                source_metrics[source]["errors"] += 1
            
            if job.get("throughput"):
                source_metrics[source]["throughputs"].append(job["throughput"])
        
        # Calculate averages and rankings
        comparison = []
        for source, metrics in source_metrics.items():
            avg_throughput = (
                statistics.mean(metrics["throughputs"])
                if metrics["throughputs"] else 0
            )
            error_rate = metrics["errors"] / metrics["jobs"] if metrics["jobs"] > 0 else 0
            
            comparison.append({
                "source_id": source,
                "total_jobs": metrics["jobs"],
                "total_records": metrics["records"],
                "total_bytes": metrics["bytes"],
                "total_duration": metrics["duration"],
                "avg_throughput": avg_throughput,
                "error_rate": error_rate,
                "efficiency_score": avg_throughput * (1 - error_rate)
            })
        
        # Sort by efficiency score
        comparison.sort(key=lambda x: x["efficiency_score"], reverse=True)
        
        return {
            "sources": comparison,
            "best_performer": comparison[0]["source_id"] if comparison else None,
            "worst_performer": comparison[-1]["source_id"] if comparison else None
        }


# Global instance
sync_analyzer = SyncAnalyzer()
