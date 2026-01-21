"""
Monitoring Report Service for SuperInsight Platform.

Provides comprehensive reporting capabilities including:
- Scheduled report generation
- Trend analysis reports
- Capacity planning recommendations
- SLA compliance reporting
- Custom report templates
- Email notification with retry logic
"""

import logging
import asyncio
import json
import statistics
import smtplib
import ssl
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional, Callable, Tuple
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import hashlib
import os

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    """Types of monitoring reports."""
    SYSTEM_OVERVIEW = "system_overview"
    PERFORMANCE = "performance"
    BUSINESS_METRICS = "business_metrics"
    SLA_COMPLIANCE = "sla_compliance"
    CAPACITY_PLANNING = "capacity_planning"
    TREND_ANALYSIS = "trend_analysis"
    ALERT_SUMMARY = "alert_summary"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Report output formats."""
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    CSV = "csv"


class ReportFrequency(str, Enum):
    """Report generation frequency."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_DEMAND = "on_demand"


@dataclass
class SMTPConfig:
    """SMTP 邮件服务器配置"""
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    timeout: int = 30
    from_address: str = ""
    from_name: str = "SuperInsight Platform"
    
    @classmethod
    def from_env(cls) -> "SMTPConfig":
        """从环境变量加载配置"""
        return cls(
            host=os.getenv("SMTP_HOST", ""),
            port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            timeout=int(os.getenv("SMTP_TIMEOUT", "30")),
            from_address=os.getenv("SMTP_FROM_ADDRESS", ""),
            from_name=os.getenv("SMTP_FROM_NAME", "SuperInsight Platform")
        )
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.host and self.username and self.password)


@dataclass
class SendResult:
    """邮件发送结果"""
    recipient: str
    success: bool
    error_message: Optional[str] = None
    retry_count: int = 0
    sent_at: Optional[datetime] = None


@dataclass
class SLADefinition:
    """SLA definition for monitoring."""
    name: str
    metric_name: str
    target_value: float
    comparison: str  # gte, lte, eq
    measurement_period_hours: int = 24
    description: str = ""
    critical: bool = False


@dataclass
class SLAResult:
    """SLA compliance result."""
    sla_name: str
    metric_name: str
    target_value: float
    actual_value: float
    compliance_percentage: float
    is_compliant: bool
    measurement_period: Tuple[datetime, datetime]
    violations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CapacityPrediction:
    """Capacity prediction result."""
    resource_name: str
    current_usage: float
    current_capacity: float
    predicted_usage_7d: float
    predicted_usage_30d: float
    predicted_usage_90d: float
    days_until_threshold: Optional[int]
    recommendation: str
    confidence: float


@dataclass
class TrendAnalysis:
    """Trend analysis result."""
    metric_name: str
    period_start: datetime
    period_end: datetime
    direction: str  # increasing, decreasing, stable
    change_percentage: float
    slope: float
    average_value: float
    min_value: float
    max_value: float
    volatility: float
    anomaly_count: int
    forecast_next_24h: float


@dataclass
class ReportSchedule:
    """Report schedule configuration."""
    schedule_id: str
    report_type: ReportType
    frequency: ReportFrequency
    recipients: List[str]
    parameters: Dict[str, Any]
    next_run: datetime
    last_run: Optional[datetime] = None
    enabled: bool = True


@dataclass
class GeneratedReport:
    """Generated report record."""
    report_id: str
    report_type: ReportType
    title: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    format: ReportFormat
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsDataProvider:
    """
    Interface for metrics data access.

    This class provides methods to fetch metrics data for reporting.
    In a real implementation, this would connect to your metrics storage.
    """

    def __init__(self):
        self._metrics_cache: Dict[str, List[Tuple[float, float]]] = defaultdict(list)


class EmailSender:
    """
    邮件发送器
    
    支持 HTML 和纯文本格式，带指数退避重试机制
    """
    
    def __init__(self, smtp_config: Optional[SMTPConfig] = None):
        self.config = smtp_config or SMTPConfig.from_env()
        self.retry_count = 3
        self.retry_delays = [1, 2, 4]  # 指数退避：1秒, 2秒, 4秒
        self._send_logs: List[Dict[str, Any]] = []
    
    def _create_message(
        self,
        recipient: str,
        subject: str,
        content: str,
        format: ReportFormat = ReportFormat.HTML
    ) -> MIMEMultipart:
        """创建邮件消息"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.config.from_name} <{self.config.from_address}>"
        msg["To"] = recipient
        
        if format == ReportFormat.HTML:
            # 添加纯文本版本作为备选
            text_content = self._html_to_text(content)
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
            msg.attach(MIMEText(content, "html", "utf-8"))
        else:
            msg.attach(MIMEText(content, "plain", "utf-8"))
        
        return msg
    
    def _html_to_text(self, html: str) -> str:
        """简单的 HTML 转纯文本"""
        import re
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', html)
        # 处理常见 HTML 实体
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        return text.strip()
    
    def _log_send_attempt(
        self,
        recipient: str,
        subject: str,
        success: bool,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ):
        """记录发送尝试"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "recipient": recipient,
            "subject": subject,
            "success": success,
            "error_message": error_message,
            "retry_count": retry_count
        }
        self._send_logs.append(log_entry)
        
        # 保留最近 1000 条日志
        if len(self._send_logs) > 1000:
            self._send_logs = self._send_logs[-1000:]
        
        if success:
            logger.info(f"邮件发送成功: {recipient}, 主题: {subject}")
        else:
            logger.warning(f"邮件发送失败: {recipient}, 错误: {error_message}, 重试次数: {retry_count}")
    
    async def send_report(
        self,
        recipient: str,
        subject: str,
        content: str,
        format: ReportFormat = ReportFormat.HTML
    ) -> SendResult:
        """
        发送报告邮件，带重试机制
        
        Args:
            recipient: 收件人邮箱
            subject: 邮件主题
            content: 邮件内容
            format: 内容格式 (HTML 或纯文本)
            
        Returns:
            SendResult: 发送结果
        """
        if not self.config.is_configured():
            error_msg = "SMTP 未配置"
            self._log_send_attempt(recipient, subject, False, error_msg)
            return SendResult(
                recipient=recipient,
                success=False,
                error_message=error_msg
            )
        
        last_error = None
        
        for attempt in range(self.retry_count):
            try:
                msg = self._create_message(recipient, subject, content, format)
                
                # 在线程池中执行同步 SMTP 操作
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self._send_smtp,
                    msg,
                    recipient
                )
                
                self._log_send_attempt(recipient, subject, True, retry_count=attempt)
                
                return SendResult(
                    recipient=recipient,
                    success=True,
                    retry_count=attempt,
                    sent_at=datetime.now()
                )
                
            except Exception as e:
                last_error = str(e)
                self._log_send_attempt(recipient, subject, False, last_error, attempt)
                
                if attempt < self.retry_count - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"等待 {delay} 秒后重试发送邮件到 {recipient}")
                    await asyncio.sleep(delay)
        
        return SendResult(
            recipient=recipient,
            success=False,
            error_message=last_error,
            retry_count=self.retry_count
        )
    
    def _send_smtp(self, msg: MIMEMultipart, recipient: str):
        """同步发送 SMTP 邮件"""
        if self.config.use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.config.host, self.config.port, timeout=self.config.timeout) as server:
                server.starttls(context=context)
                server.login(self.config.username, self.config.password)
                server.sendmail(self.config.from_address, recipient, msg.as_string())
        else:
            with smtplib.SMTP(self.config.host, self.config.port, timeout=self.config.timeout) as server:
                server.login(self.config.username, self.config.password)
                server.sendmail(self.config.from_address, recipient, msg.as_string())
    
    async def send_batch(
        self,
        recipients: List[str],
        subject: str,
        content: str,
        format: ReportFormat = ReportFormat.HTML
    ) -> List[SendResult]:
        """
        并发发送给多个收件人
        
        Args:
            recipients: 收件人列表
            subject: 邮件主题
            content: 邮件内容
            format: 内容格式
            
        Returns:
            List[SendResult]: 所有发送结果
        """
        if not recipients:
            return []
        
        # 并发发送
        tasks = [
            self.send_report(recipient, subject, content, format)
            for recipient in recipients
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(SendResult(
                    recipient=recipients[i],
                    success=False,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        # 统计结果
        success_count = sum(1 for r in processed_results if r.success)
        logger.info(f"批量发送完成: {success_count}/{len(recipients)} 成功")
        
        return processed_results
    
    def get_send_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取发送日志"""
        return self._send_logs[-limit:]


class MetricsDataProviderImpl(MetricsDataProvider):
    """
    MetricsDataProvider 的具体实现
    """
    pass


# 将方法添加到 MetricsDataProvider 类
def _mp_record_metric(self, name: str, value: float, timestamp: Optional[float] = None):
    """Record a metric value."""
    ts = timestamp or datetime.now().timestamp()
    self._metrics_cache[name].append((ts, value))

    # Keep last 10000 points per metric
    if len(self._metrics_cache[name]) > 10000:
        self._metrics_cache[name] = self._metrics_cache[name][-10000:]


MetricsDataProvider.record_metric = _mp_record_metric


async def _mp_get_metric_values(
    self,
    metric_name: str,
    start_time: datetime,
    end_time: datetime
) -> List[Tuple[datetime, float]]:
    """Get metric values for a time range."""
    start_ts = start_time.timestamp()
    end_ts = end_time.timestamp()

    values = [
        (datetime.fromtimestamp(ts), val)
        for ts, val in self._metrics_cache.get(metric_name, [])
        if start_ts <= ts <= end_ts
    ]

    return sorted(values, key=lambda x: x[0])


MetricsDataProvider.get_metric_values = _mp_get_metric_values


async def _mp_get_metric_summary(
    self,
    metric_name: str,
    start_time: datetime,
    end_time: datetime
) -> Dict[str, Any]:
    """Get summary statistics for a metric in a time range."""
    values = await self.get_metric_values(metric_name, start_time, end_time)

    if not values:
        return {
            "metric_name": metric_name,
            "count": 0,
            "min": None,
            "max": None,
            "avg": None,
            "median": None,
            "std_dev": None
        }

    vals = [v for _, v in values]

    return {
        "metric_name": metric_name,
        "count": len(vals),
        "min": min(vals),
        "max": max(vals),
        "avg": statistics.mean(vals),
        "median": statistics.median(vals),
        "std_dev": statistics.stdev(vals) if len(vals) > 1 else 0,
        "first_value": vals[0],
        "last_value": vals[-1],
        "first_timestamp": values[0][0].isoformat(),
        "last_timestamp": values[-1][0].isoformat()
    }


MetricsDataProvider.get_metric_summary = _mp_get_metric_summary


async def _mp_get_available_metrics(self) -> List[str]:
    """Get list of available metrics."""
    return list(self._metrics_cache.keys())


MetricsDataProvider.get_available_metrics = _mp_get_available_metrics


class SLAMonitor:
    """
    SLA compliance monitoring and reporting.

    Tracks SLA definitions and calculates compliance metrics.
    """

    def __init__(self, data_provider: MetricsDataProvider):
        self.data_provider = data_provider
        self.sla_definitions: Dict[str, SLADefinition] = {}
        self._setup_default_slas()

    def _setup_default_slas(self):
        """Setup default SLA definitions."""
        default_slas = [
            SLADefinition(
                name="API Response Time",
                metric_name="api.response_time.p95",
                target_value=2.0,
                comparison="lte",
                measurement_period_hours=24,
                description="95th percentile API response time should be under 2 seconds",
                critical=True
            ),
            SLADefinition(
                name="System Availability",
                metric_name="system.availability.percentage",
                target_value=99.9,
                comparison="gte",
                measurement_period_hours=720,  # 30 days
                description="System should be available 99.9% of the time",
                critical=True
            ),
            SLADefinition(
                name="Error Rate",
                metric_name="api.error_rate.percentage",
                target_value=1.0,
                comparison="lte",
                measurement_period_hours=24,
                description="API error rate should be under 1%",
                critical=True
            ),
            SLADefinition(
                name="Database Query Performance",
                metric_name="database.query.p95",
                target_value=1.0,
                comparison="lte",
                measurement_period_hours=24,
                description="95th percentile database query time should be under 1 second",
                critical=False
            ),
            SLADefinition(
                name="AI Inference Latency",
                metric_name="ai.inference.p95",
                target_value=5.0,
                comparison="lte",
                measurement_period_hours=24,
                description="95th percentile AI inference time should be under 5 seconds",
                critical=False
            ),
            SLADefinition(
                name="Task Completion Rate",
                metric_name="tasks.completion_rate.percentage",
                target_value=95.0,
                comparison="gte",
                measurement_period_hours=168,  # 7 days
                description="Task completion rate should be above 95%",
                critical=False
            )
        ]

        for sla in default_slas:
            self.add_sla(sla)

    def add_sla(self, sla: SLADefinition):
        """Add an SLA definition."""
        self.sla_definitions[sla.name] = sla
        logger.info(f"Added SLA definition: {sla.name}")

    def remove_sla(self, name: str) -> bool:
        """Remove an SLA definition."""
        if name in self.sla_definitions:
            del self.sla_definitions[name]
            return True
        return False

    async def check_sla_compliance(
        self,
        sla_name: str,
        end_time: Optional[datetime] = None
    ) -> Optional[SLAResult]:
        """Check compliance for a specific SLA."""
        if sla_name not in self.sla_definitions:
            return None

        sla = self.sla_definitions[sla_name]
        end_time = end_time or datetime.now()
        start_time = end_time - timedelta(hours=sla.measurement_period_hours)

        # Get metric values
        values = await self.data_provider.get_metric_values(
            sla.metric_name, start_time, end_time
        )

        if not values:
            return SLAResult(
                sla_name=sla_name,
                metric_name=sla.metric_name,
                target_value=sla.target_value,
                actual_value=0,
                compliance_percentage=0,
                is_compliant=False,
                measurement_period=(start_time, end_time),
                violations=[{"error": "No data available"}]
            )

        # Calculate compliance
        vals = [v for _, v in values]
        actual_value = statistics.mean(vals)

        # Find violations
        violations = []
        compliant_count = 0

        for ts, val in values:
            is_compliant = self._check_value_compliance(val, sla.target_value, sla.comparison)

            if is_compliant:
                compliant_count += 1
            else:
                violations.append({
                    "timestamp": ts.isoformat(),
                    "value": val,
                    "target": sla.target_value,
                    "deviation": abs(val - sla.target_value)
                })

        compliance_percentage = (compliant_count / len(values)) * 100

        return SLAResult(
            sla_name=sla_name,
            metric_name=sla.metric_name,
            target_value=sla.target_value,
            actual_value=actual_value,
            compliance_percentage=compliance_percentage,
            is_compliant=compliance_percentage >= 99.0,  # 99% of samples must comply
            measurement_period=(start_time, end_time),
            violations=violations[-10:]  # Last 10 violations
        )

    def _check_value_compliance(self, value: float, target: float, comparison: str) -> bool:
        """Check if a value complies with the target."""
        if comparison == "gte":
            return value >= target
        elif comparison == "lte":
            return value <= target
        elif comparison == "eq":
            return abs(value - target) < 0.001
        return False

    async def check_all_slas(self, end_time: Optional[datetime] = None) -> List[SLAResult]:
        """Check compliance for all SLAs."""
        results = []

        for sla_name in self.sla_definitions:
            result = await self.check_sla_compliance(sla_name, end_time)
            if result:
                results.append(result)

        return results

    async def generate_sla_report(self, end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate comprehensive SLA compliance report."""
        end_time = end_time or datetime.now()
        results = await self.check_all_slas(end_time)

        compliant_count = sum(1 for r in results if r.is_compliant)
        critical_violations = [
            r for r in results
            if not r.is_compliant and self.sla_definitions[r.sla_name].critical
        ]

        return {
            "report_type": "sla_compliance",
            "generated_at": datetime.now().isoformat(),
            "period_end": end_time.isoformat(),
            "summary": {
                "total_slas": len(results),
                "compliant": compliant_count,
                "non_compliant": len(results) - compliant_count,
                "overall_compliance_rate": (compliant_count / len(results) * 100) if results else 0,
                "critical_violations": len(critical_violations)
            },
            "sla_results": [
                {
                    "sla_name": r.sla_name,
                    "metric_name": r.metric_name,
                    "target_value": r.target_value,
                    "actual_value": r.actual_value,
                    "compliance_percentage": r.compliance_percentage,
                    "is_compliant": r.is_compliant,
                    "is_critical": self.sla_definitions[r.sla_name].critical,
                    "measurement_period": {
                        "start": r.measurement_period[0].isoformat(),
                        "end": r.measurement_period[1].isoformat()
                    },
                    "violation_count": len(r.violations)
                }
                for r in results
            ],
            "critical_violations": [
                {
                    "sla_name": r.sla_name,
                    "compliance_percentage": r.compliance_percentage,
                    "recent_violations": r.violations[:5]
                }
                for r in critical_violations
            ]
        }


class CapacityPlanner:
    """
    Capacity planning and prediction system.

    Analyzes resource usage trends to predict future capacity needs.
    """

    def __init__(self, data_provider: MetricsDataProvider):
        self.data_provider = data_provider
        self.resources = {
            "cpu": {
                "metric": "system.cpu.usage_percent",
                "threshold": 80,
                "unit": "percent"
            },
            "memory": {
                "metric": "system.memory.usage_percent",
                "threshold": 85,
                "unit": "percent"
            },
            "disk": {
                "metric": "system.disk.usage_percent",
                "threshold": 90,
                "unit": "percent"
            },
            "database_connections": {
                "metric": "database.connections.active",
                "threshold": 100,
                "unit": "connections"
            }
        }

    async def predict_capacity(
        self,
        resource_name: str,
        days_of_history: int = 30
    ) -> Optional[CapacityPrediction]:
        """Predict capacity needs for a resource."""
        if resource_name not in self.resources:
            return None

        resource = self.resources[resource_name]
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_of_history)

        values = await self.data_provider.get_metric_values(
            resource["metric"], start_time, end_time
        )

        if len(values) < 10:
            return None

        # Extract values and calculate current usage
        vals = [v for _, v in values]
        current_usage = vals[-1]
        avg_usage = statistics.mean(vals)

        # Calculate trend using linear regression
        n = len(vals)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(vals) / n

        numerator = sum((x[i] - x_mean) * (vals[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        # Calculate prediction confidence based on R-squared
        ss_tot = sum((vals[i] - y_mean) ** 2 for i in range(n))
        ss_res = sum((vals[i] - (slope * x[i] + (y_mean - slope * x_mean))) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Predict future usage
        # Convert slope to per-day rate (assuming 1 data point per hour)
        points_per_day = n / days_of_history
        daily_slope = slope * points_per_day

        predicted_7d = current_usage + (daily_slope * 7)
        predicted_30d = current_usage + (daily_slope * 30)
        predicted_90d = current_usage + (daily_slope * 90)

        # Calculate days until threshold
        threshold = resource["threshold"]
        days_until_threshold = None
        if daily_slope > 0 and current_usage < threshold:
            days_until_threshold = int((threshold - current_usage) / daily_slope)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            resource_name, current_usage, predicted_30d, threshold, days_until_threshold
        )

        return CapacityPrediction(
            resource_name=resource_name,
            current_usage=current_usage,
            current_capacity=threshold,
            predicted_usage_7d=min(100, max(0, predicted_7d)),
            predicted_usage_30d=min(100, max(0, predicted_30d)),
            predicted_usage_90d=min(100, max(0, predicted_90d)),
            days_until_threshold=days_until_threshold,
            recommendation=recommendation,
            confidence=max(0, min(1, r_squared))
        )

    def _generate_recommendation(
        self,
        resource_name: str,
        current: float,
        predicted_30d: float,
        threshold: float,
        days_until_threshold: Optional[int]
    ) -> str:
        """Generate capacity planning recommendation."""
        if current >= threshold * 0.9:
            return f"CRITICAL: {resource_name} usage is at {current:.1f}%. Immediate action required."

        if days_until_threshold is not None and days_until_threshold <= 7:
            return f"URGENT: {resource_name} will reach capacity in ~{days_until_threshold} days. Plan expansion now."

        if days_until_threshold is not None and days_until_threshold <= 30:
            return f"WARNING: {resource_name} will reach capacity in ~{days_until_threshold} days. Schedule expansion."

        if predicted_30d > threshold * 0.8:
            return f"MONITOR: {resource_name} predicted to reach {predicted_30d:.1f}% in 30 days. Monitor closely."

        return f"OK: {resource_name} capacity is sufficient. Current usage: {current:.1f}%"

    async def generate_capacity_report(self, days_of_history: int = 30) -> Dict[str, Any]:
        """Generate comprehensive capacity planning report."""
        predictions = []

        for resource_name in self.resources:
            prediction = await self.predict_capacity(resource_name, days_of_history)
            if prediction:
                predictions.append(prediction)

        # Identify urgent items
        urgent = [p for p in predictions if p.days_until_threshold and p.days_until_threshold <= 30]
        critical = [p for p in predictions if p.current_usage >= self.resources[p.resource_name]["threshold"] * 0.9]

        return {
            "report_type": "capacity_planning",
            "generated_at": datetime.now().isoformat(),
            "analysis_period_days": days_of_history,
            "summary": {
                "resources_analyzed": len(predictions),
                "critical_resources": len(critical),
                "urgent_resources": len(urgent),
                "overall_status": "critical" if critical else ("urgent" if urgent else "healthy")
            },
            "predictions": [
                {
                    "resource": p.resource_name,
                    "current_usage": p.current_usage,
                    "threshold": p.current_capacity,
                    "predicted_7d": p.predicted_usage_7d,
                    "predicted_30d": p.predicted_usage_30d,
                    "predicted_90d": p.predicted_usage_90d,
                    "days_until_threshold": p.days_until_threshold,
                    "confidence": p.confidence,
                    "recommendation": p.recommendation
                }
                for p in predictions
            ],
            "action_items": [
                {
                    "priority": "critical" if p.current_usage >= self.resources[p.resource_name]["threshold"] * 0.9 else "high",
                    "resource": p.resource_name,
                    "action": p.recommendation,
                    "deadline": (datetime.now() + timedelta(days=p.days_until_threshold)).isoformat()
                    if p.days_until_threshold else None
                }
                for p in urgent + critical
            ]
        }


class TrendAnalyzer:
    """
    Trend analysis system for metrics.

    Analyzes historical data to identify trends and patterns.
    """

    def __init__(self, data_provider: MetricsDataProvider):
        self.data_provider = data_provider

    async def analyze_trend(
        self,
        metric_name: str,
        period_hours: int = 24
    ) -> Optional[TrendAnalysis]:
        """Analyze trend for a specific metric."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=period_hours)

        values = await self.data_provider.get_metric_values(
            metric_name, start_time, end_time
        )

        if len(values) < 5:
            return None

        vals = [v for _, v in values]

        # Calculate basic statistics
        avg_value = statistics.mean(vals)
        min_value = min(vals)
        max_value = max(vals)
        volatility = statistics.stdev(vals) / avg_value if avg_value > 0 else 0

        # Calculate trend using linear regression
        n = len(vals)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(vals) / n

        numerator = sum((x[i] - x_mean) * (vals[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        # Determine trend direction
        if slope > 0.01:
            direction = "increasing"
        elif slope < -0.01:
            direction = "decreasing"
        else:
            direction = "stable"

        # Calculate change percentage
        if vals[0] != 0:
            change_percentage = ((vals[-1] - vals[0]) / abs(vals[0])) * 100
        else:
            change_percentage = 0

        # Count anomalies (values more than 2 std from mean)
        std = statistics.stdev(vals) if len(vals) > 1 else 0
        anomaly_count = sum(1 for v in vals if abs(v - avg_value) > 2 * std) if std > 0 else 0

        # Forecast next 24 hours
        forecast_next_24h = vals[-1] + (slope * (n // period_hours) * 24)

        return TrendAnalysis(
            metric_name=metric_name,
            period_start=start_time,
            period_end=end_time,
            direction=direction,
            change_percentage=change_percentage,
            slope=slope,
            average_value=avg_value,
            min_value=min_value,
            max_value=max_value,
            volatility=volatility,
            anomaly_count=anomaly_count,
            forecast_next_24h=forecast_next_24h
        )

    async def generate_trend_report(
        self,
        metric_names: Optional[List[str]] = None,
        period_hours: int = 24
    ) -> Dict[str, Any]:
        """Generate comprehensive trend analysis report."""
        if metric_names is None:
            metric_names = await self.data_provider.get_available_metrics()

        analyses = []
        for metric_name in metric_names:
            analysis = await self.analyze_trend(metric_name, period_hours)
            if analysis:
                analyses.append(analysis)

        # Categorize by trend direction
        increasing = [a for a in analyses if a.direction == "increasing"]
        decreasing = [a for a in analyses if a.direction == "decreasing"]
        stable = [a for a in analyses if a.direction == "stable"]

        # Find significant changes
        significant = [a for a in analyses if abs(a.change_percentage) > 10]

        return {
            "report_type": "trend_analysis",
            "generated_at": datetime.now().isoformat(),
            "period_hours": period_hours,
            "summary": {
                "metrics_analyzed": len(analyses),
                "increasing": len(increasing),
                "decreasing": len(decreasing),
                "stable": len(stable),
                "significant_changes": len(significant)
            },
            "trends": [
                {
                    "metric_name": a.metric_name,
                    "direction": a.direction,
                    "change_percentage": a.change_percentage,
                    "average_value": a.average_value,
                    "min_value": a.min_value,
                    "max_value": a.max_value,
                    "volatility": a.volatility,
                    "anomaly_count": a.anomaly_count,
                    "forecast_next_24h": a.forecast_next_24h
                }
                for a in analyses
            ],
            "significant_changes": [
                {
                    "metric_name": a.metric_name,
                    "change_percentage": a.change_percentage,
                    "direction": a.direction,
                    "current_value": a.average_value
                }
                for a in sorted(significant, key=lambda x: abs(x.change_percentage), reverse=True)
            ],
            "high_volatility": [
                {
                    "metric_name": a.metric_name,
                    "volatility": a.volatility,
                    "average_value": a.average_value
                }
                for a in sorted(analyses, key=lambda x: x.volatility, reverse=True)[:5]
            ]
        }


class MonitoringReportService:
    """
    Central monitoring report service.

    Coordinates report generation, scheduling, and distribution.
    """

    def __init__(self, smtp_config: Optional[SMTPConfig] = None):
        self.data_provider = MetricsDataProvider()
        self.sla_monitor = SLAMonitor(self.data_provider)
        self.capacity_planner = CapacityPlanner(self.data_provider)
        self.trend_analyzer = TrendAnalyzer(self.data_provider)
        
        # 初始化邮件发送器
        self.email_sender = EmailSender(smtp_config)

        self.report_schedules: Dict[str, ReportSchedule] = {}
        self.report_history: List[GeneratedReport] = []
        self.report_templates: Dict[str, Dict[str, Any]] = {}

        self._scheduler_task: Optional[asyncio.Task] = None
        self._is_running = False

        self._setup_default_templates()

    def _setup_default_templates(self):
        """Setup default report templates."""
        self.report_templates = {
            "daily_operations": {
                "report_type": ReportType.SYSTEM_OVERVIEW,
                "include_sections": ["system_health", "alerts", "performance", "trends"],
                "period_hours": 24
            },
            "weekly_business": {
                "report_type": ReportType.BUSINESS_METRICS,
                "include_sections": ["kpis", "trends", "forecasts"],
                "period_hours": 168
            },
            "monthly_sla": {
                "report_type": ReportType.SLA_COMPLIANCE,
                "include_sections": ["compliance", "violations", "recommendations"],
                "period_hours": 720
            },
            "capacity_review": {
                "report_type": ReportType.CAPACITY_PLANNING,
                "include_sections": ["current_usage", "predictions", "recommendations"],
                "history_days": 30
            }
        }

    async def start(self):
        """Start the report service scheduler."""
        if self._is_running:
            return

        self._is_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Report service started")

    async def stop(self):
        """Stop the report service scheduler."""
        self._is_running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("Report service stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop for report generation."""
        while self._is_running:
            try:
                current_time = datetime.now()

                for schedule_id, schedule in list(self.report_schedules.items()):
                    if not schedule.enabled:
                        continue

                    if current_time >= schedule.next_run:
                        await self._execute_scheduled_report(schedule)

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)

    async def _execute_scheduled_report(self, schedule: ReportSchedule):
        """Execute a scheduled report and send to recipients."""
        try:
            report = await self.generate_report(
                schedule.report_type,
                schedule.parameters
            )

            # 生成报告内容
            report_content = self._format_report_for_email(report)
            subject = f"[SuperInsight] {report.title} - {report.generated_at.strftime('%Y-%m-%d %H:%M')}"
            
            # 发送报告给所有收件人
            if schedule.recipients:
                results = await self.email_sender.send_batch(
                    recipients=schedule.recipients,
                    subject=subject,
                    content=report_content,
                    format=ReportFormat.HTML
                )
                
                # 记录发送结果
                success_count = sum(1 for r in results if r.success)
                logger.info(f"报告发送完成: {success_count}/{len(schedule.recipients)} 成功")

            # Update schedule
            schedule.last_run = datetime.now()
            schedule.next_run = self._calculate_next_run(schedule.frequency)

            logger.info(f"Executed scheduled report: {schedule.schedule_id}")

        except Exception as e:
            logger.error(f"Failed to execute scheduled report {schedule.schedule_id}: {e}")
    
    def _format_report_for_email(self, report: GeneratedReport) -> str:
        """将报告格式化为 HTML 邮件内容"""
        content = report.content
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: #1890ff; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: white; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #1890ff; }}
        .metric-label {{ font-size: 12px; color: #666; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; }}
        .status-ok {{ color: #52c41a; }}
        .status-warning {{ color: #faad14; }}
        .status-error {{ color: #f5222d; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{report.title}</h1>
        <p>生成时间: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="content">
        <div class="summary">
            <h3>报告摘要</h3>
            <p>报告类型: {report.report_type.value}</p>
            <p>时间范围: {report.period_start.strftime('%Y-%m-%d %H:%M')} - {report.period_end.strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        <div class="details">
            <h3>详细内容</h3>
            <pre>{json.dumps(content, indent=2, ensure_ascii=False, default=str)}</pre>
        </div>
    </div>
    <div class="footer">
        <p>此邮件由 SuperInsight AI 数据治理平台自动发送</p>
        <p>如有问题，请联系系统管理员</p>
    </div>
</body>
</html>
"""
        return html

    def _calculate_next_run(self, frequency: ReportFrequency) -> datetime:
        """Calculate next run time based on frequency."""
        now = datetime.now()

        if frequency == ReportFrequency.HOURLY:
            return now + timedelta(hours=1)
        elif frequency == ReportFrequency.DAILY:
            return now + timedelta(days=1)
        elif frequency == ReportFrequency.WEEKLY:
            return now + timedelta(weeks=1)
        elif frequency == ReportFrequency.MONTHLY:
            return now + timedelta(days=30)
        else:
            return now + timedelta(days=365)  # On-demand

    def add_schedule(
        self,
        report_type: ReportType,
        frequency: ReportFrequency,
        recipients: List[str],
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a new report schedule."""
        schedule_id = hashlib.md5(
            f"{report_type.value}:{frequency.value}:{','.join(recipients)}".encode()
        ).hexdigest()[:12]

        schedule = ReportSchedule(
            schedule_id=schedule_id,
            report_type=report_type,
            frequency=frequency,
            recipients=recipients,
            parameters=parameters or {},
            next_run=self._calculate_next_run(frequency)
        )

        self.report_schedules[schedule_id] = schedule
        logger.info(f"Added report schedule: {schedule_id}")

        return schedule_id

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a report schedule."""
        if schedule_id in self.report_schedules:
            del self.report_schedules[schedule_id]
            return True
        return False

    def get_schedules(self) -> List[Dict[str, Any]]:
        """Get all report schedules."""
        return [
            {
                "schedule_id": s.schedule_id,
                "report_type": s.report_type.value,
                "frequency": s.frequency.value,
                "recipients": s.recipients,
                "next_run": s.next_run.isoformat(),
                "last_run": s.last_run.isoformat() if s.last_run else None,
                "enabled": s.enabled
            }
            for s in self.report_schedules.values()
        ]

    async def generate_report(
        self,
        report_type: ReportType,
        parameters: Optional[Dict[str, Any]] = None,
        output_format: ReportFormat = ReportFormat.JSON
    ) -> GeneratedReport:
        """Generate a report on demand."""
        parameters = parameters or {}
        end_time = datetime.now()
        period_hours = parameters.get("period_hours", 24)
        start_time = end_time - timedelta(hours=period_hours)

        content = {}

        if report_type == ReportType.SYSTEM_OVERVIEW:
            content = await self._generate_system_overview(parameters)
        elif report_type == ReportType.SLA_COMPLIANCE:
            content = await self.sla_monitor.generate_sla_report(end_time)
        elif report_type == ReportType.CAPACITY_PLANNING:
            content = await self.capacity_planner.generate_capacity_report(
                parameters.get("history_days", 30)
            )
        elif report_type == ReportType.TREND_ANALYSIS:
            content = await self.trend_analyzer.generate_trend_report(
                parameters.get("metrics"),
                period_hours
            )
        elif report_type == ReportType.PERFORMANCE:
            content = await self._generate_performance_report(parameters)
        elif report_type == ReportType.BUSINESS_METRICS:
            content = await self._generate_business_report(parameters)
        elif report_type == ReportType.ALERT_SUMMARY:
            content = await self._generate_alert_report(parameters)

        report = GeneratedReport(
            report_id=f"rpt_{int(end_time.timestamp())}_{report_type.value}",
            report_type=report_type,
            title=f"{report_type.value.replace('_', ' ').title()} Report",
            generated_at=end_time,
            period_start=start_time,
            period_end=end_time,
            format=output_format,
            content=content
        )

        self.report_history.append(report)

        # Keep only last 100 reports
        if len(self.report_history) > 100:
            self.report_history = self.report_history[-100:]

        return report

    async def _generate_system_overview(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate system overview report."""
        period_hours = parameters.get("period_hours", 24)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=period_hours)

        # Get key metrics summaries
        metrics = ["system.cpu.usage_percent", "system.memory.usage_percent",
                   "system.disk.usage_percent", "api.response_time", "api.error_rate"]

        metric_summaries = {}
        for metric in metrics:
            summary = await self.data_provider.get_metric_summary(metric, start_time, end_time)
            metric_summaries[metric] = summary

        return {
            "report_type": "system_overview",
            "generated_at": end_time.isoformat(),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": period_hours
            },
            "system_health": {
                "cpu": metric_summaries.get("system.cpu.usage_percent", {}),
                "memory": metric_summaries.get("system.memory.usage_percent", {}),
                "disk": metric_summaries.get("system.disk.usage_percent", {})
            },
            "api_performance": {
                "response_time": metric_summaries.get("api.response_time", {}),
                "error_rate": metric_summaries.get("api.error_rate", {})
            }
        }

    async def _generate_performance_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance report."""
        period_hours = parameters.get("period_hours", 24)

        # Get trend analysis for performance metrics
        performance_metrics = [
            "api.response_time.p50", "api.response_time.p95", "api.response_time.p99",
            "database.query.p50", "database.query.p95",
            "ai.inference.duration"
        ]

        trend_report = await self.trend_analyzer.generate_trend_report(
            performance_metrics, period_hours
        )

        return {
            "report_type": "performance",
            "generated_at": datetime.now().isoformat(),
            "period_hours": period_hours,
            **trend_report
        }

    async def _generate_business_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate business metrics report."""
        period_hours = parameters.get("period_hours", 168)  # Default to 7 days

        business_metrics = [
            "business.annotations.completed", "business.annotations.quality_score",
            "business.users.active", "business.projects.completion_rate"
        ]

        trend_report = await self.trend_analyzer.generate_trend_report(
            business_metrics, period_hours
        )

        return {
            "report_type": "business_metrics",
            "generated_at": datetime.now().isoformat(),
            "period_hours": period_hours,
            **trend_report
        }

    async def _generate_alert_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate alert summary report."""
        period_hours = parameters.get("period_hours", 24)

        # This would integrate with alert_manager in production
        return {
            "report_type": "alert_summary",
            "generated_at": datetime.now().isoformat(),
            "period_hours": period_hours,
            "summary": {
                "total_alerts": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "resolved": 0,
                "pending": 0
            },
            "top_alert_types": [],
            "resolution_metrics": {
                "avg_resolution_time_minutes": 0,
                "resolution_rate": 0
            }
        }

    def get_report_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent report history."""
        reports = self.report_history[-limit:]
        return [
            {
                "report_id": r.report_id,
                "report_type": r.report_type.value,
                "title": r.title,
                "generated_at": r.generated_at.isoformat(),
                "period_start": r.period_start.isoformat(),
                "period_end": r.period_end.isoformat(),
                "format": r.format.value
            }
            for r in reversed(reports)
        ]

    # SLA management methods
    def add_sla(self, sla: SLADefinition):
        """Add an SLA definition."""
        self.sla_monitor.add_sla(sla)

    def remove_sla(self, name: str) -> bool:
        """Remove an SLA definition."""
        return self.sla_monitor.remove_sla(name)

    def get_slas(self) -> List[Dict[str, Any]]:
        """Get all SLA definitions."""
        return [
            {
                "name": sla.name,
                "metric_name": sla.metric_name,
                "target_value": sla.target_value,
                "comparison": sla.comparison,
                "measurement_period_hours": sla.measurement_period_hours,
                "description": sla.description,
                "critical": sla.critical
            }
            for sla in self.sla_monitor.sla_definitions.values()
        ]

    # Metrics data recording (for testing/demo)
    def record_metric(self, name: str, value: float, timestamp: Optional[float] = None):
        """Record a metric value for reporting."""
        self.data_provider.record_metric(name, value, timestamp)


# Global instance
monitoring_report_service = MonitoringReportService()
