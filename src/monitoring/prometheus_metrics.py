"""
Prometheus 指标模块
为关键操作提供计数器、直方图和仪表盘指标

**Feature: system-optimization**
**Validates: Requirements 13.1**
"""

import logging
import time
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from contextlib import contextmanager
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import threading

from src.i18n.translations import t

logger = logging.getLogger(__name__)


# ============================================================================
# 指标类型定义
# ============================================================================

class MetricType(str, Enum):
    """指标类型"""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"


@dataclass
class MetricLabel:
    """指标标签"""
    name: str
    value: str


@dataclass
class MetricValue:
    """指标值"""
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)


# ============================================================================
# 计数器 (Counter)
# ============================================================================

class Counter:
    """
    计数器指标
    只能增加，用于统计请求数、错误数等
    """
    
    def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[tuple, float] = {}
        self._lock = threading.Lock()
    
    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """增加计数器值"""
        if value < 0:
            raise ValueError(t('monitoring.metrics.counter_negative_value'))
        
        label_key = self._get_label_key(labels)
        with self._lock:
            if label_key not in self._values:
                self._values[label_key] = 0.0
            self._values[label_key] += value
    
    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """获取计数器值"""
        label_key = self._get_label_key(labels)
        with self._lock:
            return self._values.get(label_key, 0.0)
    
    def _get_label_key(self, labels: Optional[Dict[str, str]] = None) -> tuple:
        """生成标签键"""
        if not labels:
            return ()
        return tuple(sorted(labels.items()))
    
    def collect(self) -> List[Dict[str, Any]]:
        """收集所有指标值"""
        with self._lock:
            return [
                {
                    "name": self.name,
                    "type": MetricType.COUNTER.value,
                    "description": self.description,
                    "labels": dict(label_key) if label_key else {},
                    "value": value
                }
                for label_key, value in self._values.items()
            ]


# ============================================================================
# 直方图 (Histogram)
# ============================================================================

class Histogram:
    """
    直方图指标
    用于统计请求延迟、响应时间等分布
    """
    
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))
    
    def __init__(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        buckets: Optional[tuple] = None
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._values: Dict[tuple, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """记录观测值"""
        label_key = self._get_label_key(labels)
        
        with self._lock:
            if label_key not in self._values:
                self._values[label_key] = {
                    "sum": 0.0,
                    "count": 0,
                    "buckets": {b: 0 for b in self.buckets}
                }
            
            data = self._values[label_key]
            data["sum"] += value
            data["count"] += 1
            
            for bucket in self.buckets:
                if value <= bucket:
                    data["buckets"][bucket] += 1
    
    def get_sum(self, labels: Optional[Dict[str, str]] = None) -> float:
        """获取总和"""
        label_key = self._get_label_key(labels)
        with self._lock:
            data = self._values.get(label_key, {})
            return data.get("sum", 0.0)
    
    def get_count(self, labels: Optional[Dict[str, str]] = None) -> int:
        """获取计数"""
        label_key = self._get_label_key(labels)
        with self._lock:
            data = self._values.get(label_key, {})
            return data.get("count", 0)
    
    def get_average(self, labels: Optional[Dict[str, str]] = None) -> float:
        """获取平均值"""
        label_key = self._get_label_key(labels)
        with self._lock:
            data = self._values.get(label_key, {})
            count = data.get("count", 0)
            if count == 0:
                return 0.0
            return data.get("sum", 0.0) / count
    
    def _get_label_key(self, labels: Optional[Dict[str, str]] = None) -> tuple:
        """生成标签键"""
        if not labels:
            return ()
        return tuple(sorted(labels.items()))
    
    @contextmanager
    def time(self, labels: Optional[Dict[str, str]] = None):
        """计时上下文管理器"""
        start = time.time()
        try:
            yield
        finally:
            self.observe(time.time() - start, labels)
    
    def collect(self) -> List[Dict[str, Any]]:
        """收集所有指标值"""
        with self._lock:
            return [
                {
                    "name": self.name,
                    "type": MetricType.HISTOGRAM.value,
                    "description": self.description,
                    "labels": dict(label_key) if label_key else {},
                    "sum": data["sum"],
                    "count": data["count"],
                    "buckets": data["buckets"]
                }
                for label_key, data in self._values.items()
            ]


# ============================================================================
# 仪表盘 (Gauge)
# ============================================================================

class Gauge:
    """
    仪表盘指标
    可以增加或减少，用于统计当前连接数、缓存命中率等
    """
    
    def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[tuple, float] = {}
        self._lock = threading.Lock()
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表盘值"""
        label_key = self._get_label_key(labels)
        with self._lock:
            self._values[label_key] = value
    
    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """增加仪表盘值"""
        label_key = self._get_label_key(labels)
        with self._lock:
            if label_key not in self._values:
                self._values[label_key] = 0.0
            self._values[label_key] += value
    
    def dec(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """减少仪表盘值"""
        label_key = self._get_label_key(labels)
        with self._lock:
            if label_key not in self._values:
                self._values[label_key] = 0.0
            self._values[label_key] -= value
    
    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """获取仪表盘值"""
        label_key = self._get_label_key(labels)
        with self._lock:
            return self._values.get(label_key, 0.0)
    
    def _get_label_key(self, labels: Optional[Dict[str, str]] = None) -> tuple:
        """生成标签键"""
        if not labels:
            return ()
        return tuple(sorted(labels.items()))
    
    def collect(self) -> List[Dict[str, Any]]:
        """收集所有指标值"""
        with self._lock:
            return [
                {
                    "name": self.name,
                    "type": MetricType.GAUGE.value,
                    "description": self.description,
                    "labels": dict(label_key) if label_key else {},
                    "value": value
                }
                for label_key, value in self._values.items()
            ]


# ============================================================================
# 指标注册表
# ============================================================================

class MetricsRegistry:
    """
    指标注册表
    管理所有 Prometheus 指标
    """
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def register(self, metric):
        """注册指标"""
        with self._lock:
            if metric.name in self._metrics:
                logger.warning(
                    t('monitoring.metrics.metric_already_registered', name=metric.name)
                )
                return self._metrics[metric.name]
            self._metrics[metric.name] = metric
            logger.debug(t('monitoring.metrics.metric_registered', name=metric.name))
            return metric
    
    def get(self, name: str):
        """获取指标"""
        with self._lock:
            return self._metrics.get(name)
    
    def unregister(self, name: str):
        """取消注册指标"""
        with self._lock:
            if name in self._metrics:
                del self._metrics[name]
                logger.debug(t('monitoring.metrics.metric_unregistered', name=name))
    
    def collect_all(self) -> List[Dict[str, Any]]:
        """收集所有指标"""
        with self._lock:
            all_metrics = []
            for metric in self._metrics.values():
                all_metrics.extend(metric.collect())
            return all_metrics
    
    def get_prometheus_format(self) -> str:
        """获取 Prometheus 格式的指标输出"""
        lines = []
        metrics = self.collect_all()
        
        for metric in metrics:
            name = metric["name"]
            metric_type = metric["type"]
            description = metric.get("description", "")
            labels = metric.get("labels", {})
            
            # HELP 行
            lines.append(f"# HELP {name} {description}")
            # TYPE 行
            lines.append(f"# TYPE {name} {metric_type}")
            
            # 标签字符串
            label_str = ""
            if labels:
                label_parts = [f'{k}="{v}"' for k, v in labels.items()]
                label_str = "{" + ",".join(label_parts) + "}"
            
            if metric_type == MetricType.COUNTER.value:
                lines.append(f"{name}{label_str} {metric['value']}")
            elif metric_type == MetricType.GAUGE.value:
                lines.append(f"{name}{label_str} {metric['value']}")
            elif metric_type == MetricType.HISTOGRAM.value:
                # 直方图需要输出多行
                for bucket, count in metric.get("buckets", {}).items():
                    bucket_label = f'{label_str[:-1]},le="{bucket}"}}' if label_str else f'{{le="{bucket}"}}'
                    lines.append(f"{name}_bucket{bucket_label} {count}")
                lines.append(f"{name}_sum{label_str} {metric['sum']}")
                lines.append(f"{name}_count{label_str} {metric['count']}")
        
        return "\n".join(lines)


# ============================================================================
# 全局指标注册表
# ============================================================================

# 全局注册表实例
metrics_registry = MetricsRegistry()


# ============================================================================
# SuperInsight 平台指标定义
# ============================================================================

# API 请求指标
api_requests_total = metrics_registry.register(
    Counter(
        name="superinsight_api_requests_total",
        description="API 请求总数",
        labels=["method", "endpoint", "status"]
    )
)

api_errors_total = metrics_registry.register(
    Counter(
        name="superinsight_api_errors_total",
        description="API 错误总数",
        labels=["method", "endpoint", "error_type"]
    )
)

api_request_duration_seconds = metrics_registry.register(
    Histogram(
        name="superinsight_api_request_duration_seconds",
        description="API 请求延迟（秒）",
        labels=["method", "endpoint"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf'))
    )
)

# 缓存指标
cache_hits_total = metrics_registry.register(
    Counter(
        name="superinsight_cache_hits_total",
        description="缓存命中总数",
        labels=["cache_type"]
    )
)

cache_misses_total = metrics_registry.register(
    Counter(
        name="superinsight_cache_misses_total",
        description="缓存未命中总数",
        labels=["cache_type"]
    )
)

cache_operation_duration_seconds = metrics_registry.register(
    Histogram(
        name="superinsight_cache_operation_duration_seconds",
        description="缓存操作延迟（秒）",
        labels=["operation", "cache_type"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float('inf'))
    )
)

cache_hit_rate = metrics_registry.register(
    Gauge(
        name="superinsight_cache_hit_rate",
        description="缓存命中率",
        labels=["cache_type"]
    )
)

# 数据库指标
db_queries_total = metrics_registry.register(
    Counter(
        name="superinsight_db_queries_total",
        description="数据库查询总数",
        labels=["operation", "table"]
    )
)

db_query_duration_seconds = metrics_registry.register(
    Histogram(
        name="superinsight_db_query_duration_seconds",
        description="数据库查询延迟（秒）",
        labels=["operation", "table"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf'))
    )
)

# 连接指标
active_connections = metrics_registry.register(
    Gauge(
        name="superinsight_active_connections",
        description="活跃连接数",
        labels=["connection_type"]
    )
)

# 通知指标
notifications_sent_total = metrics_registry.register(
    Counter(
        name="superinsight_notifications_sent_total",
        description="通知发送总数",
        labels=["channel", "status"]
    )
)

# 服务健康指标
service_health = metrics_registry.register(
    Gauge(
        name="superinsight_service_health",
        description="服务健康状态 (0=不健康, 1=健康)",
        labels=["service"]
    )
)

# 业务指标
annotation_throughput = metrics_registry.register(
    Counter(
        name="superinsight_annotation_throughput_total",
        description="标注吞吐量",
        labels=["project_id", "annotator_id"]
    )
)

quality_score = metrics_registry.register(
    Gauge(
        name="superinsight_quality_score",
        description="质量分数",
        labels=["project_id", "metric_type"]
    )
)


# ============================================================================
# 装饰器
# ============================================================================

def track_request(method: str, endpoint: str):
    """
    请求追踪装饰器
    自动记录请求计数和延迟
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                api_errors_total.inc(labels={
                    "method": method,
                    "endpoint": endpoint,
                    "error_type": type(e).__name__
                })
                raise
            finally:
                duration = time.time() - start_time
                api_requests_total.inc(labels={
                    "method": method,
                    "endpoint": endpoint,
                    "status": status
                })
                api_request_duration_seconds.observe(duration, labels={
                    "method": method,
                    "endpoint": endpoint
                })
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                api_errors_total.inc(labels={
                    "method": method,
                    "endpoint": endpoint,
                    "error_type": type(e).__name__
                })
                raise
            finally:
                duration = time.time() - start_time
                api_requests_total.inc(labels={
                    "method": method,
                    "endpoint": endpoint,
                    "status": status
                })
                api_request_duration_seconds.observe(duration, labels={
                    "method": method,
                    "endpoint": endpoint
                })
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def track_db_query(operation: str, table: str):
    """
    数据库查询追踪装饰器
    自动记录查询计数和延迟
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                db_queries_total.inc(labels={
                    "operation": operation,
                    "table": table
                })
                db_query_duration_seconds.observe(duration, labels={
                    "operation": operation,
                    "table": table
                })
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                db_queries_total.inc(labels={
                    "operation": operation,
                    "table": table
                })
                db_query_duration_seconds.observe(duration, labels={
                    "operation": operation,
                    "table": table
                })
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ============================================================================
# 辅助函数
# ============================================================================

def record_cache_hit(cache_type: str = "default"):
    """记录缓存命中"""
    cache_hits_total.inc(labels={"cache_type": cache_type})


def record_cache_miss(cache_type: str = "default"):
    """记录缓存未命中"""
    cache_misses_total.inc(labels={"cache_type": cache_type})


def update_cache_hit_rate(cache_type: str = "default"):
    """更新缓存命中率"""
    hits = cache_hits_total.get(labels={"cache_type": cache_type})
    misses = cache_misses_total.get(labels={"cache_type": cache_type})
    total = hits + misses
    if total > 0:
        rate = hits / total
        cache_hit_rate.set(rate, labels={"cache_type": cache_type})


def record_notification_sent(channel: str, success: bool):
    """记录通知发送"""
    status = "success" if success else "failed"
    notifications_sent_total.inc(labels={"channel": channel, "status": status})


def update_service_health(service: str, healthy: bool):
    """更新服务健康状态"""
    service_health.set(1.0 if healthy else 0.0, labels={"service": service})


def record_annotation(project_id: str, annotator_id: str, count: int = 1):
    """记录标注"""
    annotation_throughput.inc(count, labels={
        "project_id": project_id,
        "annotator_id": annotator_id
    })


def update_quality_score(project_id: str, metric_type: str, score: float):
    """更新质量分数"""
    quality_score.set(score, labels={
        "project_id": project_id,
        "metric_type": metric_type
    })


def update_active_connections(connection_type: str, count: int):
    """更新活跃连接数"""
    active_connections.set(count, labels={"connection_type": connection_type})


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 类型
    "MetricType",
    "MetricLabel",
    "MetricValue",
    # 指标类
    "Counter",
    "Histogram",
    "Gauge",
    "MetricsRegistry",
    # 全局注册表
    "metrics_registry",
    # 预定义指标
    "api_requests_total",
    "api_errors_total",
    "api_request_duration_seconds",
    "cache_hits_total",
    "cache_misses_total",
    "cache_operation_duration_seconds",
    "cache_hit_rate",
    "db_queries_total",
    "db_query_duration_seconds",
    "active_connections",
    "notifications_sent_total",
    "service_health",
    "annotation_throughput",
    "quality_score",
    # 装饰器
    "track_request",
    "track_db_query",
    # 辅助函数
    "record_cache_hit",
    "record_cache_miss",
    "update_cache_hit_rate",
    "record_notification_sent",
    "update_service_health",
    "record_annotation",
    "update_quality_score",
    "update_active_connections",
]
