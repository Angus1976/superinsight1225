"""
Application Performance Monitoring (APM) for SuperInsight Platform.

Provides comprehensive application performance monitoring including:
- Full-stack request tracing with distributed tracing support
- API response time analysis with detailed breakdown
- Database query performance monitoring with optimization suggestions
- User experience monitoring with real user metrics (RUM)
- Performance bottleneck detection and alerting
- Custom business transaction monitoring
"""

import asyncio
import logging
import time
import uuid
import threading
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import json
import statistics

from src.config.settings import settings


logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    """Distributed tracing span."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"  # ok, error, timeout
    service_name: str = "superinsight"
    
    def finish(self, status: str = "ok"):
        """Finish the span."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = status
    
    def add_tag(self, key: str, value: str):
        """Add a tag to the span."""
        self.tags[key] = value
    
    def add_log(self, message: str, level: str = "info", **kwargs):
        """Add a log entry to the span."""
        self.logs.append({
            "timestamp": time.time(),
            "level": level,
            "message": message,
            **kwargs
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "tags": self.tags,
            "logs": self.logs,
            "status": self.status,
            "service_name": self.service_name
        }


@dataclass
class APIMetrics:
    """API endpoint performance metrics."""
    endpoint: str
    method: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    error_rate: float = 0.0
    throughput: float = 0.0  # requests per second
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    def update(self, response_time: float, status_code: int):
        """Update metrics with new request data."""
        self.total_requests += 1
        self.response_times.append(response_time)
        self.status_codes[status_code] += 1
        
        if 200 <= status_code < 400:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Update response time statistics
        self.min_response_time = min(self.min_response_time, response_time)
        self.max_response_time = max(self.max_response_time, response_time)
        
        # Calculate percentiles if we have enough data
        if len(self.response_times) >= 10:
            sorted_times = sorted(self.response_times)
            self.p50_response_time = self._percentile(sorted_times, 50)
            self.p95_response_time = self._percentile(sorted_times, 95)
            self.p99_response_time = self._percentile(sorted_times, 99)
        
        # Calculate average
        self.avg_response_time = sum(self.response_times) / len(self.response_times)
        
        # Calculate error rate
        self.error_rate = self.failed_requests / self.total_requests if self.total_requests > 0 else 0
    
    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not sorted_values:
            return 0.0
        
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))


@dataclass
class DatabaseMetrics:
    """Database query performance metrics."""
    query_type: str
    table_name: Optional[str] = None
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    slow_query_count: int = 0
    slow_query_threshold: float = 1.0  # seconds
    execution_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def update(self, execution_time: float, success: bool):
        """Update metrics with new query data."""
        self.total_queries += 1
        self.execution_times.append(execution_time)
        
        if success:
            self.successful_queries += 1
        else:
            self.failed_queries += 1
        
        # Update execution time statistics
        self.min_execution_time = min(self.min_execution_time, execution_time)
        self.max_execution_time = max(self.max_execution_time, execution_time)
        
        # Calculate average
        self.avg_execution_time = sum(self.execution_times) / len(self.execution_times)
        
        # Count slow queries
        if execution_time > self.slow_query_threshold:
            self.slow_query_count += 1


@dataclass
class UserExperienceMetrics:
    """Real User Monitoring (RUM) metrics."""
    page_url: str
    user_agent: str
    page_load_time: float = 0.0
    dom_content_loaded: float = 0.0
    first_contentful_paint: float = 0.0
    largest_contentful_paint: float = 0.0
    cumulative_layout_shift: float = 0.0
    first_input_delay: float = 0.0
    time_to_interactive: float = 0.0
    bounce_rate: float = 0.0
    session_duration: float = 0.0
    error_count: int = 0
    timestamp: float = field(default_factory=time.time)


class DistributedTracer:
    """Distributed tracing system for request flow tracking."""
    
    def __init__(self):
        self.active_traces: Dict[str, List[TraceSpan]] = {}
        self.completed_traces: deque = deque(maxlen=10000)
        self._lock = threading.Lock()
        
    def start_trace(self, operation_name: str, trace_id: Optional[str] = None) -> TraceSpan:
        """Start a new trace."""
        trace_id = trace_id or str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=None,
            operation_name=operation_name,
            start_time=time.time()
        )
        
        with self._lock:
            if trace_id not in self.active_traces:
                self.active_traces[trace_id] = []
            self.active_traces[trace_id].append(span)
        
        return span
    
    def start_span(self, operation_name: str, parent_span: TraceSpan) -> TraceSpan:
        """Start a child span."""
        span_id = str(uuid.uuid4())
        
        span = TraceSpan(
            span_id=span_id,
            trace_id=parent_span.trace_id,
            parent_span_id=parent_span.span_id,
            operation_name=operation_name,
            start_time=time.time()
        )
        
        with self._lock:
            if parent_span.trace_id in self.active_traces:
                self.active_traces[parent_span.trace_id].append(span)
        
        return span
    
    def finish_span(self, span: TraceSpan, status: str = "ok"):
        """Finish a span."""
        span.finish(status)
        
        # Check if this completes the trace
        with self._lock:
            if span.trace_id in self.active_traces:
                trace_spans = self.active_traces[span.trace_id]
                
                # Check if all spans in trace are finished
                if all(s.end_time is not None for s in trace_spans):
                    # Move to completed traces
                    self.completed_traces.append(trace_spans)
                    del self.active_traces[span.trace_id]
    
    def get_trace(self, trace_id: str) -> Optional[List[TraceSpan]]:
        """Get trace by ID."""
        with self._lock:
            if trace_id in self.active_traces:
                return self.active_traces[trace_id].copy()
        
        # Search in completed traces
        for trace_spans in self.completed_traces:
            if trace_spans and trace_spans[0].trace_id == trace_id:
                return trace_spans
        
        return None
    
    def get_recent_traces(self, limit: int = 100) -> List[List[TraceSpan]]:
        """Get recent completed traces."""
        return list(self.completed_traces)[-limit:]


class APMMonitor:
    """
    Application Performance Monitoring system.
    
    Provides comprehensive monitoring of application performance including
    request tracing, API metrics, database performance, and user experience.
    """
    
    def __init__(self):
        self.tracer = DistributedTracer()
        self.api_metrics: Dict[str, APIMetrics] = {}
        self.db_metrics: Dict[str, DatabaseMetrics] = {}
        self.user_metrics: List[UserExperienceMetrics] = []
        self.business_transactions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
        # Performance thresholds
        self.slow_request_threshold = 2.0  # seconds
        self.slow_query_threshold = 1.0    # seconds
        self.error_rate_threshold = 0.05   # 5%
        
        # Alert handlers
        self.alert_handlers: List[Callable] = []
    
    def register_alert_handler(self, handler: Callable):
        """Register an alert handler."""
        self.alert_handlers.append(handler)
    
    @asynccontextmanager
    async def trace_request(self, operation_name: str, trace_id: Optional[str] = None):
        """Context manager for tracing requests."""
        span = self.tracer.start_trace(operation_name, trace_id)
        
        try:
            yield span
            self.tracer.finish_span(span, "ok")
        except Exception as e:
            span.add_log(f"Error: {str(e)}", "error")
            self.tracer.finish_span(span, "error")
            raise
    
    @asynccontextmanager
    async def trace_span(self, operation_name: str, parent_span: TraceSpan):
        """Context manager for tracing child spans."""
        span = self.tracer.start_span(operation_name, parent_span)
        
        try:
            yield span
            self.tracer.finish_span(span, "ok")
        except Exception as e:
            span.add_log(f"Error: {str(e)}", "error")
            self.tracer.finish_span(span, "error")
            raise
    
    def record_api_request(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int,
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        """Record API request metrics."""
        key = f"{method}:{endpoint}"
        
        with self._lock:
            if key not in self.api_metrics:
                self.api_metrics[key] = APIMetrics(endpoint=endpoint, method=method)
            
            self.api_metrics[key].update(response_time, status_code)
        
        # Check for performance issues
        self._check_api_performance(key, response_time, status_code)
    
    def record_database_query(
        self,
        query_type: str,
        execution_time: float,
        success: bool,
        table_name: Optional[str] = None,
        query_hash: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        """Record database query metrics."""
        key = f"{query_type}:{table_name or 'unknown'}"
        
        with self._lock:
            if key not in self.db_metrics:
                self.db_metrics[key] = DatabaseMetrics(
                    query_type=query_type,
                    table_name=table_name,
                    slow_query_threshold=self.slow_query_threshold
                )
            
            self.db_metrics[key].update(execution_time, success)
        
        # Check for performance issues
        self._check_db_performance(key, execution_time, success)
    
    def record_user_experience(self, metrics: UserExperienceMetrics):
        """Record user experience metrics."""
        self.user_metrics.append(metrics)
        
        # Keep only recent metrics (last 10000)
        if len(self.user_metrics) > 10000:
            self.user_metrics = self.user_metrics[-10000:]
        
        # Check for UX issues
        self._check_user_experience(metrics)
    
    def start_business_transaction(
        self,
        transaction_name: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start tracking a business transaction."""
        transaction_id = str(uuid.uuid4())
        
        self.business_transactions[transaction_id] = {
            "name": transaction_name,
            "user_id": user_id,
            "start_time": time.time(),
            "end_time": None,
            "duration": None,
            "status": "in_progress",
            "steps": [],
            "metadata": metadata or {}
        }
        
        return transaction_id
    
    def add_transaction_step(
        self,
        transaction_id: str,
        step_name: str,
        duration: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a step to a business transaction."""
        if transaction_id in self.business_transactions:
            step = {
                "name": step_name,
                "duration": duration,
                "success": success,
                "timestamp": time.time(),
                "metadata": metadata or {}
            }
            self.business_transactions[transaction_id]["steps"].append(step)
    
    def finish_business_transaction(
        self,
        transaction_id: str,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Finish a business transaction."""
        if transaction_id in self.business_transactions:
            transaction = self.business_transactions[transaction_id]
            transaction["end_time"] = time.time()
            transaction["duration"] = transaction["end_time"] - transaction["start_time"]
            transaction["status"] = "completed" if success else "failed"
            
            if metadata:
                transaction["metadata"].update(metadata)
    
    def _check_api_performance(self, endpoint_key: str, response_time: float, status_code: int):
        """Check API performance and trigger alerts if needed."""
        metrics = self.api_metrics[endpoint_key]
        
        # Check slow requests
        if response_time > self.slow_request_threshold:
            self._trigger_alert({
                "type": "slow_request",
                "endpoint": endpoint_key,
                "response_time": response_time,
                "threshold": self.slow_request_threshold,
                "severity": "warning"
            })
        
        # Check error rate
        if metrics.error_rate > self.error_rate_threshold and metrics.total_requests >= 10:
            self._trigger_alert({
                "type": "high_error_rate",
                "endpoint": endpoint_key,
                "error_rate": metrics.error_rate,
                "threshold": self.error_rate_threshold,
                "severity": "critical"
            })
    
    def _check_db_performance(self, query_key: str, execution_time: float, success: bool):
        """Check database performance and trigger alerts if needed."""
        if execution_time > self.slow_query_threshold:
            self._trigger_alert({
                "type": "slow_query",
                "query": query_key,
                "execution_time": execution_time,
                "threshold": self.slow_query_threshold,
                "severity": "warning"
            })
        
        if not success:
            self._trigger_alert({
                "type": "query_failure",
                "query": query_key,
                "execution_time": execution_time,
                "severity": "error"
            })
    
    def _check_user_experience(self, metrics: UserExperienceMetrics):
        """Check user experience metrics and trigger alerts if needed."""
        # Check page load time
        if metrics.page_load_time > 5.0:  # 5 seconds
            self._trigger_alert({
                "type": "slow_page_load",
                "page_url": metrics.page_url,
                "load_time": metrics.page_load_time,
                "threshold": 5.0,
                "severity": "warning"
            })
        
        # Check Core Web Vitals
        if metrics.largest_contentful_paint > 2.5:  # LCP threshold
            self._trigger_alert({
                "type": "poor_lcp",
                "page_url": metrics.page_url,
                "lcp": metrics.largest_contentful_paint,
                "threshold": 2.5,
                "severity": "warning"
            })
        
        if metrics.first_input_delay > 100:  # FID threshold (ms)
            self._trigger_alert({
                "type": "poor_fid",
                "page_url": metrics.page_url,
                "fid": metrics.first_input_delay,
                "threshold": 100,
                "severity": "warning"
            })
        
        if metrics.cumulative_layout_shift > 0.1:  # CLS threshold
            self._trigger_alert({
                "type": "poor_cls",
                "page_url": metrics.page_url,
                "cls": metrics.cumulative_layout_shift,
                "threshold": 0.1,
                "severity": "warning"
            })
    
    def _trigger_alert(self, alert: Dict[str, Any]):
        """Trigger performance alert."""
        alert["timestamp"] = time.time()
        
        logger.warning(f"APM Alert: {alert}")
        
        # Notify alert handlers
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(alert))
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def get_api_performance_summary(self) -> Dict[str, Any]:
        """Get API performance summary."""
        with self._lock:
            summary = {
                "total_endpoints": len(self.api_metrics),
                "endpoints": {}
            }
            
            for key, metrics in self.api_metrics.items():
                summary["endpoints"][key] = {
                    "total_requests": metrics.total_requests,
                    "avg_response_time": metrics.avg_response_time,
                    "p95_response_time": metrics.p95_response_time,
                    "error_rate": metrics.error_rate,
                    "status_codes": dict(metrics.status_codes)
                }
        
        return summary
    
    def get_database_performance_summary(self) -> Dict[str, Any]:
        """Get database performance summary."""
        with self._lock:
            summary = {
                "total_query_types": len(self.db_metrics),
                "queries": {}
            }
            
            for key, metrics in self.db_metrics.items():
                summary["queries"][key] = {
                    "total_queries": metrics.total_queries,
                    "avg_execution_time": metrics.avg_execution_time,
                    "slow_query_count": metrics.slow_query_count,
                    "success_rate": metrics.successful_queries / metrics.total_queries if metrics.total_queries > 0 else 0
                }
        
        return summary
    
    def get_user_experience_summary(self) -> Dict[str, Any]:
        """Get user experience summary."""
        if not self.user_metrics:
            return {"total_sessions": 0}
        
        recent_metrics = self.user_metrics[-1000:]  # Last 1000 sessions
        
        page_loads = [m.page_load_time for m in recent_metrics if m.page_load_time > 0]
        lcp_values = [m.largest_contentful_paint for m in recent_metrics if m.largest_contentful_paint > 0]
        fid_values = [m.first_input_delay for m in recent_metrics if m.first_input_delay > 0]
        cls_values = [m.cumulative_layout_shift for m in recent_metrics if m.cumulative_layout_shift > 0]
        
        return {
            "total_sessions": len(recent_metrics),
            "avg_page_load_time": statistics.mean(page_loads) if page_loads else 0,
            "avg_lcp": statistics.mean(lcp_values) if lcp_values else 0,
            "avg_fid": statistics.mean(fid_values) if fid_values else 0,
            "avg_cls": statistics.mean(cls_values) if cls_values else 0,
            "core_web_vitals_score": self._calculate_cwv_score(recent_metrics)
        }
    
    def _calculate_cwv_score(self, metrics: List[UserExperienceMetrics]) -> float:
        """Calculate Core Web Vitals score (0-100)."""
        if not metrics:
            return 0.0
        
        good_lcp = sum(1 for m in metrics if m.largest_contentful_paint <= 2.5 and m.largest_contentful_paint > 0)
        good_fid = sum(1 for m in metrics if m.first_input_delay <= 100 and m.first_input_delay > 0)
        good_cls = sum(1 for m in metrics if m.cumulative_layout_shift <= 0.1 and m.cumulative_layout_shift > 0)
        
        total_with_lcp = sum(1 for m in metrics if m.largest_contentful_paint > 0)
        total_with_fid = sum(1 for m in metrics if m.first_input_delay > 0)
        total_with_cls = sum(1 for m in metrics if m.cumulative_layout_shift > 0)
        
        lcp_score = (good_lcp / total_with_lcp * 100) if total_with_lcp > 0 else 100
        fid_score = (good_fid / total_with_fid * 100) if total_with_fid > 0 else 100
        cls_score = (good_cls / total_with_cls * 100) if total_with_cls > 0 else 100
        
        return (lcp_score + fid_score + cls_score) / 3
    
    def get_business_transaction_summary(self) -> Dict[str, Any]:
        """Get business transaction summary."""
        completed_transactions = [
            t for t in self.business_transactions.values()
            if t["status"] in ["completed", "failed"]
        ]
        
        if not completed_transactions:
            return {"total_transactions": 0}
        
        successful_transactions = [t for t in completed_transactions if t["status"] == "completed"]
        
        durations = [t["duration"] for t in completed_transactions if t["duration"]]
        
        return {
            "total_transactions": len(completed_transactions),
            "successful_transactions": len(successful_transactions),
            "success_rate": len(successful_transactions) / len(completed_transactions),
            "avg_duration": statistics.mean(durations) if durations else 0,
            "transactions_by_name": self._group_transactions_by_name(completed_transactions)
        }
    
    def _group_transactions_by_name(self, transactions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Group transactions by name and calculate statistics."""
        grouped = defaultdict(list)
        
        for transaction in transactions:
            grouped[transaction["name"]].append(transaction)
        
        result = {}
        for name, trans_list in grouped.items():
            durations = [t["duration"] for t in trans_list if t["duration"]]
            successful = [t for t in trans_list if t["status"] == "completed"]
            
            result[name] = {
                "count": len(trans_list),
                "success_rate": len(successful) / len(trans_list),
                "avg_duration": statistics.mean(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0
            }
        
        return result
    
    def get_trace_analysis(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed trace analysis."""
        trace_spans = self.tracer.get_trace(trace_id)
        
        if not trace_spans:
            return None
        
        # Calculate trace statistics
        total_duration = max(s.end_time for s in trace_spans if s.end_time) - min(s.start_time for s in trace_spans)
        
        # Build span hierarchy
        span_tree = self._build_span_tree(trace_spans)
        
        # Identify bottlenecks
        bottlenecks = self._identify_trace_bottlenecks(trace_spans)
        
        return {
            "trace_id": trace_id,
            "total_duration": total_duration,
            "span_count": len(trace_spans),
            "service_count": len(set(s.service_name for s in trace_spans)),
            "error_count": len([s for s in trace_spans if s.status == "error"]),
            "span_tree": span_tree,
            "bottlenecks": bottlenecks,
            "spans": [s.to_dict() for s in trace_spans]
        }
    
    def _build_span_tree(self, spans: List[TraceSpan]) -> Dict[str, Any]:
        """Build hierarchical span tree."""
        span_map = {s.span_id: s for s in spans}
        root_spans = [s for s in spans if s.parent_span_id is None]
        
        def build_tree_node(span: TraceSpan) -> Dict[str, Any]:
            children = [s for s in spans if s.parent_span_id == span.span_id]
            
            return {
                "span": span.to_dict(),
                "children": [build_tree_node(child) for child in children]
            }
        
        return {
            "roots": [build_tree_node(root) for root in root_spans]
        }
    
    def _identify_trace_bottlenecks(self, spans: List[TraceSpan]) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks in trace."""
        bottlenecks = []
        
        # Find spans that take more than 50% of total trace time
        total_duration = max(s.end_time for s in spans if s.end_time) - min(s.start_time for s in spans)
        threshold = total_duration * 0.5
        
        for span in spans:
            if span.duration and span.duration > threshold:
                bottlenecks.append({
                    "span_id": span.span_id,
                    "operation_name": span.operation_name,
                    "duration": span.duration,
                    "percentage": (span.duration / total_duration) * 100,
                    "type": "duration_bottleneck"
                })
        
        # Find spans with errors
        for span in spans:
            if span.status == "error":
                bottlenecks.append({
                    "span_id": span.span_id,
                    "operation_name": span.operation_name,
                    "duration": span.duration,
                    "type": "error_bottleneck",
                    "logs": span.logs
                })
        
        return bottlenecks


# Global APM monitor instance
apm_monitor = APMMonitor()


# Convenience decorators and context managers
def trace_api_request(endpoint: str, method: str = "GET"):
    """Decorator for tracing API requests."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with apm_monitor.trace_request(f"{method} {endpoint}") as span:
                    span.add_tag("endpoint", endpoint)
                    span.add_tag("method", method)
                    
                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        response_time = time.time() - start_time
                        
                        # Assume success if no exception
                        status_code = getattr(result, 'status_code', 200)
                        apm_monitor.record_api_request(endpoint, method, response_time, status_code, trace_id=span.trace_id)
                        
                        return result
                    except Exception as e:
                        response_time = time.time() - start_time
                        apm_monitor.record_api_request(endpoint, method, response_time, 500, trace_id=span.trace_id)
                        raise
            return async_wrapper
        else:
            def wrapper(*args, **kwargs):
                # For sync functions, create a simple trace
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    response_time = time.time() - start_time
                    
                    status_code = getattr(result, 'status_code', 200)
                    apm_monitor.record_api_request(endpoint, method, response_time, status_code)
                    
                    return result
                except Exception as e:
                    response_time = time.time() - start_time
                    apm_monitor.record_api_request(endpoint, method, response_time, 500)
                    raise
            return wrapper
    return decorator


@asynccontextmanager
async def trace_database_query(query_type: str, table_name: Optional[str] = None):
    """Context manager for tracing database queries."""
    start_time = time.time()
    success = True
    
    try:
        yield
    except Exception as e:
        success = False
        raise
    finally:
        execution_time = time.time() - start_time
        apm_monitor.record_database_query(query_type, execution_time, success, table_name)


class BusinessTransactionTracker:
    """Context manager for tracking business transactions."""
    
    def __init__(self, transaction_name: str, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.transaction_name = transaction_name
        self.user_id = user_id
        self.metadata = metadata
        self.transaction_id = None
        self.success = True
    
    def __enter__(self):
        self.transaction_id = apm_monitor.start_business_transaction(
            self.transaction_name, self.user_id, self.metadata
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.success = False
        
        if self.transaction_id:
            apm_monitor.finish_business_transaction(self.transaction_id, self.success)
    
    def add_step(self, step_name: str, duration: float, success: bool = True, metadata: Optional[Dict[str, Any]] = None):
        """Add a step to the transaction."""
        if self.transaction_id:
            apm_monitor.add_transaction_step(self.transaction_id, step_name, duration, success, metadata)
    
    def set_success(self, success: bool):
        """Set transaction success status."""
        self.success = success