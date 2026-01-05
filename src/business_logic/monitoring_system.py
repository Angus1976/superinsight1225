#!/usr/bin/env python3
"""
业务逻辑监控和报告系统
实现实时监控、性能跟踪、自动报告生成

实现需求 13: 客户业务逻辑提炼与智能化 - 任务 48.3
"""

import logging
import time
import uuid
import threading
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import psutil
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Alert:
    """告警"""
    alert_id: str
    alert_name: str
    severity: str  # low, medium, high, critical
    message: str
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold_value: float
    status: str = "active"  # active, resolved, suppressed
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class PerformanceReport:
    """性能报告"""
    report_id: str
    report_name: str
    time_range: Dict[str, datetime]
    metrics_summary: Dict[str, Dict[str, float]]
    alerts_summary: Dict[str, int]
    recommendations: List[str]
    generated_at: datetime

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_points: int = 10000):
        self.metrics_buffer = defaultdict(lambda: deque(maxlen=max_points))
        self.collection_interval = 30  # 秒
        self.is_collecting = False
        self.collection_thread = None
        
    def start_collection(self):
        """开始指标收集"""
        if self.is_collecting:
            logger.warning("指标收集已在运行")
            return
        
        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        logger.info("指标收集已启动")
    
    def stop_collection(self):
        """停止指标收集"""
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        logger.info("指标收集已停止")
    
    def _collection_loop(self):
        """指标收集循环"""
        while self.is_collecting:
            try:
                self._collect_system_metrics()
                self._collect_business_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"指标收集出错: {e}")
                time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            now = datetime.now()
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.add_metric("system.cpu.usage", cpu_percent, now, {"type": "system"})
            
            # 内存使用率
            memory = psutil.virtual_memory()
            self.add_metric("system.memory.usage", memory.percent, now, {"type": "system"})
            self.add_metric("system.memory.available", memory.available / 1024 / 1024, now, {"type": "system", "unit": "MB"})
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.add_metric("system.disk.usage", disk_percent, now, {"type": "system"})
            
            # 网络IO
            net_io = psutil.net_io_counters()
            self.add_metric("system.network.bytes_sent", net_io.bytes_sent, now, {"type": "system", "direction": "sent"})
            self.add_metric("system.network.bytes_recv", net_io.bytes_recv, now, {"type": "system", "direction": "received"})
            
        except Exception as e:
            logger.error(f"系统指标收集失败: {e}")
    
    def _collect_business_metrics(self):
        """收集业务指标"""
        try:
            now = datetime.now()
            
            # 这里可以添加具体的业务指标收集逻辑
            # 例如：API调用次数、处理时间、错误率等
            
            # 模拟业务指标
            import random
            self.add_metric("business.api.requests", random.randint(10, 100), now, {"type": "business", "endpoint": "all"})
            self.add_metric("business.api.response_time", random.uniform(0.1, 2.0), now, {"type": "business", "unit": "seconds"})
            self.add_metric("business.api.error_rate", random.uniform(0, 0.05), now, {"type": "business", "unit": "percentage"})
            
        except Exception as e:
            logger.error(f"业务指标收集失败: {e}")
    
    def add_metric(self, metric_name: str, value: float, timestamp: datetime = None, tags: Dict[str, str] = None):
        """添加指标"""
        if timestamp is None:
            timestamp = datetime.now()
        
        if tags is None:
            tags = {}
        
        metric_point = MetricPoint(
            timestamp=timestamp,
            metric_name=metric_name,
            value=value,
            tags=tags
        )
        
        self.metrics_buffer[metric_name].append(metric_point)
    
    def get_metrics(self, metric_name: str, time_range: Optional[Dict[str, datetime]] = None) -> List[MetricPoint]:
        """获取指标数据"""
        if metric_name not in self.metrics_buffer:
            return []
        
        metrics = list(self.metrics_buffer[metric_name])
        
        if time_range:
            start_time = time_range.get("start")
            end_time = time_range.get("end")
            
            if start_time or end_time:
                filtered_metrics = []
                for metric in metrics:
                    if start_time and metric.timestamp < start_time:
                        continue
                    if end_time and metric.timestamp > end_time:
                        continue
                    filtered_metrics.append(metric)
                metrics = filtered_metrics
        
        return metrics
    
    def get_metric_summary(self, metric_name: str, time_range: Optional[Dict[str, datetime]] = None) -> Dict[str, float]:
        """获取指标摘要统计"""
        metrics = self.get_metrics(metric_name, time_range)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0,
            "latest": values[-1] if values else 0
        }
    
    def list_metrics(self) -> List[str]:
        """列出所有指标名称"""
        return list(self.metrics_buffer.keys())

class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alert_rules = []
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.notification_handlers = []
        
    def add_alert_rule(self, metric_name: str, threshold: float, 
                      comparison: str = "greater", severity: str = "medium",
                      alert_name: str = None):
        """
        添加告警规则
        
        Args:
            metric_name: 指标名称
            threshold: 阈值
            comparison: 比较方式 (greater, less, equal)
            severity: 严重程度
            alert_name: 告警名称
        """
        rule = {
            "rule_id": f"rule_{uuid.uuid4().hex[:8]}",
            "metric_name": metric_name,
            "threshold": threshold,
            "comparison": comparison,
            "severity": severity,
            "alert_name": alert_name or f"{metric_name} 告警",
            "enabled": True
        }
        
        self.alert_rules.append(rule)
        logger.info(f"添加告警规则: {rule['alert_name']}")
        
        return rule["rule_id"]
    
    def check_alerts(self, metrics_collector: MetricsCollector):
        """检查告警"""
        for rule in self.alert_rules:
            if not rule["enabled"]:
                continue
                
            try:
                self._check_single_rule(rule, metrics_collector)
            except Exception as e:
                logger.error(f"告警检查失败 ({rule['alert_name']}): {e}")
    
    def _check_single_rule(self, rule: Dict[str, Any], metrics_collector: MetricsCollector):
        """检查单个告警规则"""
        metric_name = rule["metric_name"]
        
        # 获取最近的指标值
        recent_metrics = metrics_collector.get_metrics(
            metric_name, 
            {"start": datetime.now() - timedelta(minutes=5)}
        )
        
        if not recent_metrics:
            return
        
        current_value = recent_metrics[-1].value
        threshold = rule["threshold"]
        comparison = rule["comparison"]
        
        # 检查是否触发告警
        triggered = False
        if comparison == "greater" and current_value > threshold:
            triggered = True
        elif comparison == "less" and current_value < threshold:
            triggered = True
        elif comparison == "equal" and abs(current_value - threshold) < 0.001:
            triggered = True
        
        alert_key = f"{rule['rule_id']}_{metric_name}"
        
        if triggered:
            # 触发告警
            if alert_key not in self.active_alerts:
                alert = Alert(
                    alert_id=f"alert_{uuid.uuid4().hex[:8]}",
                    alert_name=rule["alert_name"],
                    severity=rule["severity"],
                    message=f"{metric_name} 当前值 {current_value} {comparison} 阈值 {threshold}",
                    timestamp=datetime.now(),
                    metric_name=metric_name,
                    current_value=current_value,
                    threshold_value=threshold,
                    status="active"
                )
                
                self.active_alerts[alert_key] = alert
                self.alert_history.append(alert)
                
                # 发送通知
                self._send_alert_notification(alert)
                
                logger.warning(f"触发告警: {alert.alert_name}")
        else:
            # 解除告警
            if alert_key in self.active_alerts:
                alert = self.active_alerts[alert_key]
                alert.status = "resolved"
                del self.active_alerts[alert_key]
                
                logger.info(f"解除告警: {alert.alert_name}")
    
    def _send_alert_notification(self, alert: Alert):
        """发送告警通知"""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"告警通知发送失败: {e}")
    
    def add_notification_handler(self, handler: Callable[[Alert], None]):
        """添加通知处理器"""
        self.notification_handlers.append(handler)
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return list(self.alert_history)[-limit:]
    
    def suppress_alert(self, alert_id: str):
        """抑制告警"""
        for alert_key, alert in self.active_alerts.items():
            if alert.alert_id == alert_id:
                alert.status = "suppressed"
                logger.info(f"抑制告警: {alert.alert_name}")
                break

class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self.report_templates = {}
        self.generated_reports = deque(maxlen=100)
        
    def generate_performance_report(self, metrics_collector: MetricsCollector,
                                  alert_manager: AlertManager,
                                  time_range: Dict[str, datetime],
                                  report_name: str = "性能报告") -> PerformanceReport:
        """
        生成性能报告
        
        Args:
            metrics_collector: 指标收集器
            alert_manager: 告警管理器
            time_range: 时间范围
            report_name: 报告名称
            
        Returns:
            PerformanceReport: 性能报告
        """
        logger.info(f"生成性能报告: {report_name}")
        
        try:
            report_id = f"report_{uuid.uuid4().hex[:8]}"
            
            # 收集指标摘要
            metrics_summary = {}
            for metric_name in metrics_collector.list_metrics():
                summary = metrics_collector.get_metric_summary(metric_name, time_range)
                if summary:
                    metrics_summary[metric_name] = summary
            
            # 收集告警摘要
            alert_history = alert_manager.get_alert_history()
            alerts_in_range = [
                alert for alert in alert_history
                if time_range["start"] <= alert.timestamp <= time_range["end"]
            ]
            
            alerts_summary = {
                "total": len(alerts_in_range),
                "critical": len([a for a in alerts_in_range if a.severity == "critical"]),
                "high": len([a for a in alerts_in_range if a.severity == "high"]),
                "medium": len([a for a in alerts_in_range if a.severity == "medium"]),
                "low": len([a for a in alerts_in_range if a.severity == "low"])
            }
            
            # 生成建议
            recommendations = self._generate_recommendations(metrics_summary, alerts_summary)
            
            # 创建报告
            report = PerformanceReport(
                report_id=report_id,
                report_name=report_name,
                time_range=time_range,
                metrics_summary=metrics_summary,
                alerts_summary=alerts_summary,
                recommendations=recommendations,
                generated_at=datetime.now()
            )
            
            self.generated_reports.append(report)
            
            logger.info(f"性能报告生成完成: {report_id}")
            return report
            
        except Exception as e:
            logger.error(f"性能报告生成失败: {e}")
            raise
    
    def _generate_recommendations(self, metrics_summary: Dict[str, Dict[str, float]],
                                alerts_summary: Dict[str, int]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 基于告警的建议
        if alerts_summary.get("critical", 0) > 0:
            recommendations.append("发现关键告警，需要立即处理")
        
        if alerts_summary.get("high", 0) > 5:
            recommendations.append("高优先级告警较多，建议检查系统负载")
        
        # 基于指标的建议
        for metric_name, summary in metrics_summary.items():
            if "cpu" in metric_name.lower() and summary.get("mean", 0) > 80:
                recommendations.append("CPU使用率较高，建议优化或扩容")
            
            if "memory" in metric_name.lower() and summary.get("mean", 0) > 85:
                recommendations.append("内存使用率较高，建议检查内存泄漏")
            
            if "response_time" in metric_name.lower() and summary.get("mean", 0) > 2.0:
                recommendations.append("响应时间较长，建议优化性能")
            
            if "error_rate" in metric_name.lower() and summary.get("mean", 0) > 0.05:
                recommendations.append("错误率较高，建议检查系统稳定性")
        
        if not recommendations:
            recommendations.append("系统运行正常，继续监控")
        
        return recommendations
    
    def export_report(self, report: PerformanceReport, format: str = "dict") -> Dict[str, Any]:
        """导出报告"""
        if format == "dict":
            return {
                "report_id": report.report_id,
                "report_name": report.report_name,
                "generated_at": report.generated_at.isoformat(),
                "time_range": {
                    "start": report.time_range["start"].isoformat(),
                    "end": report.time_range["end"].isoformat()
                },
                "metrics_summary": report.metrics_summary,
                "alerts_summary": report.alerts_summary,
                "recommendations": report.recommendations
            }
        else:
            return {"error": f"不支持的导出格式: {format}"}
    
    def get_report_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取报告历史"""
        recent_reports = list(self.generated_reports)[-limit:]
        
        return [
            {
                "report_id": report.report_id,
                "report_name": report.report_name,
                "generated_at": report.generated_at.isoformat(),
                "metrics_count": len(report.metrics_summary),
                "total_alerts": report.alerts_summary.get("total", 0)
            }
            for report in recent_reports
        ]

class MonitoringSystem:
    """监控系统主类"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.report_generator = ReportGenerator()
        self.is_running = False
        self.monitoring_thread = None
        
        # 设置默认告警规则
        self._setup_default_alerts()
        
        # 设置默认通知处理器
        self._setup_default_notifications()
    
    def start_monitoring(self):
        """启动监控系统"""
        if self.is_running:
            logger.warning("监控系统已在运行")
            return
        
        logger.info("启动监控系统")
        
        # 启动指标收集
        self.metrics_collector.start_collection()
        
        # 启动告警检查
        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("监控系统启动完成")
    
    def stop_monitoring(self):
        """停止监控系统"""
        logger.info("停止监控系统")
        
        self.is_running = False
        
        # 停止指标收集
        self.metrics_collector.stop_collection()
        
        # 等待监控线程结束
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        logger.info("监控系统已停止")
    
    def _monitoring_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 检查告警
                self.alert_manager.check_alerts(self.metrics_collector)
                
                # 等待下一次检查
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(60)
    
    def _setup_default_alerts(self):
        """设置默认告警规则"""
        # CPU使用率告警
        self.alert_manager.add_alert_rule(
            "system.cpu.usage", 90, "greater", "high", "CPU使用率过高"
        )
        
        # 内存使用率告警
        self.alert_manager.add_alert_rule(
            "system.memory.usage", 90, "greater", "high", "内存使用率过高"
        )
        
        # 磁盘使用率告警
        self.alert_manager.add_alert_rule(
            "system.disk.usage", 85, "greater", "medium", "磁盘使用率过高"
        )
        
        # API错误率告警
        self.alert_manager.add_alert_rule(
            "business.api.error_rate", 0.1, "greater", "critical", "API错误率过高"
        )
        
        # API响应时间告警
        self.alert_manager.add_alert_rule(
            "business.api.response_time", 5.0, "greater", "medium", "API响应时间过长"
        )
    
    def _setup_default_notifications(self):
        """设置默认通知处理器"""
        def log_notification(alert: Alert):
            logger.warning(f"告警通知: [{alert.severity.upper()}] {alert.alert_name} - {alert.message}")
        
        self.alert_manager.add_notification_handler(log_notification)
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "monitoring_active": self.is_running,
            "metrics_count": len(self.metrics_collector.list_metrics()),
            "active_alerts": len(self.alert_manager.get_active_alerts()),
            "alert_rules": len(self.alert_manager.alert_rules),
            "last_collection": datetime.now().isoformat()
        }
    
    def generate_daily_report(self) -> PerformanceReport:
        """生成日报"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)
        
        return self.report_generator.generate_performance_report(
            self.metrics_collector,
            self.alert_manager,
            {"start": start_time, "end": end_time},
            "日报"
        )
    
    def generate_weekly_report(self) -> PerformanceReport:
        """生成周报"""
        end_time = datetime.now()
        start_time = end_time - timedelta(weeks=1)
        
        return self.report_generator.generate_performance_report(
            self.metrics_collector,
            self.alert_manager,
            {"start": start_time, "end": end_time},
            "周报"
        )

# 创建全局监控系统实例
monitoring_system = MonitoringSystem()