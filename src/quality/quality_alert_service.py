"""
Quality Alert Service - 质量预警服务
发送质量预警通知
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


class QualityAlert(BaseModel):
    """质量预警"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    annotation_id: Optional[str] = None
    triggered_dimensions: List[str] = Field(default_factory=list)
    scores: Dict[str, float] = Field(default_factory=dict)
    thresholds: Dict[str, float] = Field(default_factory=dict)
    severity: str = "medium"  # critical, high, medium, low
    escalation_level: int = 0
    status: str = "open"  # open, acknowledged, resolved, silenced
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AlertConfig(BaseModel):
    """预警配置"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "accuracy": 0.8,
        "completeness": 0.9,
        "timeliness": 0.7
    })
    enabled: bool = True
    notification_channels: List[str] = Field(default_factory=lambda: ["in_app"])
    recipients: List[str] = Field(default_factory=list)
    silence_duration: int = 0  # 分钟
    silence_until: Optional[datetime] = None
    escalation_rules: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class QualityScore(BaseModel):
    """质量评分 (简化版)"""
    annotation_id: str
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    total_score: float = 0.0


class QualityAlertService:
    """质量预警服务"""
    
    def __init__(self, notification_service: Optional[Any] = None):
        """
        初始化预警服务
        
        Args:
            notification_service: 通知服务 (可选)
        """
        self.notification_service = notification_service
        
        # 内存存储
        self._configs: Dict[str, AlertConfig] = {}
        self._alerts: Dict[str, QualityAlert] = {}
        self._recipients: Dict[str, List[Dict[str, Any]]] = {}
    
    async def configure_thresholds(
        self,
        project_id: str,
        thresholds: Dict[str, float],
        notification_channels: Optional[List[str]] = None,
        recipients: Optional[List[str]] = None,
        escalation_rules: Optional[Dict[str, Any]] = None
    ) -> AlertConfig:
        """
        配置质量阈值
        
        Args:
            project_id: 项目ID
            thresholds: 各维度阈值
            notification_channels: 通知渠道
            recipients: 接收人列表
            escalation_rules: 升级规则
            
        Returns:
            预警配置
        """
        config = AlertConfig(
            project_id=project_id,
            thresholds=thresholds,
            notification_channels=notification_channels or ["in_app"],
            recipients=recipients or [],
            escalation_rules=escalation_rules or {},
            enabled=True
        )
        
        self._configs[project_id] = config
        
        return config
    
    async def get_alert_config(self, project_id: str) -> Optional[AlertConfig]:
        """获取预警配置"""
        return self._configs.get(project_id)
    
    async def update_config(
        self,
        project_id: str,
        updates: Dict[str, Any]
    ) -> Optional[AlertConfig]:
        """更新预警配置"""
        config = self._configs.get(project_id)
        if not config:
            return None
        
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        config.updated_at = datetime.utcnow()
        return config
    
    async def check_and_alert(
        self,
        project_id: str,
        score: QualityScore
    ) -> Optional[QualityAlert]:
        """
        检查并发送预警
        
        Args:
            project_id: 项目ID
            score: 质量评分
            
        Returns:
            预警对象 (如果触发)
        """
        config = await self.get_alert_config(project_id)
        
        if not config or not config.enabled:
            return None
        
        # 检查是否在静默期
        if await self._is_in_silence_period(project_id):
            return None
        
        # 检查各维度是否低于阈值
        triggered_dimensions = []
        for dimension, threshold in config.thresholds.items():
            actual_score = score.dimension_scores.get(dimension, 1.0)
            if actual_score < threshold:
                triggered_dimensions.append(dimension)
        
        if not triggered_dimensions:
            return None
        
        # 创建预警
        alert = QualityAlert(
            project_id=project_id,
            annotation_id=score.annotation_id,
            triggered_dimensions=triggered_dimensions,
            scores=score.dimension_scores,
            thresholds=config.thresholds,
            severity=self._determine_severity(triggered_dimensions, score, config.thresholds)
        )
        
        self._alerts[alert.id] = alert
        
        # 发送通知
        await self._send_alert_notification(alert, config)
        
        return alert
    
    def _determine_severity(
        self,
        triggered_dimensions: List[str],
        score: QualityScore,
        thresholds: Dict[str, float]
    ) -> str:
        """
        确定预警严重程度
        
        Args:
            triggered_dimensions: 触发的维度
            score: 质量评分
            thresholds: 阈值配置
            
        Returns:
            严重程度
        """
        if score.total_score < 0.3:
            return "critical"
        elif score.total_score < 0.5:
            return "high"
        elif score.total_score < 0.7:
            return "medium"
        else:
            return "low"
    
    async def _send_alert_notification(
        self,
        alert: QualityAlert,
        config: AlertConfig
    ) -> None:
        """发送预警通知"""
        if not self.notification_service:
            return
        
        # 获取通知接收人
        recipients = await self._get_alert_recipients(alert.project_id)
        
        for recipient in recipients:
            for channel in config.notification_channels:
                try:
                    await self.notification_service.send(
                        user_id=recipient.get("id"),
                        channel=channel,
                        title=f"质量预警 - {alert.severity.upper()}",
                        message=f"项目质量低于阈值，触发维度: {', '.join(alert.triggered_dimensions)}"
                    )
                except Exception:
                    pass
    
    async def _get_alert_recipients(self, project_id: str) -> List[Dict[str, Any]]:
        """获取预警接收人"""
        return self._recipients.get(project_id, [])
    
    def set_recipients(self, project_id: str, recipients: List[Dict[str, Any]]) -> None:
        """设置预警接收人 (用于测试)"""
        self._recipients[project_id] = recipients
    
    async def _is_in_silence_period(self, project_id: str) -> bool:
        """检查是否在静默期"""
        config = self._configs.get(project_id)
        if not config:
            return False
        
        if config.silence_until and config.silence_until > datetime.utcnow():
            return True
        
        return False
    
    async def set_silence_period(
        self,
        project_id: str,
        duration_minutes: int
    ) -> AlertConfig:
        """
        设置静默期
        
        Args:
            project_id: 项目ID
            duration_minutes: 静默时长 (分钟)
            
        Returns:
            更新后的配置
        """
        config = self._configs.get(project_id)
        if not config:
            config = AlertConfig(project_id=project_id)
            self._configs[project_id] = config
        
        config.silence_duration = duration_minutes
        config.silence_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        config.updated_at = datetime.utcnow()
        
        return config
    
    async def clear_silence_period(self, project_id: str) -> Optional[AlertConfig]:
        """清除静默期"""
        config = self._configs.get(project_id)
        if config:
            config.silence_until = None
            config.silence_duration = 0
            config.updated_at = datetime.utcnow()
        return config
    
    async def escalate_alert(self, alert_id: str) -> Optional[QualityAlert]:
        """
        升级预警
        
        Args:
            alert_id: 预警ID
            
        Returns:
            更新后的预警
        """
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        
        alert.escalation_level += 1
        
        # 获取升级接收人
        config = self._configs.get(alert.project_id)
        if config and self.notification_service:
            escalation_recipients = await self._get_escalation_recipients(
                alert.project_id, alert.escalation_level
            )
            
            for recipient in escalation_recipients:
                try:
                    await self.notification_service.send(
                        user_id=recipient.get("id"),
                        channel="email",
                        title=f"质量预警升级 - Level {alert.escalation_level}",
                        message=f"预警已升级，请立即处理"
                    )
                except Exception:
                    pass
        
        return alert
    
    async def _get_escalation_recipients(
        self,
        project_id: str,
        level: int
    ) -> List[Dict[str, Any]]:
        """获取升级接收人"""
        config = self._configs.get(project_id)
        if not config:
            return []
        
        escalation_rules = config.escalation_rules
        level_key = f"level_{level}"
        
        if level_key in escalation_rules:
            return escalation_rules[level_key].get("recipients", [])
        
        # 默认返回所有接收人
        return self._recipients.get(project_id, [])
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        user_id: str
    ) -> Optional[QualityAlert]:
        """
        确认预警
        
        Args:
            alert_id: 预警ID
            user_id: 用户ID
            
        Returns:
            更新后的预警
        """
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        
        alert.status = "acknowledged"
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.utcnow()
        
        return alert
    
    async def resolve_alert(
        self,
        alert_id: str,
        user_id: str,
        resolution_notes: Optional[str] = None
    ) -> Optional[QualityAlert]:
        """
        解决预警
        
        Args:
            alert_id: 预警ID
            user_id: 用户ID
            resolution_notes: 解决备注
            
        Returns:
            更新后的预警
        """
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        
        alert.status = "resolved"
        alert.resolved_by = user_id
        alert.resolved_at = datetime.utcnow()
        alert.resolution_notes = resolution_notes
        
        return alert
    
    async def get_alerts(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[QualityAlert]:
        """
        获取预警列表
        
        Args:
            project_id: 项目ID (可选)
            status: 状态 (可选)
            severity: 严重程度 (可选)
            
        Returns:
            预警列表
        """
        alerts = list(self._alerts.values())
        
        if project_id:
            alerts = [a for a in alerts if a.project_id == project_id]
        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts
    
    async def get_alert(self, alert_id: str) -> Optional[QualityAlert]:
        """获取单个预警"""
        return self._alerts.get(alert_id)
    
    async def send_alert(
        self,
        annotation_id: str,
        issues: List[Any]
    ) -> Optional[QualityAlert]:
        """
        发送预警 (简化接口)
        
        Args:
            annotation_id: 标注ID
            issues: 问题列表
            
        Returns:
            预警对象
        """
        # 从问题中提取项目ID (简化实现)
        project_id = "default"
        
        alert = QualityAlert(
            project_id=project_id,
            annotation_id=annotation_id,
            triggered_dimensions=["quality_check"],
            severity="high" if any(getattr(i, "severity", "") == "critical" for i in issues) else "medium"
        )
        
        self._alerts[alert.id] = alert
        
        return alert


# 独立函数 (用于属性测试)
def check_and_alert(
    scores: Dict[str, float],
    thresholds: Dict[str, float]
) -> Optional[QualityAlert]:
    """
    检查并生成预警 (同步版本，用于属性测试)
    
    Args:
        scores: 各维度分数
        thresholds: 各维度阈值
        
    Returns:
        预警对象 (如果触发)
    """
    triggered_dimensions = []
    
    for dimension, threshold in thresholds.items():
        actual_score = scores.get(dimension, 1.0)
        if actual_score < threshold:
            triggered_dimensions.append(dimension)
    
    if not triggered_dimensions:
        return None
    
    # 计算总分
    total_score = sum(scores.values()) / len(scores) if scores else 0
    
    # 确定严重程度
    if total_score < 0.3:
        severity = "critical"
    elif total_score < 0.5:
        severity = "high"
    elif total_score < 0.7:
        severity = "medium"
    else:
        severity = "low"
    
    return QualityAlert(
        project_id="test",
        triggered_dimensions=triggered_dimensions,
        scores=scores,
        thresholds=thresholds,
        severity=severity
    )
