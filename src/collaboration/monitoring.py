"""
本体专家协作监控模块

提供监控和日志支持：
- Prometheus 指标
- 结构化日志
- 健康检查端点

Validates: Task 29 - Implement Monitoring and Logging
"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# Prometheus 指标
# ============================================================================

class MetricType(str, Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricDefinition:
    """指标定义"""
    name: str
    description: str
    metric_type: MetricType
    labels: List[str] = field(default_factory=list)


# 协作模块指标定义
COLLABORATION_METRICS: List[MetricDefinition] = [
    # API 指标
    MetricDefinition(
        name="ontology_api_requests_total",
        description="Total API requests",
        metric_type=MetricType.COUNTER,
        labels=["endpoint", "method", "status"],
    ),
    MetricDefinition(
        name="ontology_api_request_duration_seconds",
        description="API request duration in seconds",
        metric_type=MetricType.HISTOGRAM,
        labels=["endpoint", "method"],
    ),
    MetricDefinition(
        name="ontology_api_errors_total",
        description="Total API errors",
        metric_type=MetricType.COUNTER,
        labels=["endpoint", "error_type"],
    ),
]

# WebSocket 指标
WEBSOCKET_METRICS: List[MetricDefinition] = [
    MetricDefinition(
        name="ontology_websocket_connections_total",
        description="Total WebSocket connections",
        metric_type=MetricType.COUNTER,
        labels=["session_id"],
    ),
    MetricDefinition(
        name="ontology_websocket_connections_active",
        description="Active WebSocket connections",
        metric_type=MetricType.GAUGE,
        labels=[],
    ),
    MetricDefinition(
        name="ontology_websocket_messages_total",
        description="Total WebSocket messages",
        metric_type=MetricType.COUNTER,
        labels=["message_type", "direction"],
    ),
    MetricDefinition(
        name="ontology_websocket_message_size_bytes",
        description="WebSocket message size in bytes",
        metric_type=MetricType.HISTOGRAM,
        labels=["message_type"],
    ),
]

# 协作会话指标
SESSION_METRICS: List[MetricDefinition] = [
    MetricDefinition(
        name="ontology_collaboration_sessions_total",
        description="Total collaboration sessions created",
        metric_type=MetricType.COUNTER,
        labels=[],
    ),
    MetricDefinition(
        name="ontology_collaboration_sessions_active",
        description="Active collaboration sessions",
        metric_type=MetricType.GAUGE,
        labels=[],
    ),
    MetricDefinition(
        name="ontology_collaboration_session_duration_seconds",
        description="Collaboration session duration in seconds",
        metric_type=MetricType.HISTOGRAM,
        labels=[],
    ),
    MetricDefinition(
        name="ontology_collaboration_participants",
        description="Number of participants per session",
        metric_type=MetricType.GAUGE,
        labels=["session_id"],
    ),
]

# 审批工作流指标
APPROVAL_METRICS: List[MetricDefinition] = [
    MetricDefinition(
        name="ontology_approval_requests_total",
        description="Total approval requests",
        metric_type=MetricType.COUNTER,
        labels=["ontology_area", "status"],
    ),
    MetricDefinition(
        name="ontology_approval_pending",
        description="Pending approval requests",
        metric_type=MetricType.GAUGE,
        labels=["ontology_area"],
    ),
    MetricDefinition(
        name="ontology_approval_completion_time_seconds",
        description="Approval completion time in seconds",
        metric_type=MetricType.HISTOGRAM,
        labels=["ontology_area"],
    ),
]


class PrometheusMetricsCollector:
    """
    Prometheus 指标收集器
    
    收集和导出协作模块的 Prometheus 指标
    """
    
    def __init__(self):
        """初始化指标收集器"""
        self._counters: Dict[str, Dict[tuple, float]] = {}
        self._gauges: Dict[str, Dict[tuple, float]] = {}
        self._histograms: Dict[str, Dict[tuple, List[float]]] = {}
        self._lock = asyncio.Lock()
        
        # 初始化指标
        all_metrics = (
            COLLABORATION_METRICS + 
            WEBSOCKET_METRICS + 
            SESSION_METRICS + 
            APPROVAL_METRICS
        )
        
        for metric in all_metrics:
            if metric.metric_type == MetricType.COUNTER:
                self._counters[metric.name] = {}
            elif metric.metric_type == MetricType.GAUGE:
                self._gauges[metric.name] = {}
            elif metric.metric_type in (MetricType.HISTOGRAM, MetricType.SUMMARY):
                self._histograms[metric.name] = {}
        
        logger.info("PrometheusMetricsCollector initialized")
    
    async def inc_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """增加计数器"""
        label_key = tuple(sorted((labels or {}).items()))
        
        async with self._lock:
            if name not in self._counters:
                self._counters[name] = {}
            
            current = self._counters[name].get(label_key, 0.0)
            self._counters[name][label_key] = current + value
    
    async def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """设置仪表值"""
        label_key = tuple(sorted((labels or {}).items()))
        
        async with self._lock:
            if name not in self._gauges:
                self._gauges[name] = {}
            
            self._gauges[name][label_key] = value
    
    async def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """观察直方图值"""
        label_key = tuple(sorted((labels or {}).items()))
        
        async with self._lock:
            if name not in self._histograms:
                self._histograms[name] = {}
            
            if label_key not in self._histograms[name]:
                self._histograms[name][label_key] = []
            
            self._histograms[name][label_key].append(value)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        async with self._lock:
            return {
                "counters": {
                    name: {str(k): v for k, v in values.items()}
                    for name, values in self._counters.items()
                },
                "gauges": {
                    name: {str(k): v for k, v in values.items()}
                    for name, values in self._gauges.items()
                },
                "histograms": {
                    name: {
                        str(k): {
                            "count": len(v),
                            "sum": sum(v),
                            "avg": sum(v) / len(v) if v else 0,
                            "min": min(v) if v else 0,
                            "max": max(v) if v else 0,
                        }
                        for k, v in values.items()
                    }
                    for name, values in self._histograms.items()
                },
            }
    
    async def export_prometheus_format(self) -> str:
        """导出 Prometheus 格式"""
        lines = []
        
        async with self._lock:
            # 导出计数器
            for name, values in self._counters.items():
                lines.append(f"# TYPE {name} counter")
                for labels, value in values.items():
                    label_str = self._format_labels(labels)
                    lines.append(f"{name}{label_str} {value}")
            
            # 导出仪表
            for name, values in self._gauges.items():
                lines.append(f"# TYPE {name} gauge")
                for labels, value in values.items():
                    label_str = self._format_labels(labels)
                    lines.append(f"{name}{label_str} {value}")
            
            # 导出直方图
            for name, values in self._histograms.items():
                lines.append(f"# TYPE {name} histogram")
                for labels, observations in values.items():
                    label_str = self._format_labels(labels)
                    if observations:
                        lines.append(f"{name}_count{label_str} {len(observations)}")
                        lines.append(f"{name}_sum{label_str} {sum(observations)}")
        
        return "\n".join(lines)
    
    def _format_labels(self, labels: tuple) -> str:
        """格式化标签"""
        if not labels:
            return ""
        
        label_parts = [f'{k}="{v}"' for k, v in labels]
        return "{" + ",".join(label_parts) + "}"


# ============================================================================
# 结构化日志
# ============================================================================

class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class StructuredLogEntry:
    """结构化日志条目"""
    timestamp: datetime
    level: LogLevel
    message: str
    correlation_id: str
    service: str = "ontology_collaboration"
    module: Optional[str] = None
    function: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None
    duration_ms: Optional[float] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "correlation_id": self.correlation_id,
            "service": self.service,
        }
        
        if self.module:
            result["module"] = self.module
        if self.function:
            result["function"] = self.function
        if self.user_id:
            result["user_id"] = self.user_id
        if self.tenant_id:
            result["tenant_id"] = self.tenant_id
        if self.session_id:
            result["session_id"] = self.session_id
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        if self.error_type:
            result["error_type"] = self.error_type
        if self.error_message:
            result["error_message"] = self.error_message
        if self.stack_trace:
            result["stack_trace"] = self.stack_trace
        if self.extra:
            result["extra"] = self.extra
        
        return result


class StructuredLogger:
    """
    结构化日志记录器
    
    提供带有关联 ID 的结构化日志
    """
    
    def __init__(
        self,
        service_name: str = "ontology_collaboration",
        default_level: LogLevel = LogLevel.INFO,
    ):
        """
        初始化结构化日志记录器
        
        Args:
            service_name: 服务名称
            default_level: 默认日志级别
        """
        self._service_name = service_name
        self._default_level = default_level
        self._correlation_id: Optional[str] = None
        
        logger.info(f"StructuredLogger initialized for {service_name}")
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """设置关联 ID"""
        self._correlation_id = correlation_id
    
    def get_correlation_id(self) -> str:
        """获取关联 ID"""
        if self._correlation_id is None:
            self._correlation_id = str(uuid.uuid4())
        return self._correlation_id
    
    def clear_correlation_id(self) -> None:
        """清除关联 ID"""
        self._correlation_id = None
    
    def _create_entry(
        self,
        level: LogLevel,
        message: str,
        **kwargs,
    ) -> StructuredLogEntry:
        """创建日志条目"""
        return StructuredLogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            correlation_id=self.get_correlation_id(),
            service=self._service_name,
            **kwargs,
        )
    
    def _log(self, entry: StructuredLogEntry) -> None:
        """记录日志"""
        import json
        log_dict = entry.to_dict()
        log_json = json.dumps(log_dict, ensure_ascii=False)
        
        # 使用标准 logger 输出
        level_map = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }
        
        logger.log(level_map[entry.level], log_json)
    
    def debug(self, message: str, **kwargs) -> None:
        """记录 DEBUG 日志"""
        entry = self._create_entry(LogLevel.DEBUG, message, **kwargs)
        self._log(entry)
    
    def info(self, message: str, **kwargs) -> None:
        """记录 INFO 日志"""
        entry = self._create_entry(LogLevel.INFO, message, **kwargs)
        self._log(entry)
    
    def warning(self, message: str, **kwargs) -> None:
        """记录 WARNING 日志"""
        entry = self._create_entry(LogLevel.WARNING, message, **kwargs)
        self._log(entry)
    
    def error(
        self,
        message: str,
        error: Optional[Exception] = None,
        **kwargs,
    ) -> None:
        """记录 ERROR 日志"""
        if error:
            import traceback
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
            kwargs["stack_trace"] = traceback.format_exc()
        
        entry = self._create_entry(LogLevel.ERROR, message, **kwargs)
        self._log(entry)
    
    def critical(
        self,
        message: str,
        error: Optional[Exception] = None,
        **kwargs,
    ) -> None:
        """记录 CRITICAL 日志"""
        if error:
            import traceback
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
            kwargs["stack_trace"] = traceback.format_exc()
        
        entry = self._create_entry(LogLevel.CRITICAL, message, **kwargs)
        self._log(entry)


# ============================================================================
# 健康检查
# ============================================================================

class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """组件健康状态"""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "name": self.name,
            "status": self.status.value,
        }
        
        if self.message:
            result["message"] = self.message
        if self.latency_ms is not None:
            result["latency_ms"] = self.latency_ms
        if self.details:
            result["details"] = self.details
        
        return result


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    status: HealthStatus
    components: List[ComponentHealth]
    timestamp: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "components": [c.to_dict() for c in self.components],
        }


class HealthChecker:
    """
    健康检查器
    
    检查各组件的健康状态
    """
    
    def __init__(self):
        """初始化健康检查器"""
        self._checks: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        
        logger.info("HealthChecker initialized")
    
    def register_check(
        self,
        name: str,
        check_func: Callable[[], ComponentHealth],
    ) -> None:
        """注册健康检查"""
        self._checks[name] = check_func
    
    async def check_all(self) -> HealthCheckResult:
        """执行所有健康检查"""
        components = []
        overall_status = HealthStatus.HEALTHY
        
        for name, check_func in self._checks.items():
            try:
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                result.latency_ms = (time.time() - start_time) * 1000
                components.append(result)
                
                # 更新整体状态
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED:
                    if overall_status != HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.DEGRADED
            
            except Exception as e:
                components.append(ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                ))
                overall_status = HealthStatus.UNHEALTHY
        
        return HealthCheckResult(
            status=overall_status,
            components=components,
        )
    
    async def check_component(self, name: str) -> Optional[ComponentHealth]:
        """检查单个组件"""
        if name not in self._checks:
            return None
        
        check_func = self._checks[name]
        
        try:
            start_time = time.time()
            
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            result.latency_ms = (time.time() - start_time) * 1000
            return result
        
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )


# 默认健康检查函数
async def check_database_health() -> ComponentHealth:
    """检查数据库健康"""
    # 实际实现应该执行数据库查询
    return ComponentHealth(
        name="database",
        status=HealthStatus.HEALTHY,
        message="Database connection OK",
    )


async def check_redis_health() -> ComponentHealth:
    """检查 Redis 健康"""
    # 实际实现应该执行 Redis PING
    return ComponentHealth(
        name="redis",
        status=HealthStatus.HEALTHY,
        message="Redis connection OK",
    )


async def check_neo4j_health() -> ComponentHealth:
    """检查 Neo4j 健康"""
    # 实际实现应该执行 Neo4j 查询
    return ComponentHealth(
        name="neo4j",
        status=HealthStatus.HEALTHY,
        message="Neo4j connection OK",
    )


# ============================================================================
# 装饰器
# ============================================================================

def track_request(
    endpoint: str,
    method: str = "GET",
):
    """
    请求跟踪装饰器
    
    用法:
        @track_request("/api/v1/experts", "POST")
        async def create_expert(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            slogger = get_structured_logger()
            
            start_time = time.time()
            status = "success"
            
            try:
                result = await func(*args, **kwargs)
                return result
            
            except Exception as e:
                status = "error"
                await metrics.inc_counter(
                    "ontology_api_errors_total",
                    labels={"endpoint": endpoint, "error_type": type(e).__name__},
                )
                slogger.error(
                    f"Request failed: {endpoint}",
                    error=e,
                    extra={"endpoint": endpoint, "method": method},
                )
                raise
            
            finally:
                duration = time.time() - start_time
                
                await metrics.inc_counter(
                    "ontology_api_requests_total",
                    labels={"endpoint": endpoint, "method": method, "status": status},
                )
                await metrics.observe_histogram(
                    "ontology_api_request_duration_seconds",
                    duration,
                    labels={"endpoint": endpoint, "method": method},
                )
                
                slogger.info(
                    f"Request completed: {endpoint}",
                    duration_ms=duration * 1000,
                    extra={"endpoint": endpoint, "method": method, "status": status},
                )
        
        return wrapper
    return decorator


def track_websocket_message(message_type: str):
    """
    WebSocket 消息跟踪装饰器
    
    用法:
        @track_websocket_message("element_edited")
        async def handle_edit(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            
            await metrics.inc_counter(
                "ontology_websocket_messages_total",
                labels={"message_type": message_type, "direction": "inbound"},
            )
            
            try:
                result = await func(*args, **kwargs)
                return result
            
            except Exception as e:
                logger.error(f"WebSocket message handling failed: {e}")
                raise
        
        return wrapper
    return decorator


def track_collaboration_session(func):
    """
    协作会话跟踪装饰器
    
    用法:
        @track_collaboration_session
        async def create_session(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        metrics = get_metrics_collector()
        
        await metrics.inc_counter("ontology_collaboration_sessions_total")
        
        try:
            result = await func(*args, **kwargs)
            return result
        
        except Exception as e:
            logger.error(f"Collaboration session operation failed: {e}")
            raise
    
    return wrapper


# ============================================================================
# 全局实例
# ============================================================================

_metrics_collector: Optional[PrometheusMetricsCollector] = None
_structured_logger: Optional[StructuredLogger] = None
_health_checker: Optional[HealthChecker] = None


def get_metrics_collector() -> PrometheusMetricsCollector:
    """获取或创建全局指标收集器实例"""
    global _metrics_collector
    
    if _metrics_collector is None:
        _metrics_collector = PrometheusMetricsCollector()
    
    return _metrics_collector


def get_structured_logger() -> StructuredLogger:
    """获取或创建全局结构化日志记录器实例"""
    global _structured_logger
    
    if _structured_logger is None:
        _structured_logger = StructuredLogger()
    
    return _structured_logger


def get_health_checker() -> HealthChecker:
    """获取或创建全局健康检查器实例"""
    global _health_checker
    
    if _health_checker is None:
        _health_checker = HealthChecker()
        
        # 注册默认健康检查
        _health_checker.register_check("database", check_database_health)
        _health_checker.register_check("redis", check_redis_health)
        _health_checker.register_check("neo4j", check_neo4j_health)
    
    return _health_checker
