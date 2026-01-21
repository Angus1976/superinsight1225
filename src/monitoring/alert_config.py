"""
告警配置模块
支持可配置的告警阈值和动态更新

**Feature: system-optimization**
**Validates: Requirements 13.2**
"""

import logging
import json
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
import threading
import asyncio

from pydantic import BaseModel, Field, validator

from src.i18n.translations import t

logger = logging.getLogger(__name__)


# ============================================================================
# 告警配置模型
# ============================================================================

class AlertOperator(str, Enum):
    """告警比较运算符"""
    GT = "gt"       # 大于
    LT = "lt"       # 小于
    EQ = "eq"       # 等于
    GTE = "gte"     # 大于等于
    LTE = "lte"     # 小于等于
    NE = "ne"       # 不等于


class AlertSeverity(str, Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """告警状态"""
    PENDING = "pending"       # 等待触发
    FIRING = "firing"         # 正在触发
    RESOLVED = "resolved"     # 已解决


class AlertThreshold(BaseModel):
    """
    告警阈值配置
    
    定义单个告警规则的阈值条件
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    metric_name: str = Field(..., description="指标名称")
    operator: AlertOperator = Field(..., description="比较运算符")
    value: float = Field(..., description="阈值")
    duration_seconds: int = Field(default=0, description="持续时间（秒）")
    severity: AlertSeverity = Field(default=AlertSeverity.WARNING, description="严重程度")
    enabled: bool = Field(default=True, description="是否启用")
    labels: Dict[str, str] = Field(default_factory=dict, description="标签过滤")
    description: str = Field(default="", description="告警描述")
    
    @validator('duration_seconds')
    def validate_duration(cls, v):
        if v < 0:
            raise ValueError(t('monitoring.alert.invalid_duration'))
        return v
    
    @validator('value')
    def validate_value(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError(t('monitoring.alert.invalid_value'))
        return float(v)
    
    def evaluate(self, current_value: float) -> bool:
        """
        评估当前值是否触发告警
        
        Args:
            current_value: 当前指标值
            
        Returns:
            是否触发告警
        """
        if self.operator == AlertOperator.GT:
            return current_value > self.value
        elif self.operator == AlertOperator.LT:
            return current_value < self.value
        elif self.operator == AlertOperator.EQ:
            return current_value == self.value
        elif self.operator == AlertOperator.GTE:
            return current_value >= self.value
        elif self.operator == AlertOperator.LTE:
            return current_value <= self.value
        elif self.operator == AlertOperator.NE:
            return current_value != self.value
        return False


class AlertConfig(BaseModel):
    """
    告警配置
    
    包含多个告警阈值和通知配置
    """
    thresholds: List[AlertThreshold] = Field(default_factory=list, description="告警阈值列表")
    notification_channels: List[str] = Field(default_factory=list, description="通知渠道")
    cooldown_seconds: int = Field(default=300, description="告警冷却时间（秒）")
    max_alerts_per_hour: int = Field(default=100, description="每小时最大告警数")
    
    @validator('cooldown_seconds')
    def validate_cooldown(cls, v):
        if v < 0:
            raise ValueError(t('monitoring.alert.invalid_cooldown'))
        return v
    
    @validator('max_alerts_per_hour')
    def validate_max_alerts(cls, v):
        if v < 1:
            raise ValueError(t('monitoring.alert.invalid_max_alerts'))
        return v


# ============================================================================
# 告警实例
# ============================================================================

@dataclass
class AlertInstance:
    """
    告警实例
    
    表示一个正在触发或已解决的告警
    """
    id: UUID = field(default_factory=uuid4)
    threshold_id: str = ""
    metric_name: str = ""
    current_value: float = 0.0
    threshold_value: float = 0.0
    operator: AlertOperator = AlertOperator.GT
    severity: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.PENDING
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    last_notified_at: Optional[datetime] = None
    notification_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id),
            "threshold_id": self.threshold_id,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "operator": self.operator.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "labels": self.labels,
            "description": self.description,
            "started_at": self.started_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "last_notified_at": self.last_notified_at.isoformat() if self.last_notified_at else None,
            "notification_count": self.notification_count
        }


# ============================================================================
# 告警配置管理器
# ============================================================================

class AlertConfigManager:
    """
    告警配置管理器
    
    管理告警阈值配置，支持动态更新
    """
    
    def __init__(self, config: Optional[AlertConfig] = None):
        self._config = config or AlertConfig()
        self._thresholds: Dict[str, AlertThreshold] = {}
        self._active_alerts: Dict[str, AlertInstance] = {}
        self._alert_history: List[AlertInstance] = []
        self._pending_durations: Dict[str, datetime] = {}  # 用于持续时间检查
        self._last_alert_times: Dict[str, datetime] = {}  # 用于冷却时间
        self._alert_count_per_hour: int = 0
        self._hour_start: datetime = datetime.now()
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[AlertInstance], None]] = []
        
        # 初始化阈值
        for threshold in self._config.thresholds:
            self._thresholds[threshold.id] = threshold
    
    # ========================================================================
    # 阈值管理
    # ========================================================================
    
    def add_threshold(self, threshold: AlertThreshold) -> str:
        """
        添加告警阈值
        
        Args:
            threshold: 告警阈值配置
            
        Returns:
            阈值 ID
        """
        with self._lock:
            self._thresholds[threshold.id] = threshold
            logger.info(t('monitoring.alert.threshold_added', id=threshold.id))
            return threshold.id
    
    def update_threshold(self, threshold_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新告警阈值
        
        Args:
            threshold_id: 阈值 ID
            updates: 更新内容
            
        Returns:
            是否更新成功
        """
        with self._lock:
            if threshold_id not in self._thresholds:
                logger.warning(t('monitoring.alert.threshold_not_found', id=threshold_id))
                return False
            
            threshold = self._thresholds[threshold_id]
            
            # 更新字段
            for key, value in updates.items():
                if hasattr(threshold, key):
                    setattr(threshold, key, value)
            
            logger.info(t('monitoring.alert.threshold_updated', id=threshold_id))
            return True
    
    def remove_threshold(self, threshold_id: str) -> bool:
        """
        移除告警阈值
        
        Args:
            threshold_id: 阈值 ID
            
        Returns:
            是否移除成功
        """
        with self._lock:
            if threshold_id not in self._thresholds:
                return False
            
            del self._thresholds[threshold_id]
            logger.info(t('monitoring.alert.threshold_removed', id=threshold_id))
            return True
    
    def get_threshold(self, threshold_id: str) -> Optional[AlertThreshold]:
        """获取告警阈值"""
        with self._lock:
            return self._thresholds.get(threshold_id)
    
    def get_all_thresholds(self) -> List[AlertThreshold]:
        """获取所有告警阈值"""
        with self._lock:
            return list(self._thresholds.values())
    
    def enable_threshold(self, threshold_id: str) -> bool:
        """启用告警阈值"""
        return self.update_threshold(threshold_id, {"enabled": True})
    
    def disable_threshold(self, threshold_id: str) -> bool:
        """禁用告警阈值"""
        return self.update_threshold(threshold_id, {"enabled": False})
    
    # ========================================================================
    # 告警评估
    # ========================================================================
    
    def evaluate_metric(
        self,
        metric_name: str,
        current_value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> List[AlertInstance]:
        """
        评估指标值是否触发告警
        
        Args:
            metric_name: 指标名称
            current_value: 当前值
            labels: 标签
            
        Returns:
            触发的告警列表
        """
        triggered_alerts = []
        now = datetime.now()
        
        # 检查每小时告警限制
        self._check_hourly_limit()
        
        with self._lock:
            for threshold in self._thresholds.values():
                if not threshold.enabled:
                    continue
                
                if threshold.metric_name != metric_name:
                    continue
                
                # 检查标签匹配
                if threshold.labels and labels:
                    if not all(labels.get(k) == v for k, v in threshold.labels.items()):
                        continue
                
                # 评估阈值
                is_triggered = threshold.evaluate(current_value)
                alert_key = f"{threshold.id}:{metric_name}:{json.dumps(labels or {}, sort_keys=True)}"
                
                if is_triggered:
                    # 检查持续时间
                    if threshold.duration_seconds > 0:
                        if alert_key not in self._pending_durations:
                            self._pending_durations[alert_key] = now
                            continue
                        
                        elapsed = (now - self._pending_durations[alert_key]).total_seconds()
                        if elapsed < threshold.duration_seconds:
                            continue
                    
                    # 检查冷却时间
                    if alert_key in self._last_alert_times:
                        elapsed = (now - self._last_alert_times[alert_key]).total_seconds()
                        if elapsed < self._config.cooldown_seconds:
                            continue
                    
                    # 检查每小时限制
                    if self._alert_count_per_hour >= self._config.max_alerts_per_hour:
                        logger.warning(t('monitoring.alert.hourly_limit_reached'))
                        continue
                    
                    # 创建或更新告警实例
                    if alert_key in self._active_alerts:
                        alert = self._active_alerts[alert_key]
                        alert.current_value = current_value
                    else:
                        alert = AlertInstance(
                            threshold_id=threshold.id,
                            metric_name=metric_name,
                            current_value=current_value,
                            threshold_value=threshold.value,
                            operator=threshold.operator,
                            severity=threshold.severity,
                            status=AlertStatus.FIRING,
                            labels=labels or {},
                            description=threshold.description,
                            started_at=now
                        )
                        self._active_alerts[alert_key] = alert
                        self._alert_count_per_hour += 1
                    
                    self._last_alert_times[alert_key] = now
                    triggered_alerts.append(alert)
                    
                    # 触发回调
                    self._trigger_callbacks(alert)
                    
                else:
                    # 清除待处理状态
                    if alert_key in self._pending_durations:
                        del self._pending_durations[alert_key]
                    
                    # 解决告警
                    if alert_key in self._active_alerts:
                        alert = self._active_alerts[alert_key]
                        alert.status = AlertStatus.RESOLVED
                        alert.resolved_at = now
                        self._alert_history.append(alert)
                        del self._active_alerts[alert_key]
                        
                        # 触发回调
                        self._trigger_callbacks(alert)
        
        return triggered_alerts
    
    def _check_hourly_limit(self):
        """检查并重置每小时告警计数"""
        now = datetime.now()
        if (now - self._hour_start).total_seconds() >= 3600:
            self._alert_count_per_hour = 0
            self._hour_start = now
    
    def _trigger_callbacks(self, alert: AlertInstance):
        """触发告警回调"""
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(t('monitoring.alert.callback_error', error=str(e)))
    
    # ========================================================================
    # 告警管理
    # ========================================================================
    
    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        metric_name: Optional[str] = None
    ) -> List[AlertInstance]:
        """
        获取活跃告警
        
        Args:
            severity: 按严重程度过滤
            metric_name: 按指标名称过滤
            
        Returns:
            活跃告警列表
        """
        with self._lock:
            alerts = list(self._active_alerts.values())
            
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            
            if metric_name:
                alerts = [a for a in alerts if a.metric_name == metric_name]
            
            return alerts
    
    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None
    ) -> List[AlertInstance]:
        """
        获取告警历史
        
        Args:
            limit: 返回数量限制
            severity: 按严重程度过滤
            
        Returns:
            告警历史列表
        """
        with self._lock:
            alerts = self._alert_history.copy()
            
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            
            # 按时间倒序
            alerts.sort(key=lambda x: x.started_at, reverse=True)
            
            return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        确认告警
        
        Args:
            alert_id: 告警 ID
            
        Returns:
            是否确认成功
        """
        with self._lock:
            for key, alert in self._active_alerts.items():
                if str(alert.id) == alert_id:
                    alert.last_notified_at = datetime.now()
                    alert.notification_count += 1
                    logger.info(t('monitoring.alert.acknowledged', id=alert_id))
                    return True
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        手动解决告警
        
        Args:
            alert_id: 告警 ID
            
        Returns:
            是否解决成功
        """
        with self._lock:
            for key, alert in list(self._active_alerts.items()):
                if str(alert.id) == alert_id:
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.now()
                    self._alert_history.append(alert)
                    del self._active_alerts[key]
                    logger.info(t('monitoring.alert.resolved', id=alert_id))
                    return True
            return False
    
    # ========================================================================
    # 配置管理
    # ========================================================================
    
    def update_config(self, config: AlertConfig):
        """更新告警配置"""
        with self._lock:
            self._config = config
            
            # 更新阈值
            self._thresholds.clear()
            for threshold in config.thresholds:
                self._thresholds[threshold.id] = threshold
            
            logger.info(t('monitoring.alert.config_updated'))
    
    def get_config(self) -> AlertConfig:
        """获取当前配置"""
        with self._lock:
            return self._config
    
    def set_cooldown(self, seconds: int):
        """设置冷却时间"""
        with self._lock:
            self._config.cooldown_seconds = seconds
            logger.info(t('monitoring.alert.cooldown_updated', seconds=seconds))
    
    def set_max_alerts_per_hour(self, max_alerts: int):
        """设置每小时最大告警数"""
        with self._lock:
            self._config.max_alerts_per_hour = max_alerts
            logger.info(t('monitoring.alert.max_alerts_updated', max_alerts=max_alerts))
    
    def add_notification_channel(self, channel: str):
        """添加通知渠道"""
        with self._lock:
            if channel not in self._config.notification_channels:
                self._config.notification_channels.append(channel)
                logger.info(t('monitoring.alert.channel_added', channel=channel))
    
    def remove_notification_channel(self, channel: str):
        """移除通知渠道"""
        with self._lock:
            if channel in self._config.notification_channels:
                self._config.notification_channels.remove(channel)
                logger.info(t('monitoring.alert.channel_removed', channel=channel))
    
    # ========================================================================
    # 回调管理
    # ========================================================================
    
    def register_callback(self, callback: Callable[[AlertInstance], None]):
        """注册告警回调"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[AlertInstance], None]):
        """取消注册告警回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    # ========================================================================
    # 统计信息
    # ========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取告警统计信息"""
        with self._lock:
            active_by_severity = {}
            for severity in AlertSeverity:
                active_by_severity[severity.value] = len([
                    a for a in self._active_alerts.values()
                    if a.severity == severity
                ])
            
            return {
                "total_thresholds": len(self._thresholds),
                "enabled_thresholds": len([t for t in self._thresholds.values() if t.enabled]),
                "active_alerts": len(self._active_alerts),
                "active_by_severity": active_by_severity,
                "alerts_this_hour": self._alert_count_per_hour,
                "max_alerts_per_hour": self._config.max_alerts_per_hour,
                "cooldown_seconds": self._config.cooldown_seconds,
                "notification_channels": self._config.notification_channels,
                "history_count": len(self._alert_history)
            }


# ============================================================================
# 全局告警配置管理器
# ============================================================================

# 默认告警阈值
DEFAULT_THRESHOLDS = [
    AlertThreshold(
        id="api_error_rate_high",
        metric_name="superinsight_api_errors_total",
        operator=AlertOperator.GT,
        value=100,
        duration_seconds=60,
        severity=AlertSeverity.WARNING,
        description="API 错误率过高"
    ),
    AlertThreshold(
        id="api_error_rate_critical",
        metric_name="superinsight_api_errors_total",
        operator=AlertOperator.GT,
        value=500,
        duration_seconds=60,
        severity=AlertSeverity.CRITICAL,
        description="API 错误率严重过高"
    ),
    AlertThreshold(
        id="cache_hit_rate_low",
        metric_name="superinsight_cache_hit_rate",
        operator=AlertOperator.LT,
        value=0.8,
        duration_seconds=300,
        severity=AlertSeverity.WARNING,
        description="缓存命中率过低"
    ),
    AlertThreshold(
        id="db_query_slow",
        metric_name="superinsight_db_query_duration_seconds",
        operator=AlertOperator.GT,
        value=1.0,
        duration_seconds=0,
        severity=AlertSeverity.WARNING,
        description="数据库查询过慢"
    ),
    AlertThreshold(
        id="service_unhealthy",
        metric_name="superinsight_service_health",
        operator=AlertOperator.EQ,
        value=0,
        duration_seconds=30,
        severity=AlertSeverity.CRITICAL,
        description="服务不健康"
    ),
]

# 默认配置
DEFAULT_CONFIG = AlertConfig(
    thresholds=DEFAULT_THRESHOLDS,
    notification_channels=["email", "wechat_work"],
    cooldown_seconds=300,
    max_alerts_per_hour=100
)

# 全局实例
alert_config_manager = AlertConfigManager(DEFAULT_CONFIG)


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 枚举
    "AlertOperator",
    "AlertSeverity",
    "AlertStatus",
    # 模型
    "AlertThreshold",
    "AlertConfig",
    "AlertInstance",
    # 管理器
    "AlertConfigManager",
    # 全局实例
    "alert_config_manager",
    # 默认配置
    "DEFAULT_THRESHOLDS",
    "DEFAULT_CONFIG",
]
