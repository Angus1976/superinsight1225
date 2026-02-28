"""
Performance Metrics Collection and Analysis Module.

This module provides utilities for collecting, analyzing, and reporting
performance metrics from various test sources.

**Validates: Requirements 5.3, 5.4, 5.5, 13.2, 13.3**
**Validates: Properties 14, 15, 16**
"""

import json
import time
import statistics
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from contextlib import contextmanager


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class EndpointMetrics:
    """Metrics for a single API endpoint."""
    endpoint: str
    method: str
    request_count: int = 0
    error_count: int = 0
    response_times: List[float] = field(default_factory=list)
    
    @property
    def p50(self) -> float:
        if not self.response_times:
            return 0.0
        return statistics.median(self.response_times)
    
    @property
    def p95(self) -> float:
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]
    
    @property
    def p99(self) -> float:
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[min(idx, len(sorted_times) - 1)]
    
    @property
    def avg(self) -> float:
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times)
    
    @property
    def min(self) -> float:
        if not self.response_times:
            return 0.0
        return min(self.response_times)
    
    @property
    def max(self) -> float:
        if not self.response_times:
            return 0.0
        return max(self.response_times)
    
    @property
    def stddev(self) -> float:
        if len(self.response_times) < 2:
            return 0.0
        return statistics.stdev(self.response_times)
    
    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count
    
    @property
    def throughput(self) -> float:
        """Requests per second."""
        if not self.response_times:
            return 0.0
        return self.request_count / sum(self.response_times) * 1000


@dataclass
class DatabaseMetrics:
    """Metrics for database operations."""
    query_name: str
    query_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = 0.0
    max_time_ms: float = 0.0
    
    @property
    def avg_time_ms(self) -> float:
        if self.query_count == 0:
            return 0.0
        return self.total_time_ms / self.query_count
    
    @property
    def p95_time_ms(self) -> float:
        # Placeholder - would need actual distribution
        return self.avg_time_ms * 1.5


@dataclass
class PerformanceReport:
    """Complete performance test report."""
    timestamp: str
    duration_seconds: float
    total_requests: int
    total_errors: int
    endpoints: Dict[str, EndpointMetrics]
    database_metrics: Dict[str, DatabaseMetrics] = field(default_factory=dict)
    threshold_violations: List[str] = field(default_factory=list)
    baseline_comparison: Optional[Dict] = None
    
    @property
    def overall_error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_errors / self.total_requests
    
    @property
    def overall_throughput(self) -> float:
        if self.duration_seconds == 0:
            return 0.0
        return self.total_requests / self.duration_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "overall_error_rate": self.overall_error_rate,
            "overall_throughput": self.overall_throughput,
            "endpoints": {
                key: {
                    "endpoint": metrics.endpoint,
                    "method": metrics.method,
                    "request_count": metrics.request_count,
                    "error_count": metrics.error_count,
                    "p50_ms": round(metrics.p50, 2),
                    "p95_ms": round(metrics.p95, 2),
                    "p99_ms": round(metrics.p99, 2),
                    "avg_ms": round(metrics.avg, 2),
                    "min_ms": round(metrics.min, 2),
                    "max_ms": round(metrics.max, 2),
                    "stddev_ms": round(metrics.stddev, 2),
                    "error_rate": round(metrics.error_rate, 4),
                    "throughput_rps": round(metrics.throughput, 2),
                }
                for key, metrics in self.endpoints.items()
            },
            "database_metrics": {
                key: {
                    "query_name": metrics.query_name,
                    "query_count": metrics.query_count,
                    "total_time_ms": round(metrics.total_time_ms, 2),
                    "avg_time_ms": round(metrics.avg_time_ms, 2),
                    "min_time_ms": round(metrics.min_time_ms, 2),
                    "max_time_ms": round(metrics.max_time_ms, 2),
                }
                for key, metrics in self.database_metrics.items()
            },
            "threshold_violations": self.threshold_violations,
            "baseline_comparison": self.baseline_comparison,
        }


# =============================================================================
# Metrics Collector
# =============================================================================

class MetricsCollector:
    """
    Centralized metrics collection for performance tests.
    
    Collects metrics from multiple sources including:
    - HTTP endpoint requests
    - Database queries
    - Custom timers
    """
    
    def __init__(self):
        self.endpoints: Dict[str, EndpointMetrics] = {}
        self.database_queries: Dict[str, DatabaseMetrics] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._active_timers: Dict[str, float] = {}
    
    def start(self):
        """Start metrics collection."""
        self.start_time = datetime.utcnow()
    
    def stop(self):
        """Stop metrics collection."""
        self.end_time = datetime.utcnow()
    
    @property
    def duration(self) -> float:
        """Get test duration in seconds."""
        if not self.start_time or not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()
    
    def record_request(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int
    ):
        """Record an HTTP request."""
        key = f"{method}:{endpoint}"
        
        if key not in self.endpoints:
            self.endpoints[key] = EndpointMetrics(endpoint=endpoint, method=method)
        
        metrics = self.endpoints[key]
        metrics.request_count += 1
        metrics.response_times.append(response_time)
        
        if status_code >= 400:
            metrics.error_count += 1
    
    def record_database_query(
        self,
        query_name: str,
        query_time_ms: float
    ):
        """Record a database query."""
        if query_name not in self.database_queries:
            self.database_queries[query_name] = DatabaseMetrics(query_name=query_name)
        
        metrics = self.database_queries[query_name]
        metrics.query_count += 1
        metrics.total_time_ms += query_time_ms
        
        if metrics.query_count == 1:
            metrics.min_time_ms = query_time_ms
            metrics.max_time_ms = query_time_ms
        else:
            metrics.min_time_ms = min(metrics.min_time_ms, query_time_ms)
            metrics.max_time_ms = max(metrics.max_time_ms, query_time_ms)
    
    @contextmanager
    def timer(self, name: str):
        """Context manager for timing operations."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            self.record_database_query(name, elapsed)
    
    def start_timer(self, name: str):
        """Start a named timer."""
        self._active_timers[name] = time.perf_counter()
    
    def stop_timer(self, name: str) -> float:
        """Stop a named timer and return elapsed time in ms."""
        if name not in self._active_timers:
            return 0.0
        
        elapsed = (time.perf_counter() - self._active_timers[name]) * 1000
        del self._active_timers[name]
        self.record_database_query(name, elapsed)
        return elapsed
    
    def get_report(self) -> PerformanceReport:
        """Generate a complete performance report."""
        total_requests = sum(m.request_count for m in self.endpoints.values())
        total_errors = sum(m.error_count for m in self.endpoints.values())
        
        return PerformanceReport(
            timestamp=self.start_time.isoformat() if self.start_time else datetime.utcnow().isoformat(),
            duration_seconds=self.duration,
            total_requests=total_requests,
            total_errors=total_errors,
            endpoints=self.endpoints,
            database_metrics=self.database_queries,
        )
    
    def check_thresholds(
        self,
        p95_threshold_ms: float = 500,
        error_rate_threshold: float = 0.01
    ) -> List[str]:
        """Check if metrics exceed defined thresholds."""
        violations = []
        
        for key, metrics in self.endpoints.items():
            if metrics.p95 > p95_threshold_ms:
                violations.append(
                    f"{key}: P95={metrics.p95:.2f}ms exceeds threshold {p95_threshold_ms}ms"
                )
            if metrics.error_rate > error_rate_threshold:
                violations.append(
                    f"{key}: Error rate={metrics.error_rate:.2%} exceeds threshold {error_rate_threshold:.2%}"
                )
        
        return violations
    
    def save_baseline(self, filepath: str = "tests/performance/baseline.json"):
        """Save current metrics as baseline."""
        report = self.get_report()
        
        baseline = {
            "timestamp": report.timestamp,
            "endpoints": {},
            "database_metrics": {}
        }
        
        for key, metrics in report.endpoints.items():
            baseline["endpoints"][key] = {
                "p50_ms": metrics.p50,
                "p95_ms": metrics.p95,
                "p99_ms": metrics.p99,
                "avg_ms": metrics.avg,
            }
        
        for key, metrics in report.database_metrics.items():
            baseline["database_metrics"][key] = {
                "avg_time_ms": metrics.avg_time_ms,
                "min_time_ms": metrics.min_time_ms,
                "max_time_ms": metrics.max_time_ms,
            }
        
        # Create directory if needed
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        return filepath
    
    def compare_with_baseline(
        self,
        baseline_path: str = "tests/performance/baseline.json",
        degradation_threshold: float = 0.20
    ) -> Dict[str, Any]:
        """Compare current metrics with baseline."""
        try:
            with open(baseline_path, 'r') as f:
                baseline = json.load(f)
        except FileNotFoundError:
            return {"error": "Baseline not found"}
        
        comparison = {
            "timestamp": datetime.utcnow().isoformat(),
            "degradation_threshold": degradation_threshold,
            "endpoint_comparison": [],
            "database_comparison": [],
        }
        
        for key, metrics in self.endpoints.items():
            if key in baseline["endpoints"]:
                base = baseline["endpoints"][key]
                p95_degradation = (metrics.p95 - base["p95_ms"]) / base["p95_ms"] if base["p95_ms"] > 0 else 0
                
                comparison["endpoint_comparison"].append({
                    "endpoint": key,
                    "baseline_p95_ms": round(base["p95_ms"], 2),
                    "current_p95_ms": round(metrics.p95, 2),
                    "degradation_percent": round(p95_degradation * 100, 2),
                    "passed": p95_degradation <= degradation_threshold,
                })
        
        for key, metrics in self.database_queries.items():
            if key in baseline["database_metrics"]:
                base = baseline["database_metrics"][key]
                avg_degradation = (metrics.avg_time_ms - base["avg_time_ms"]) / base["avg_time_ms"] if base["avg_time_ms"] > 0 else 0
                
                comparison["database_comparison"].append({
                    "query": key,
                    "baseline_avg_ms": round(base["avg_time_ms"], 2),
                    "current_avg_ms": round(metrics.avg_time_ms, 2),
                    "degradation_percent": round(avg_degradation * 100, 2),
                    "passed": avg_degradation <= degradation_threshold,
                })
        
        return comparison
    
    def save_report(self, filepath: str = None) -> str:
        """Save performance report to file."""
        if filepath is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filepath = f"tests/performance/report_{timestamp}.json"
        
        report = self.get_report()
        report.threshold_violations = self.check_thresholds()
        report.baseline_comparison = self.compare_with_baseline()
        
        # Create directory if needed
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        return filepath
    
    def reset(self):
        """Reset all metrics."""
        self.endpoints = {}
        self.database_queries = {}
        self.start_time = None
        self.end_time = None
        self._active_timers = {}


# Global metrics collector instance
metrics_collector = MetricsCollector()


# =============================================================================
# Frontend Page Load Metrics
# =============================================================================

@dataclass
class PageLoadMetrics:
    """Metrics for frontend page load performance."""
    page_name: str
    load_time_ms: float = 0.0
    dom_content_loaded_ms: float = 0.0
    first_contentful_paint_ms: float = 0.0
    largest_contentful_paint_ms: float = 0.0
    time_to_interactive_ms: float = 0.0
    
    @property
    def is_healthy(self) -> bool:
        """Check if page load metrics are within acceptable range."""
        return (
            self.load_time_ms < 3000 and  # < 3s total load
            self.largest_contentful_paint_ms < 2500  # < 2.5s LCP
        )


class FrontendMetricsCollector:
    """Collects frontend page load metrics."""
    
    def __init__(self):
        self.pages: Dict[str, PageLoadMetrics] = {}
    
    def record_page_load(
        self,
        page_name: str,
        load_time_ms: float,
        dom_content_loaded_ms: float = 0,
        first_contentful_paint_ms: float = 0,
        largest_contentful_paint_ms: float = 0,
        time_to_interactive_ms: float = 0
    ):
        """Record page load metrics."""
        self.pages[page_name] = PageLoadMetrics(
            page_name=page_name,
            load_time_ms=load_time_ms,
            dom_content_loaded_ms=dom_content_loaded_ms,
            first_contentful_paint_ms=first_contentful_paint_ms,
            largest_contentful_paint_ms=largest_contentful_paint_ms,
            time_to_interactive_ms=time_to_interactive_ms,
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all page load metrics."""
        pages = list(self.pages.values())
        
        if not pages:
            return {"error": "No page load data recorded"}
        
        return {
            "total_pages": len(pages),
            "healthy_pages": sum(1 for p in pages if p.is_healthy),
            "pages": {
                name: {
                    "load_time_ms": round(m.load_time_ms, 2),
                    "lcp_ms": round(m.largest_contentful_paint_ms, 2),
                    "is_healthy": m.is_healthy,
                }
                for name, m in self.pages.items()
            }
        }


# =============================================================================
# Threshold Validation
# =============================================================================

class PerformanceThresholds:
    """Performance threshold definitions and validation."""
    
    # Critical endpoint thresholds (P95 in ms)
    CRITICAL_THRESHOLDS = {
        "GET /health": 100,
        "POST /api/v1/auth/login": 200,
        "GET /api/v1/tasks": 300,
        "POST /api/v1/tasks": 500,
        "GET /api/v1/annotations": 300,
        "POST /api/v1/annotations": 500,
        "GET /api/v1/exports": 300,
        "POST /api/v1/exports": 500,
    }
    
    # General thresholds
    P95_THRESHOLD_MS = 500
    P99_THRESHOLD_MS = 1000
    ERROR_RATE_THRESHOLD = 0.01  # 1%
    THROUGHPUT_MIN_RPS = 50
    
    @classmethod
    def validate_endpoint(
        cls,
        endpoint: str,
        p95_ms: float,
        error_rate: float = 0
    ) -> tuple[bool, List[str]]:
        """
        Validate an endpoint against thresholds.
        
        Returns:
            Tuple of (passed, list of violations)
        """
        violations = []
        
        # Check specific threshold if defined
        if endpoint in cls.CRITICAL_THRESHOLDS:
            threshold = cls.CRITICAL_THRESHOLDS[endpoint]
            if p95_ms > threshold:
                violations.append(
                    f"{endpoint}: P95={p95_ms:.2f}ms exceeds threshold {threshold}ms"
                )
        else:
            # Use general threshold
            if p95_ms > cls.P95_THRESHOLD_MS:
                violations.append(
                    f"{endpoint}: P95={p95_ms:.2f}ms exceeds general threshold {cls.P95_THRESHOLD_MS}ms"
                )
        
        if error_rate > cls.ERROR_RATE_THRESHOLD:
            violations.append(
                f"{endpoint}: Error rate={error_rate:.2%} exceeds threshold {cls.ERROR_RATE_THRESHOLD:.2%}"
            )
        
        return len(violations) == 0, violations
    
    @classmethod
    def validate_report(cls, report: PerformanceReport) -> tuple[bool, List[str]]:
        """Validate a complete performance report."""
        all_violations = []
        
        for key, metrics in report.endpoints.items():
            _, violations = cls.validate_endpoint(
                f"{metrics.method} {metrics.endpoint}",
                metrics.p95,
                metrics.error_rate
            )
            all_violations.extend(violations)
        
        return len(all_violations) == 0, all_violations


# =============================================================================
# Utility Functions
# =============================================================================

def format_metrics_summary(metrics: MetricsCollector) -> str:
    """Format metrics collector as a human-readable summary."""
    report = metrics.get_report()
    
    lines = [
        "=" * 60,
        "PERFORMANCE TEST SUMMARY",
        "=" * 60,
        f"Timestamp: {report.timestamp}",
        f"Duration: {report.duration_seconds:.2f}s",
        f"Total Requests: {report.total_requests}",
        f"Total Errors: {report.total_errors}",
        f"Overall Error Rate: {report.overall_error_rate:.2%}",
        f"Overall Throughput: {report.overall_throughput:.2f} req/s",
        "-" * 60,
        "Endpoint Metrics:",
    ]
    
    for key, m in report.endpoints.items():
        status = "✓" if m.p95 < PerformanceThresholds.P95_THRESHOLD_MS else "✗"
        lines.append(
            f"  {status} {key}: "
            f"P50={m.p50:.1f}ms, P95={m.p95:.1f}ms, P99={m.p99:.1f}ms, "
            f"Errors={m.error_count}"
        )
    
    if report.database_metrics:
        lines.append("-" * 60)
        lines.append("Database Metrics:")
        for key, m in report.database_metrics.items():
            lines.append(
                f"  {key}: {m.query_count} queries, "
                f"avg={m.avg_time_ms:.2f}ms, "
                f"max={m.max_time_ms:.2f}ms"
            )
    
    violations = report.threshold_violations
    if violations:
        lines.extend(["-" * 60, "THRESHOLD VIOLATIONS:"])
        for v in violations:
            lines.append(f"  ✗ {v}")
    else:
        lines.extend(["-" * 60, "All thresholds passed!"])
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


# Export for use in other modules
__all__ = [
    "MetricsCollector",
    "FrontendMetricsCollector",
    "PerformanceThresholds",
    "PerformanceReport",
    "EndpointMetrics",
    "DatabaseMetrics",
    "PageLoadMetrics",
    "format_metrics_summary",
    "metrics_collector",
]