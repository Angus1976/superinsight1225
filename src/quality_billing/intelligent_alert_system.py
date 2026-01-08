"""
智能告警系统 - 全面告警管理

提供多维度告警规则、告警聚合、升级处理等功能。
支持质量、效率、成本等多维度告警管理。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import json
import statistics
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class AlertDimension(str, Enum):
    """告警维度"""
    QUALITY = "quality"          # 质量维度
    EFFICIENCY = "efficiency"    # 效率维度
    COST = "cost"               # 成本维度
    PERFORMANCE = "performance"  # 性能维度
    SECURITY = "security"       # 安全维度
    COMPLIANCE = "compliance"   # 合规维度


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertPriority(int, Enum):
    """告警优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class AlertRuleType(str, Enum):
    """告警规则类型"""
    THRESHOLD = "threshold"      # 阈值告警
    TREND = "trend"             # 趋势告警
    ANOMALY = "anomaly"         # 异常检测
    COMPOSITE = "composite"     # 复合告警
    PATTERN = "pattern"         # 模式匹配


class AlertStatus(str, Enum):
    """告警状态"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"
    ESCALATED = "escalated"


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    dimension: AlertDimension
    rule_type: AlertRuleType
    level: AlertLevel
    priority: AlertPriority
    enabled: bool = True
    
    # 规则条件
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # 阈值配置
    threshold_config: Optional[Dict[str, Any]] = None
    
    # 趋势配置
    trend_config: Optional[Dict[str, Any]] = None
    
    # 异常检测配置
    anomaly_config: Optional[Dict[str, Any]] = None
    
    # 复合规则配置
    composite_config: Optional[Dict[str, Any]] = None
    
    # 告警抑制配置
    suppression_config: Optional[Dict[str, Any]] = None
    
    # 升级配置
    escalation_config: Optional[Dict[str, Any]] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "dimension": self.dimension.value,
            "rule_type": self.rule_type.value,
            "level": self.level.value,
            "priority": self.priority.value,
            "enabled": self.enabled,
            "conditions": self.conditions,
            "threshold_config": self.threshold_config,
            "trend_config": self.trend_config,
            "anomaly_config": self.anomaly_config,
            "composite_config": self.composite_config,
            "suppression_config": self.suppression_config,
            "escalation_config": self.escalation_config,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class Alert:
    """告警记录"""
    id: UUID
    rule_id: str
    dimension: AlertDimension
    level: AlertLevel
    priority: AlertPriority
    title: str
    message: str
    source: str
    status: AlertStatus = AlertStatus.ACTIVE
    
    # 关联信息
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # 告警数据
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None
    
    # 上下文信息
    context: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    escalated_at: Optional[datetime] = None
    
    # 处理信息
    notifications_sent: List[str] = field(default_factory=list)
    escalation_level: int = 0
    suppressed_until: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "rule_id": self.rule_id,
            "dimension": self.dimension.value,
            "level": self.level.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "status": self.status.value,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold_value": self.threshold_value,
            "context": self.context,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "escalated_at": self.escalated_at.isoformat() if self.escalated_at else None,
            "notifications_sent": self.notifications_sent,
            "escalation_level": self.escalation_level,
            "suppressed_until": self.suppressed_until.isoformat() if self.suppressed_until else None
        }


class MultiDimensionalAlertRuleEngine:
    """多维度告警规则引擎"""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
    def create_quality_alert_rule(
        self,
        name: str,
        quality_threshold: float = 0.8,
        trend_window: int = 10,
        level: AlertLevel = AlertLevel.WARNING
    ) -> AlertRule:
        """创建质量告警规则"""
        rule_id = f"quality_{uuid4().hex[:8]}"
        
        rule = AlertRule(
            id=rule_id,
            name=name,
            dimension=AlertDimension.QUALITY,
            rule_type=AlertRuleType.THRESHOLD,
            level=level,
            priority=AlertPriority.HIGH,
            conditions={
                "metric_name": "quality_score",
                "operator": "lt",  # less than
                "value": quality_threshold
            },
            threshold_config={
                "threshold": quality_threshold,
                "comparison": "below",
                "duration_minutes": 5
            },
            trend_config={
                "window_size": trend_window,
                "decline_threshold": 0.1,
                "check_interval_minutes": 1
            },
            escalation_config={
                "escalate_after_minutes": 15,
                "max_escalation_level": 3
            }
        )
        
        self.rules[rule_id] = rule
        logger.info(f"Created quality alert rule: {rule_id}")
        return rule
    
    def create_efficiency_alert_rule(
        self,
        name: str,
        efficiency_threshold: float = 0.7,
        workload_threshold: int = 100,
        level: AlertLevel = AlertLevel.WARNING
    ) -> AlertRule:
        """创建效率告警规则"""
        rule_id = f"efficiency_{uuid4().hex[:8]}"
        
        rule = AlertRule(
            id=rule_id,
            name=name,
            dimension=AlertDimension.EFFICIENCY,
            rule_type=AlertRuleType.COMPOSITE,
            level=level,
            priority=AlertPriority.MEDIUM,
            composite_config={
                "conditions": [
                    {
                        "metric_name": "task_completion_rate",
                        "operator": "lt",
                        "value": efficiency_threshold
                    },
                    {
                        "metric_name": "current_workload",
                        "operator": "gt",
                        "value": workload_threshold
                    }
                ],
                "logic": "AND"  # 所有条件都满足才告警
            },
            escalation_config={
                "escalate_after_minutes": 30,
                "max_escalation_level": 2
            }
        )
        
        self.rules[rule_id] = rule
        logger.info(f"Created efficiency alert rule: {rule_id}")
        return rule
    
    def create_cost_alert_rule(
        self,
        name: str,
        cost_threshold: float = 1000.0,
        budget_percentage: float = 0.8,
        level: AlertLevel = AlertLevel.HIGH
    ) -> AlertRule:
        """创建成本告警规则"""
        rule_id = f"cost_{uuid4().hex[:8]}"
        
        rule = AlertRule(
            id=rule_id,
            name=name,
            dimension=AlertDimension.COST,
            rule_type=AlertRuleType.THRESHOLD,
            level=level,
            priority=AlertPriority.HIGH,
            conditions={
                "metric_name": "daily_cost",
                "operator": "gt",
                "value": cost_threshold
            },
            threshold_config={
                "threshold": cost_threshold,
                "comparison": "above",
                "duration_minutes": 10
            },
            composite_config={
                "conditions": [
                    {
                        "metric_name": "budget_usage_percentage",
                        "operator": "gt",
                        "value": budget_percentage
                    }
                ]
            },
            escalation_config={
                "escalate_after_minutes": 10,
                "max_escalation_level": 3
            }
        )
        
        self.rules[rule_id] = rule
        logger.info(f"Created cost alert rule: {rule_id}")
        return rule
    
    def create_anomaly_detection_rule(
        self,
        name: str,
        metric_name: str,
        dimension: AlertDimension,
        sensitivity: float = 2.0,
        level: AlertLevel = AlertLevel.WARNING
    ) -> AlertRule:
        """创建异常检测规则"""
        rule_id = f"anomaly_{uuid4().hex[:8]}"
        
        rule = AlertRule(
            id=rule_id,
            name=name,
            dimension=dimension,
            rule_type=AlertRuleType.ANOMALY,
            level=level,
            priority=AlertPriority.MEDIUM,
            conditions={
                "metric_name": metric_name
            },
            anomaly_config={
                "algorithm": "statistical",
                "sensitivity": sensitivity,
                "window_size": 50,
                "min_samples": 10,
                "z_score_threshold": sensitivity
            },
            escalation_config={
                "escalate_after_minutes": 20,
                "max_escalation_level": 2
            }
        )
        
        self.rules[rule_id] = rule
        logger.info(f"Created anomaly detection rule: {rule_id}")
        return rule
    
    def evaluate_rules(self, metrics: Dict[str, Any]) -> List[Alert]:
        """评估告警规则"""
        alerts = []
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
                
            try:
                alert = self._evaluate_single_rule(rule, metrics)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {e}")
        
        return alerts
    
    def _evaluate_single_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """评估单个规则"""
        if rule.rule_type == AlertRuleType.THRESHOLD:
            return self._evaluate_threshold_rule(rule, metrics)
        elif rule.rule_type == AlertRuleType.TREND:
            return self._evaluate_trend_rule(rule, metrics)
        elif rule.rule_type == AlertRuleType.ANOMALY:
            return self._evaluate_anomaly_rule(rule, metrics)
        elif rule.rule_type == AlertRuleType.COMPOSITE:
            return self._evaluate_composite_rule(rule, metrics)
        
        return None
    
    def _evaluate_threshold_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """评估阈值规则"""
        metric_name = rule.conditions.get("metric_name")
        operator = rule.conditions.get("operator")
        threshold = rule.conditions.get("value")
        
        if not all([metric_name, operator, threshold is not None]):
            return None
        
        metric_value = metrics.get(metric_name)
        if metric_value is None:
            return None
        
        # 记录指标历史
        self.metric_history[metric_name].append({
            "value": metric_value,
            "timestamp": datetime.now()
        })
        
        # 检查阈值条件
        triggered = False
        if operator == "gt" and metric_value > threshold:
            triggered = True
        elif operator == "lt" and metric_value < threshold:
            triggered = True
        elif operator == "eq" and metric_value == threshold:
            triggered = True
        elif operator == "gte" and metric_value >= threshold:
            triggered = True
        elif operator == "lte" and metric_value <= threshold:
            triggered = True
        
        if triggered:
            return Alert(
                id=uuid4(),
                rule_id=rule.id,
                dimension=rule.dimension,
                level=rule.level,
                priority=rule.priority,
                title=f"{rule.name} - 阈值告警",
                message=f"指标 {metric_name} 当前值 {metric_value} {operator} 阈值 {threshold}",
                source="threshold_monitor",
                metric_name=metric_name,
                metric_value=metric_value,
                threshold_value=threshold,
                context={"rule_type": "threshold", "operator": operator},
                tags={"dimension": rule.dimension.value, "rule_id": rule.id}
            )
        
        return None
    
    def _evaluate_trend_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """评估趋势规则"""
        metric_name = rule.conditions.get("metric_name")
        if not metric_name:
            return None
        
        metric_value = metrics.get(metric_name)
        if metric_value is None:
            return None
        
        # 记录指标历史
        self.metric_history[metric_name].append({
            "value": metric_value,
            "timestamp": datetime.now()
        })
        
        trend_config = rule.trend_config or {}
        window_size = trend_config.get("window_size", 10)
        decline_threshold = trend_config.get("decline_threshold", 0.1)
        
        history = list(self.metric_history[metric_name])
        if len(history) < window_size:
            return None
        
        # 计算趋势
        recent_values = [h["value"] for h in history[-window_size:]]
        if len(recent_values) < 2:
            return None
        
        # 简单线性趋势计算
        x = list(range(len(recent_values)))
        y = recent_values
        
        # 计算斜率
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # 检查下降趋势
        if slope < -decline_threshold:
            return Alert(
                id=uuid4(),
                rule_id=rule.id,
                dimension=rule.dimension,
                level=rule.level,
                priority=rule.priority,
                title=f"{rule.name} - 趋势告警",
                message=f"指标 {metric_name} 呈下降趋势，斜率: {slope:.4f}",
                source="trend_monitor",
                metric_name=metric_name,
                metric_value=metric_value,
                context={
                    "rule_type": "trend",
                    "slope": slope,
                    "window_size": window_size,
                    "recent_values": recent_values
                },
                tags={"dimension": rule.dimension.value, "rule_id": rule.id}
            )
        
        return None
    
    def _evaluate_anomaly_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """评估异常检测规则"""
        metric_name = rule.conditions.get("metric_name")
        if not metric_name:
            return None
        
        metric_value = metrics.get(metric_name)
        if metric_value is None:
            return None
        
        # 记录指标历史
        self.metric_history[metric_name].append({
            "value": metric_value,
            "timestamp": datetime.now()
        })
        
        anomaly_config = rule.anomaly_config or {}
        window_size = anomaly_config.get("window_size", 50)
        min_samples = anomaly_config.get("min_samples", 10)
        z_threshold = anomaly_config.get("z_score_threshold", 2.0)
        
        history = list(self.metric_history[metric_name])
        if len(history) < min_samples:
            return None
        
        # 获取历史值
        historical_values = [h["value"] for h in history[:-1]]  # 排除当前值
        if len(historical_values) < min_samples:
            return None
        
        # 计算统计指标
        mean_val = statistics.mean(historical_values)
        std_val = statistics.stdev(historical_values) if len(historical_values) > 1 else 0
        
        if std_val == 0:
            return None
        
        # 计算 Z-score
        z_score = abs(metric_value - mean_val) / std_val
        
        if z_score > z_threshold:
            return Alert(
                id=uuid4(),
                rule_id=rule.id,
                dimension=rule.dimension,
                level=rule.level,
                priority=rule.priority,
                title=f"{rule.name} - 异常检测告警",
                message=f"指标 {metric_name} 检测到异常值，Z-score: {z_score:.2f}",
                source="anomaly_detector",
                metric_name=metric_name,
                metric_value=metric_value,
                context={
                    "rule_type": "anomaly",
                    "z_score": z_score,
                    "mean": mean_val,
                    "std": std_val,
                    "threshold": z_threshold
                },
                tags={"dimension": rule.dimension.value, "rule_id": rule.id}
            )
        
        return None
    
    def _evaluate_composite_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """评估复合规则"""
        composite_config = rule.composite_config
        if not composite_config:
            return None
        
        conditions = composite_config.get("conditions", [])
        logic = composite_config.get("logic", "AND")
        
        results = []
        for condition in conditions:
            metric_name = condition.get("metric_name")
            operator = condition.get("operator")
            threshold = condition.get("value")
            
            if not all([metric_name, operator, threshold is not None]):
                continue
            
            metric_value = metrics.get(metric_name)
            if metric_value is None:
                results.append(False)
                continue
            
            # 评估条件
            if operator == "gt":
                results.append(metric_value > threshold)
            elif operator == "lt":
                results.append(metric_value < threshold)
            elif operator == "eq":
                results.append(metric_value == threshold)
            elif operator == "gte":
                results.append(metric_value >= threshold)
            elif operator == "lte":
                results.append(metric_value <= threshold)
            else:
                results.append(False)
        
        # 应用逻辑
        if logic == "AND":
            triggered = all(results)
        elif logic == "OR":
            triggered = any(results)
        else:
            triggered = False
        
        if triggered:
            return Alert(
                id=uuid4(),
                rule_id=rule.id,
                dimension=rule.dimension,
                level=rule.level,
                priority=rule.priority,
                title=f"{rule.name} - 复合告警",
                message=f"复合条件触发告警，逻辑: {logic}",
                source="composite_monitor",
                context={
                    "rule_type": "composite",
                    "conditions": conditions,
                    "logic": logic,
                    "results": results
                },
                tags={"dimension": rule.dimension.value, "rule_id": rule.id}
            )
        
        return None
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """获取规则"""
        return self.rules.get(rule_id)
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """更新规则"""
        rule = self.rules.get(rule_id)
        if not rule:
            return False
        
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.updated_at = datetime.now()
        logger.info(f"Updated alert rule: {rule_id}")
        return True
    
    def delete_rule(self, rule_id: str) -> bool:
        """删除规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Deleted alert rule: {rule_id}")
            return True
        return False
    
    def list_rules(
        self,
        dimension: Optional[AlertDimension] = None,
        enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """列出规则"""
        rules = list(self.rules.values())
        
        if dimension:
            rules = [r for r in rules if r.dimension == dimension]
        
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        return [rule.to_dict() for rule in rules]


class AlertAggregator:
    """告警聚合器"""
    
    def __init__(self):
        self.aggregation_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_groups: Dict[str, List[Alert]] = defaultdict(list)
        
    def add_aggregation_rule(
        self,
        rule_id: str,
        group_by: List[str],
        time_window_minutes: int = 5,
        max_alerts: int = 10,
        merge_strategy: str = "count"
    ):
        """添加聚合规则"""
        self.aggregation_rules[rule_id] = {
            "group_by": group_by,
            "time_window_minutes": time_window_minutes,
            "max_alerts": max_alerts,
            "merge_strategy": merge_strategy
        }
        logger.info(f"Added aggregation rule: {rule_id}")
    
    def aggregate_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """聚合告警"""
        if not alerts:
            return []
        
        aggregated_alerts = []
        processed_alert_ids = set()
        
        for rule_id, rule_config in self.aggregation_rules.items():
            group_by = rule_config["group_by"]
            time_window = timedelta(minutes=rule_config["time_window_minutes"])
            max_alerts = rule_config["max_alerts"]
            merge_strategy = rule_config["merge_strategy"]
            
            # 按分组键聚合
            groups = defaultdict(list)
            for alert in alerts:
                if alert.id in processed_alert_ids:
                    continue
                
                # 生成分组键
                group_key = self._generate_group_key(alert, group_by)
                groups[group_key].append(alert)
            
            # 处理每个分组
            for group_key, group_alerts in groups.items():
                if len(group_alerts) <= 1:
                    continue
                
                # 按时间窗口过滤
                now = datetime.now()
                windowed_alerts = [
                    a for a in group_alerts
                    if now - a.created_at <= time_window
                ]
                
                if len(windowed_alerts) >= 2:
                    # 创建聚合告警
                    aggregated_alert = self._create_aggregated_alert(
                        windowed_alerts, merge_strategy, max_alerts
                    )
                    aggregated_alerts.append(aggregated_alert)
                    
                    # 标记已处理
                    for alert in windowed_alerts:
                        processed_alert_ids.add(alert.id)
        
        # 添加未聚合的告警
        for alert in alerts:
            if alert.id not in processed_alert_ids:
                aggregated_alerts.append(alert)
        
        return aggregated_alerts
    
    def _generate_group_key(self, alert: Alert, group_by: List[str]) -> str:
        """生成分组键"""
        key_parts = []
        for field in group_by:
            if field == "dimension":
                key_parts.append(alert.dimension.value)
            elif field == "level":
                key_parts.append(alert.level.value)
            elif field == "source":
                key_parts.append(alert.source)
            elif field == "tenant_id":
                key_parts.append(alert.tenant_id or "")
            elif field == "project_id":
                key_parts.append(alert.project_id or "")
            elif field == "rule_id":
                key_parts.append(alert.rule_id)
            elif field in alert.tags:
                key_parts.append(alert.tags[field])
        
        return "|".join(key_parts)
    
    def _create_aggregated_alert(
        self,
        alerts: List[Alert],
        merge_strategy: str,
        max_alerts: int
    ) -> Alert:
        """创建聚合告警"""
        if not alerts:
            raise ValueError("Cannot create aggregated alert from empty list")
        
        # 选择主告警（优先级最高的）
        primary_alert = max(alerts, key=lambda a: a.priority.value)
        
        # 计算聚合信息
        alert_count = len(alerts)
        dimensions = set(a.dimension for a in alerts)
        levels = set(a.level for a in alerts)
        sources = set(a.source for a in alerts)
        
        # 创建聚合告警
        aggregated_alert = Alert(
            id=uuid4(),
            rule_id=primary_alert.rule_id,
            dimension=primary_alert.dimension,
            level=max(alerts, key=lambda a: list(AlertLevel).index(a.level)).level,
            priority=max(alerts, key=lambda a: a.priority.value).priority,
            title=f"聚合告警 - {alert_count} 个相关告警",
            message=self._generate_aggregated_message(alerts, merge_strategy),
            source="alert_aggregator",
            tenant_id=primary_alert.tenant_id,
            user_id=primary_alert.user_id,
            project_id=primary_alert.project_id,
            context={
                "aggregated": True,
                "alert_count": alert_count,
                "dimensions": [d.value for d in dimensions],
                "levels": [l.value for l in levels],
                "sources": list(sources),
                "original_alerts": [str(a.id) for a in alerts[:max_alerts]],
                "merge_strategy": merge_strategy
            },
            tags={
                "aggregated": "true",
                "alert_count": str(alert_count)
            }
        )
        
        return aggregated_alert
    
    def _generate_aggregated_message(self, alerts: List[Alert], merge_strategy: str) -> str:
        """生成聚合消息"""
        if merge_strategy == "count":
            return f"检测到 {len(alerts)} 个相关告警"
        elif merge_strategy == "summary":
            dimensions = set(a.dimension.value for a in alerts)
            levels = set(a.level.value for a in alerts)
            return f"聚合告警: {len(alerts)} 个告警，涉及维度 {', '.join(dimensions)}，级别 {', '.join(levels)}"
        elif merge_strategy == "detail":
            messages = [a.message for a in alerts[:5]]  # 最多显示5个
            if len(alerts) > 5:
                messages.append(f"... 还有 {len(alerts) - 5} 个告警")
            return "; ".join(messages)
        else:
            return f"聚合了 {len(alerts)} 个告警"


class AlertDeduplicator:
    """告警去重器"""
    
    def __init__(self):
        self.dedup_window_minutes = 10
        self.recent_alerts: Dict[str, Alert] = {}
        
    def deduplicate_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """去重告警"""
        deduplicated = []
        now = datetime.now()
        
        # 清理过期的告警
        self._cleanup_expired_alerts(now)
        
        for alert in alerts:
            dedup_key = self._generate_dedup_key(alert)
            
            # 检查是否重复
            existing_alert = self.recent_alerts.get(dedup_key)
            if existing_alert:
                # 更新现有告警的计数
                existing_alert.context["duplicate_count"] = existing_alert.context.get("duplicate_count", 1) + 1
                existing_alert.context["last_seen"] = now.isoformat()
                logger.debug(f"Deduplicated alert: {dedup_key}")
                continue
            
            # 添加新告警
            alert.context["duplicate_count"] = 1
            alert.context["first_seen"] = now.isoformat()
            self.recent_alerts[dedup_key] = alert
            deduplicated.append(alert)
        
        return deduplicated
    
    def _generate_dedup_key(self, alert: Alert) -> str:
        """生成去重键"""
        key_parts = [
            alert.rule_id,
            alert.dimension.value,
            alert.level.value,
            alert.source,
            alert.tenant_id or "",
            alert.project_id or "",
            alert.metric_name or ""
        ]
        return "|".join(key_parts)
    
    def _cleanup_expired_alerts(self, now: datetime):
        """清理过期告警"""
        cutoff = now - timedelta(minutes=self.dedup_window_minutes)
        expired_keys = [
            key for key, alert in self.recent_alerts.items()
            if alert.created_at < cutoff
        ]
        
        for key in expired_keys:
            del self.recent_alerts[key]


class AlertEscalationManager:
    """告警升级管理器"""
    
    def __init__(self):
        self.escalation_rules: Dict[str, Dict[str, Any]] = {}
        self.escalated_alerts: Dict[UUID, Dict[str, Any]] = {}
        
    def add_escalation_rule(
        self,
        rule_id: str,
        trigger_conditions: Dict[str, Any],
        escalation_steps: List[Dict[str, Any]]
    ):
        """添加升级规则"""
        self.escalation_rules[rule_id] = {
            "trigger_conditions": trigger_conditions,
            "escalation_steps": escalation_steps
        }
        logger.info(f"Added escalation rule: {rule_id}")
    
    async def check_escalations(self, alerts: List[Alert]) -> List[Dict[str, Any]]:
        """检查告警升级"""
        escalations = []
        
        for alert in alerts:
            if alert.status != AlertStatus.ACTIVE:
                continue
            
            escalation = await self._check_alert_escalation(alert)
            if escalation:
                escalations.append(escalation)
        
        return escalations
    
    async def _check_alert_escalation(self, alert: Alert) -> Optional[Dict[str, Any]]:
        """检查单个告警的升级"""
        now = datetime.now()
        
        # 检查是否已经升级过
        if alert.id in self.escalated_alerts:
            escalation_info = self.escalated_alerts[alert.id]
            last_escalation = escalation_info.get("last_escalation")
            if last_escalation:
                time_since_escalation = now - datetime.fromisoformat(last_escalation)
                if time_since_escalation.total_seconds() < 300:  # 5分钟内不重复升级
                    return None
        
        # 检查升级条件
        time_since_creation = now - alert.created_at
        
        # 基于告警级别的默认升级时间
        escalation_thresholds = {
            AlertLevel.CRITICAL: 5,    # 5分钟
            AlertLevel.HIGH: 15,       # 15分钟
            AlertLevel.WARNING: 60,    # 60分钟
            AlertLevel.INFO: 0         # 不升级
        }
        
        threshold_minutes = escalation_thresholds.get(alert.level, 0)
        if threshold_minutes == 0:
            return None
        
        if time_since_creation.total_seconds() >= threshold_minutes * 60:
            # 执行升级
            escalation = {
                "alert_id": alert.id,
                "alert_title": alert.title,
                "escalation_level": alert.escalation_level + 1,
                "escalation_reason": f"告警未在 {threshold_minutes} 分钟内处理",
                "escalated_at": now.isoformat(),
                "escalation_actions": []
            }
            
            # 更新告警状态
            alert.escalation_level += 1
            alert.escalated_at = now
            alert.status = AlertStatus.ESCALATED
            
            # 记录升级信息
            self.escalated_alerts[alert.id] = {
                "escalation_count": alert.escalation_level,
                "last_escalation": now.isoformat(),
                "escalation_history": self.escalated_alerts.get(alert.id, {}).get("escalation_history", []) + [now.isoformat()]
            }
            
            # 确定升级动作
            if alert.escalation_level == 1:
                escalation["escalation_actions"] = ["notify_supervisor", "increase_priority"]
            elif alert.escalation_level == 2:
                escalation["escalation_actions"] = ["notify_manager", "create_incident"]
            elif alert.escalation_level >= 3:
                escalation["escalation_actions"] = ["notify_executive", "emergency_response"]
            
            logger.warning(f"Alert escalated: {alert.id} to level {alert.escalation_level}")
            return escalation
        
        return None


class IntelligentAlertSystem:
    """智能告警系统主类"""
    
    def __init__(self):
        self.rule_engine = MultiDimensionalAlertRuleEngine()
        self.aggregator = AlertAggregator()
        self.deduplicator = AlertDeduplicator()
        self.escalation_manager = AlertEscalationManager()
        
        self.active_alerts: Dict[UUID, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # 初始化默认规则
        self._initialize_default_rules()
        self._initialize_default_aggregation_rules()
    
    def _initialize_default_rules(self):
        """初始化默认告警规则"""
        # 质量告警规则
        self.rule_engine.create_quality_alert_rule(
            name="质量分数低于阈值",
            quality_threshold=0.8,
            level=AlertLevel.WARNING
        )
        
        self.rule_engine.create_quality_alert_rule(
            name="质量分数严重下降",
            quality_threshold=0.6,
            level=AlertLevel.CRITICAL
        )
        
        # 效率告警规则
        self.rule_engine.create_efficiency_alert_rule(
            name="任务完成率低",
            efficiency_threshold=0.7,
            workload_threshold=100,
            level=AlertLevel.WARNING
        )
        
        # 成本告警规则
        self.rule_engine.create_cost_alert_rule(
            name="日成本超标",
            cost_threshold=1000.0,
            budget_percentage=0.8,
            level=AlertLevel.HIGH
        )
        
        # 异常检测规则
        self.rule_engine.create_anomaly_detection_rule(
            name="质量分数异常",
            metric_name="quality_score",
            dimension=AlertDimension.QUALITY,
            sensitivity=2.0,
            level=AlertLevel.WARNING
        )
        
        logger.info("Initialized default alert rules")
    
    def _initialize_default_aggregation_rules(self):
        """初始化默认聚合规则"""
        # 按维度和级别聚合
        self.aggregator.add_aggregation_rule(
            rule_id="dimension_level_aggregation",
            group_by=["dimension", "level"],
            time_window_minutes=5,
            max_alerts=10,
            merge_strategy="summary"
        )
        
        # 按项目聚合
        self.aggregator.add_aggregation_rule(
            rule_id="project_aggregation",
            group_by=["project_id", "dimension"],
            time_window_minutes=10,
            max_alerts=15,
            merge_strategy="count"
        )
        
        logger.info("Initialized default aggregation rules")
    
    async def process_metrics(self, metrics: Dict[str, Any]) -> List[Alert]:
        """处理指标并生成告警"""
        # 1. 评估告警规则
        raw_alerts = self.rule_engine.evaluate_rules(metrics)
        
        if not raw_alerts:
            return []
        
        # 2. 去重
        deduplicated_alerts = self.deduplicator.deduplicate_alerts(raw_alerts)
        
        # 3. 聚合
        aggregated_alerts = self.aggregator.aggregate_alerts(deduplicated_alerts)
        
        # 4. 存储活跃告警
        for alert in aggregated_alerts:
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)
        
        # 5. 检查升级
        escalations = await self.escalation_manager.check_escalations(list(self.active_alerts.values()))
        
        logger.info(f"Processed metrics: {len(raw_alerts)} raw alerts, {len(aggregated_alerts)} final alerts, {len(escalations)} escalations")
        
        return aggregated_alerts
    
    async def acknowledge_alert(self, alert_id: UUID, acknowledged_by: str) -> bool:
        """确认告警"""
        alert = self.active_alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now()
        alert.acknowledged_by = acknowledged_by
        
        logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
        return True
    
    async def resolve_alert(self, alert_id: UUID, resolved_by: str, resolution_notes: Optional[str] = None) -> bool:
        """解决告警"""
        alert = self.active_alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        alert.resolved_by = resolved_by
        
        if resolution_notes:
            alert.context["resolution_notes"] = resolution_notes
        
        # 从活跃告警中移除
        del self.active_alerts[alert_id]
        
        logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
        return True
    
    def get_active_alerts(
        self,
        dimension: Optional[AlertDimension] = None,
        level: Optional[AlertLevel] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        alerts = list(self.active_alerts.values())
        
        if dimension:
            alerts = [a for a in alerts if a.dimension == dimension]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        # 按优先级和创建时间排序
        alerts.sort(key=lambda x: (-x.priority.value, -x.created_at.timestamp()))
        
        return [alert.to_dict() for alert in alerts[:limit]]
    
    def get_alert_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取告警统计"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_alerts = [a for a in self.alert_history if a.created_at >= cutoff]
        
        # 按维度统计
        by_dimension = defaultdict(int)
        for alert in recent_alerts:
            by_dimension[alert.dimension.value] += 1
        
        # 按级别统计
        by_level = defaultdict(int)
        for alert in recent_alerts:
            by_level[alert.level.value] += 1
        
        # 按状态统计
        by_status = defaultdict(int)
        for alert in recent_alerts:
            by_status[alert.status.value] += 1
        
        return {
            "period_days": days,
            "total_alerts": len(recent_alerts),
            "active_alerts": len(self.active_alerts),
            "by_dimension": dict(by_dimension),
            "by_level": dict(by_level),
            "by_status": dict(by_status),
            "generated_at": datetime.now().isoformat()
        }