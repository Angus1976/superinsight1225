"""
服务不健康告警模块
检测服务状态变化并触发告警通知

**Feature: system-optimization**
**Validates: Requirements 13.4**
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import threading

from src.i18n.translations import t
from src.monitoring.health_check import (
    HealthCheckManager,
    HealthStatus,
    ServiceHealthResult,
    health_check_manager
)
from src.monitoring.alert_config import (
    AlertSeverity,
    AlertInstance,
    AlertStatus,
    alert_config_manager
)
from src.monitoring.prometheus_metrics import (
    update_service_health,
    record_notification_sent
)

logger = logging.getLogger(__name__)


# ============================================================================
# 服务状态变化事件
# ============================================================================

class ServiceStateChange(str, Enum):
    """服务状态变化类型"""
    HEALTHY_TO_DEGRADED = "healthy_to_degraded"
    HEALTHY_TO_UNHEALTHY = "healthy_to_unhealthy"
    DEGRADED_TO_HEALTHY = "degraded_to_healthy"
    DEGRADED_TO_UNHEALTHY = "degraded_to_unhealthy"
    UNHEALTHY_TO_HEALTHY = "unhealthy_to_healthy"
    UNHEALTHY_TO_DEGRADED = "unhealthy_to_degraded"
    NO_CHANGE = "no_change"


@dataclass
class ServiceStateEvent:
    """
    服务状态变化事件
    """
    id: UUID = field(default_factory=uuid4)
    service_name: str = ""
    previous_status: HealthStatus = HealthStatus.HEALTHY
    current_status: HealthStatus = HealthStatus.HEALTHY
    change_type: ServiceStateChange = ServiceStateChange.NO_CHANGE
    timestamp: datetime = field(default_factory=datetime.now)
    latency_ms: float = 0.0
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "service_name": self.service_name,
            "previous_status": self.previous_status.value,
            "current_status": self.current_status.value,
            "change_type": self.change_type.value,
            "timestamp": self.timestamp.isoformat(),
            "latency_ms": self.latency_ms,
            "message": self.message,
            "details": self.details
        }


# ============================================================================
# 服务告警配置
# ============================================================================

@dataclass
class ServiceAlertConfig:
    """
    服务告警配置
    """
    # 检查间隔（秒）
    check_interval_seconds: int = 30
    
    # 连续失败次数阈值
    consecutive_failures_threshold: int = 3
    
    # 恢复确认次数
    recovery_confirmation_count: int = 2
    
    # 告警冷却时间（秒）
    alert_cooldown_seconds: int = 300
    
    # 是否启用自动恢复通知
    notify_on_recovery: bool = True
    
    # 严重程度映射
    severity_mapping: Dict[ServiceStateChange, AlertSeverity] = field(default_factory=lambda: {
        ServiceStateChange.HEALTHY_TO_DEGRADED: AlertSeverity.WARNING,
        ServiceStateChange.HEALTHY_TO_UNHEALTHY: AlertSeverity.CRITICAL,
        ServiceStateChange.DEGRADED_TO_UNHEALTHY: AlertSeverity.CRITICAL,
        ServiceStateChange.DEGRADED_TO_HEALTHY: AlertSeverity.INFO,
        ServiceStateChange.UNHEALTHY_TO_HEALTHY: AlertSeverity.INFO,
        ServiceStateChange.UNHEALTHY_TO_DEGRADED: AlertSeverity.WARNING,
    })


# ============================================================================
# 服务状态追踪器
# ============================================================================

@dataclass
class ServiceStateTracker:
    """
    服务状态追踪器
    
    追踪单个服务的状态变化
    """
    service_name: str
    current_status: HealthStatus = HealthStatus.HEALTHY
    previous_status: HealthStatus = HealthStatus.HEALTHY
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_check_time: Optional[datetime] = None
    last_alert_time: Optional[datetime] = None
    last_state_change_time: Optional[datetime] = None
    total_checks: int = 0
    total_failures: int = 0
    
    def update(self, result: ServiceHealthResult) -> Optional[ServiceStateEvent]:
        """
        更新服务状态
        
        Args:
            result: 健康检查结果
            
        Returns:
            状态变化事件（如果有变化）
        """
        self.total_checks += 1
        self.last_check_time = datetime.now()
        
        new_status = result.status
        
        # 更新连续计数
        if new_status == HealthStatus.HEALTHY:
            self.consecutive_successes += 1
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            self.total_failures += 1
        
        # 检查状态变化
        if new_status != self.current_status:
            change_type = self._determine_change_type(self.current_status, new_status)
            
            event = ServiceStateEvent(
                service_name=self.service_name,
                previous_status=self.current_status,
                current_status=new_status,
                change_type=change_type,
                timestamp=datetime.now(),
                latency_ms=result.latency_ms,
                message=result.message,
                details=result.details
            )
            
            self.previous_status = self.current_status
            self.current_status = new_status
            self.last_state_change_time = datetime.now()
            
            return event
        
        return None
    
    def _determine_change_type(
        self,
        old_status: HealthStatus,
        new_status: HealthStatus
    ) -> ServiceStateChange:
        """确定状态变化类型"""
        if old_status == HealthStatus.HEALTHY:
            if new_status == HealthStatus.DEGRADED:
                return ServiceStateChange.HEALTHY_TO_DEGRADED
            elif new_status == HealthStatus.UNHEALTHY:
                return ServiceStateChange.HEALTHY_TO_UNHEALTHY
        elif old_status == HealthStatus.DEGRADED:
            if new_status == HealthStatus.HEALTHY:
                return ServiceStateChange.DEGRADED_TO_HEALTHY
            elif new_status == HealthStatus.UNHEALTHY:
                return ServiceStateChange.DEGRADED_TO_UNHEALTHY
        elif old_status == HealthStatus.UNHEALTHY:
            if new_status == HealthStatus.HEALTHY:
                return ServiceStateChange.UNHEALTHY_TO_HEALTHY
            elif new_status == HealthStatus.DEGRADED:
                return ServiceStateChange.UNHEALTHY_TO_DEGRADED
        
        return ServiceStateChange.NO_CHANGE
    
    def should_alert(self, config: ServiceAlertConfig) -> bool:
        """
        判断是否应该发送告警
        
        Args:
            config: 告警配置
            
        Returns:
            是否应该发送告警
        """
        # 检查连续失败次数
        if self.consecutive_failures < config.consecutive_failures_threshold:
            return False
        
        # 检查冷却时间
        if self.last_alert_time:
            elapsed = (datetime.now() - self.last_alert_time).total_seconds()
            if elapsed < config.alert_cooldown_seconds:
                return False
        
        return True
    
    def should_notify_recovery(self, config: ServiceAlertConfig) -> bool:
        """
        判断是否应该发送恢复通知
        
        Args:
            config: 告警配置
            
        Returns:
            是否应该发送恢复通知
        """
        if not config.notify_on_recovery:
            return False
        
        # 检查连续成功次数
        if self.consecutive_successes < config.recovery_confirmation_count:
            return False
        
        # 检查之前是否有告警
        if not self.last_alert_time:
            return False
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "service_name": self.service_name,
            "current_status": self.current_status.value,
            "previous_status": self.previous_status.value,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "total_checks": self.total_checks,
            "total_failures": self.total_failures,
            "failure_rate": self.total_failures / self.total_checks if self.total_checks > 0 else 0,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "last_alert_time": self.last_alert_time.isoformat() if self.last_alert_time else None,
            "last_state_change_time": self.last_state_change_time.isoformat() if self.last_state_change_time else None
        }


# ============================================================================
# 服务告警管理器
# ============================================================================

class ServiceAlertManager:
    """
    服务告警管理器
    
    监控服务健康状态并触发告警
    """
    
    def __init__(
        self,
        health_manager: Optional[HealthCheckManager] = None,
        config: Optional[ServiceAlertConfig] = None
    ):
        self._health_manager = health_manager or health_check_manager
        self._config = config or ServiceAlertConfig()
        self._trackers: Dict[str, ServiceStateTracker] = {}
        self._event_history: List[ServiceStateEvent] = []
        self._is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        self._alert_callbacks: List[Callable[[ServiceStateEvent], Awaitable[None]]] = []
        self._recovery_callbacks: List[Callable[[ServiceStateEvent], Awaitable[None]]] = []
    
    # ========================================================================
    # 监控控制
    # ========================================================================
    
    async def start_monitoring(self):
        """启动监控"""
        if self._is_monitoring:
            logger.warning(t('monitoring.service_alert.already_monitoring'))
            return
        
        self._is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info(t('monitoring.service_alert.monitoring_started'))
    
    async def stop_monitoring(self):
        """停止监控"""
        self._is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info(t('monitoring.service_alert.monitoring_stopped'))
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self._is_monitoring:
            try:
                await self._check_all_services()
                await asyncio.sleep(self._config.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(t('monitoring.service_alert.monitoring_error', error=str(e)))
                await asyncio.sleep(self._config.check_interval_seconds)
    
    async def _check_all_services(self):
        """检查所有服务"""
        response = await self._health_manager.check_all()
        
        for service_name, result in response.services.items():
            await self._process_service_result(service_name, result)
    
    async def _process_service_result(
        self,
        service_name: str,
        result: ServiceHealthResult
    ):
        """
        处理服务检查结果
        
        Args:
            service_name: 服务名称
            result: 健康检查结果
        """
        # 获取或创建追踪器
        with self._lock:
            if service_name not in self._trackers:
                self._trackers[service_name] = ServiceStateTracker(service_name=service_name)
            tracker = self._trackers[service_name]
        
        # 更新状态
        event = tracker.update(result)
        
        # 更新 Prometheus 指标
        update_service_health(service_name, result.status == HealthStatus.HEALTHY)
        
        if event:
            # 记录事件
            with self._lock:
                self._event_history.append(event)
                # 保留最近 1000 条记录
                if len(self._event_history) > 1000:
                    self._event_history = self._event_history[-1000:]
            
            # 处理状态变化
            await self._handle_state_change(tracker, event)
    
    async def _handle_state_change(
        self,
        tracker: ServiceStateTracker,
        event: ServiceStateEvent
    ):
        """
        处理状态变化
        
        Args:
            tracker: 状态追踪器
            event: 状态变化事件
        """
        # 判断是否需要告警
        is_degradation = event.change_type in [
            ServiceStateChange.HEALTHY_TO_DEGRADED,
            ServiceStateChange.HEALTHY_TO_UNHEALTHY,
            ServiceStateChange.DEGRADED_TO_UNHEALTHY
        ]
        
        is_recovery = event.change_type in [
            ServiceStateChange.UNHEALTHY_TO_HEALTHY,
            ServiceStateChange.UNHEALTHY_TO_DEGRADED,
            ServiceStateChange.DEGRADED_TO_HEALTHY
        ]
        
        if is_degradation and tracker.should_alert(self._config):
            await self._trigger_alert(tracker, event)
        elif is_recovery and tracker.should_notify_recovery(self._config):
            await self._trigger_recovery(tracker, event)
    
    async def _trigger_alert(
        self,
        tracker: ServiceStateTracker,
        event: ServiceStateEvent
    ):
        """
        触发告警
        
        Args:
            tracker: 状态追踪器
            event: 状态变化事件
        """
        tracker.last_alert_time = datetime.now()
        
        severity = self._config.severity_mapping.get(
            event.change_type,
            AlertSeverity.WARNING
        )
        
        logger.warning(
            t('monitoring.service_alert.alert_triggered',
              service=event.service_name,
              status=event.current_status.value,
              severity=severity.value)
        )
        
        # 触发回调
        for callback in self._alert_callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.error(t('monitoring.service_alert.callback_error', error=str(e)))
        
        # 记录通知发送
        record_notification_sent("service_alert", True)
    
    async def _trigger_recovery(
        self,
        tracker: ServiceStateTracker,
        event: ServiceStateEvent
    ):
        """
        触发恢复通知
        
        Args:
            tracker: 状态追踪器
            event: 状态变化事件
        """
        logger.info(
            t('monitoring.service_alert.recovery_triggered',
              service=event.service_name,
              status=event.current_status.value)
        )
        
        # 触发回调
        for callback in self._recovery_callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.error(t('monitoring.service_alert.callback_error', error=str(e)))
        
        # 记录通知发送
        record_notification_sent("service_recovery", True)
    
    # ========================================================================
    # 回调管理
    # ========================================================================
    
    def register_alert_callback(
        self,
        callback: Callable[[ServiceStateEvent], Awaitable[None]]
    ):
        """注册告警回调"""
        self._alert_callbacks.append(callback)
    
    def register_recovery_callback(
        self,
        callback: Callable[[ServiceStateEvent], Awaitable[None]]
    ):
        """注册恢复回调"""
        self._recovery_callbacks.append(callback)
    
    def unregister_alert_callback(
        self,
        callback: Callable[[ServiceStateEvent], Awaitable[None]]
    ):
        """取消注册告警回调"""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
    
    def unregister_recovery_callback(
        self,
        callback: Callable[[ServiceStateEvent], Awaitable[None]]
    ):
        """取消注册恢复回调"""
        if callback in self._recovery_callbacks:
            self._recovery_callbacks.remove(callback)
    
    # ========================================================================
    # 配置管理
    # ========================================================================
    
    def update_config(self, config: ServiceAlertConfig):
        """更新配置"""
        self._config = config
        logger.info(t('monitoring.service_alert.config_updated'))
    
    def get_config(self) -> ServiceAlertConfig:
        """获取配置"""
        return self._config
    
    def set_check_interval(self, seconds: int):
        """设置检查间隔"""
        self._config.check_interval_seconds = seconds
    
    def set_failure_threshold(self, count: int):
        """设置失败阈值"""
        self._config.consecutive_failures_threshold = count
    
    def set_cooldown(self, seconds: int):
        """设置冷却时间"""
        self._config.alert_cooldown_seconds = seconds
    
    # ========================================================================
    # 状态查询
    # ========================================================================
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务状态"""
        with self._lock:
            tracker = self._trackers.get(service_name)
            if tracker:
                return tracker.get_statistics()
            return None
    
    def get_all_service_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务状态"""
        with self._lock:
            return {
                name: tracker.get_statistics()
                for name, tracker in self._trackers.items()
            }
    
    def get_unhealthy_services(self) -> List[str]:
        """获取不健康的服务列表"""
        with self._lock:
            return [
                name for name, tracker in self._trackers.items()
                if tracker.current_status == HealthStatus.UNHEALTHY
            ]
    
    def get_degraded_services(self) -> List[str]:
        """获取降级的服务列表"""
        with self._lock:
            return [
                name for name, tracker in self._trackers.items()
                if tracker.current_status == HealthStatus.DEGRADED
            ]
    
    def get_event_history(
        self,
        limit: int = 100,
        service_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取事件历史
        
        Args:
            limit: 返回数量限制
            service_name: 按服务名称过滤
            
        Returns:
            事件历史列表
        """
        with self._lock:
            events = self._event_history.copy()
        
        if service_name:
            events = [e for e in events if e.service_name == service_name]
        
        # 按时间倒序
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [e.to_dict() for e in events[:limit]]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            total_services = len(self._trackers)
            healthy_count = len([
                t for t in self._trackers.values()
                if t.current_status == HealthStatus.HEALTHY
            ])
            degraded_count = len([
                t for t in self._trackers.values()
                if t.current_status == HealthStatus.DEGRADED
            ])
            unhealthy_count = len([
                t for t in self._trackers.values()
                if t.current_status == HealthStatus.UNHEALTHY
            ])
            
            return {
                "is_monitoring": self._is_monitoring,
                "total_services": total_services,
                "healthy_count": healthy_count,
                "degraded_count": degraded_count,
                "unhealthy_count": unhealthy_count,
                "event_history_count": len(self._event_history),
                "config": {
                    "check_interval_seconds": self._config.check_interval_seconds,
                    "consecutive_failures_threshold": self._config.consecutive_failures_threshold,
                    "alert_cooldown_seconds": self._config.alert_cooldown_seconds,
                    "notify_on_recovery": self._config.notify_on_recovery
                }
            }


# ============================================================================
# 全局服务告警管理器
# ============================================================================

# 全局实例
service_alert_manager = ServiceAlertManager()


# ============================================================================
# 辅助函数
# ============================================================================

async def check_service_health(service_name: str) -> Optional[ServiceHealthResult]:
    """
    检查单个服务健康状态
    
    Args:
        service_name: 服务名称
        
    Returns:
        健康检查结果
    """
    return await health_check_manager.check_service(service_name)


async def get_overall_health() -> Dict[str, Any]:
    """
    获取整体健康状态
    
    Returns:
        整体健康状态
    """
    response = await health_check_manager.check_all()
    return {
        "status": response.status.value,
        "timestamp": response.timestamp.isoformat(),
        "services": {
            name: {
                "status": result.status.value,
                "latency_ms": result.latency_ms,
                "message": result.message
            }
            for name, result in response.services.items()
        },
        "version": response.version,
        "uptime_seconds": response.uptime_seconds
    }


def is_any_service_unhealthy() -> bool:
    """
    检查是否有任何服务不健康
    
    Returns:
        是否有不健康的服务
    """
    return len(service_alert_manager.get_unhealthy_services()) > 0


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 枚举
    "ServiceStateChange",
    # 数据类
    "ServiceStateEvent",
    "ServiceAlertConfig",
    "ServiceStateTracker",
    # 管理器
    "ServiceAlertManager",
    # 全局实例
    "service_alert_manager",
    # 辅助函数
    "check_service_health",
    "get_overall_health",
    "is_any_service_unhealthy",
]
