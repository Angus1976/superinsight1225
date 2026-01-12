"""
Billing Report Generator for SuperInsight Platform.

Provides automated billing report generation with:
- Multiple report formats (PDF, Excel, HTML)
- Scheduled report generation
- Email distribution
- Custom report templates
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from uuid import uuid4
import logging
import json

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    """Report type enumeration."""
    BILLING_SUMMARY = "billing_summary"
    DETAILED_INVOICE = "detailed_invoice"
    WORK_TIME_REPORT = "work_time_report"
    REWARD_REPORT = "reward_report"
    TAX_REPORT = "tax_report"
    ANALYTICS_REPORT = "analytics_report"
    AUDIT_REPORT = "audit_report"


class ReportFormat(str, Enum):
    """Report format enumeration."""
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"
    CSV = "csv"
    JSON = "json"


class ReportFrequency(str, Enum):
    """Report generation frequency."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ON_DEMAND = "on_demand"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    DELIVERED = "delivered"


@dataclass
class ReportConfig:
    """Report configuration."""
    config_id: str
    name: str
    report_type: ReportType
    format: ReportFormat
    frequency: ReportFrequency
    recipients: List[str] = field(default_factory=list)
    template_id: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    include_charts: bool = True
    include_summary: bool = True
    include_details: bool = True
    language: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReportSection:
    """Report section data."""
    section_id: str
    title: str
    content_type: str  # table, chart, text, summary
    data: Any
    order: int = 0
    style: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedReport:
    """Generated report result."""
    report_id: str
    config_id: str
    report_type: ReportType
    format: ReportFormat
    title: str
    period_start: date
    period_end: date
    sections: List[ReportSection] = field(default_factory=list)
    file_path: Optional[str] = None
    file_size: int = 0
    status: ReportStatus = ReportStatus.PENDING
    generated_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScheduledReport:
    """Scheduled report configuration."""
    schedule_id: str
    config_id: str
    frequency: ReportFrequency
    next_run: datetime
    last_run: Optional[datetime] = None
    run_count: int = 0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class ReportDataCollector:
    """
    Collects data for report generation.
    
    Aggregates billing, work time, and reward data for reports.
    """
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
    
    async def collect_billing_data(
        self,
        tenant_id: str,
        start_date: date,
        end_date: date,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Collect billing data for report."""
        filters = filters or {}
        
        # Simulated data collection
        billing_data = {
            "tenant_id": tenant_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_revenue": Decimal("150000.00"),
                "total_invoices": 45,
                "paid_invoices": 38,
                "pending_invoices": 7,
                "average_invoice_value": Decimal("3333.33"),
            },
            "by_project": [],
            "by_client": [],
            "by_service_type": [],
            "trends": [],
        }
        
        return billing_data
    
    async def collect_work_time_data(
        self,
        tenant_id: str,
        start_date: date,
        end_date: date,
        user_ids: List[str] = None
    ) -> Dict[str, Any]:
        """Collect work time data for report."""
        work_time_data = {
            "tenant_id": tenant_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_hours": Decimal("1250.5"),
                "billable_hours": Decimal("1100.0"),
                "non_billable_hours": Decimal("150.5"),
                "overtime_hours": Decimal("85.0"),
                "utilization_rate": Decimal("88.0"),
            },
            "by_user": [],
            "by_project": [],
            "by_activity_type": [],
            "daily_breakdown": [],
        }
        
        return work_time_data
    
    async def collect_reward_data(
        self,
        tenant_id: str,
        start_date: date,
        end_date: date,
        user_ids: List[str] = None
    ) -> Dict[str, Any]:
        """Collect reward data for report."""
        reward_data = {
            "tenant_id": tenant_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_rewards": Decimal("25000.00"),
                "quality_bonuses": Decimal("10000.00"),
                "efficiency_bonuses": Decimal("8000.00"),
                "milestone_bonuses": Decimal("5000.00"),
                "other_bonuses": Decimal("2000.00"),
            },
            "by_user": [],
            "by_bonus_type": [],
            "top_performers": [],
        }
        
        return reward_data
    
    async def collect_tax_data(
        self,
        tenant_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Collect tax data for report."""
        tax_data = {
            "tenant_id": tenant_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_tax_collected": Decimal("19500.00"),
                "vat_collected": Decimal("15000.00"),
                "service_tax_collected": Decimal("4500.00"),
            },
            "by_jurisdiction": [],
            "by_tax_type": [],
        }
        
        return tax_data


class ReportTemplateEngine:
    """
    Template engine for report generation.
    
    Manages report templates and renders content.
    """
    
    def __init__(self):
        self.templates: Dict[str, Dict[str, Any]] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default report templates."""
        self.templates = {
            "billing_summary": {
                "title": "计费汇总报告",
                "sections": ["summary", "by_project", "by_client", "trends"],
                "styles": {"header_color": "#1890ff", "font": "Microsoft YaHei"},
            },
            "work_time_report": {
                "title": "工时统计报告",
                "sections": ["summary", "by_user", "by_project", "daily_breakdown"],
                "styles": {"header_color": "#52c41a", "font": "Microsoft YaHei"},
            },
            "reward_report": {
                "title": "奖励发放报告",
                "sections": ["summary", "by_user", "by_bonus_type", "top_performers"],
                "styles": {"header_color": "#faad14", "font": "Microsoft YaHei"},
            },
            "tax_report": {
                "title": "税务报告",
                "sections": ["summary", "by_jurisdiction", "by_tax_type"],
                "styles": {"header_color": "#722ed1", "font": "Microsoft YaHei"},
            },
        }
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template by ID."""
        return self.templates.get(template_id)
    
    def register_template(self, template_id: str, template: Dict[str, Any]):
        """Register a custom template."""
        self.templates[template_id] = template
    
    def render_section(
        self,
        section_type: str,
        data: Any,
        template: Dict[str, Any]
    ) -> ReportSection:
        """Render a report section."""
        section_id = str(uuid4())
        
        return ReportSection(
            section_id=section_id,
            title=self._get_section_title(section_type),
            content_type=self._get_content_type(section_type),
            data=data,
            style=template.get("styles", {}),
        )
    
    def _get_section_title(self, section_type: str) -> str:
        """Get section title."""
        titles = {
            "summary": "概要",
            "by_project": "按项目统计",
            "by_client": "按客户统计",
            "by_user": "按用户统计",
            "by_service_type": "按服务类型统计",
            "by_bonus_type": "按奖励类型统计",
            "by_jurisdiction": "按税务管辖区统计",
            "by_tax_type": "按税种统计",
            "trends": "趋势分析",
            "daily_breakdown": "每日明细",
            "top_performers": "优秀员工",
        }
        return titles.get(section_type, section_type)
    
    def _get_content_type(self, section_type: str) -> str:
        """Get content type for section."""
        if section_type == "summary":
            return "summary"
        elif section_type in ["trends", "daily_breakdown"]:
            return "chart"
        elif section_type == "top_performers":
            return "list"
        else:
            return "table"


class ReportScheduler:
    """
    Report scheduling system.
    
    Manages scheduled report generation and delivery.
    """
    
    def __init__(self):
        self.schedules: Dict[str, ScheduledReport] = {}
    
    def create_schedule(
        self,
        config: ReportConfig,
        start_time: datetime = None
    ) -> ScheduledReport:
        """Create a new report schedule."""
        schedule_id = str(uuid4())
        next_run = start_time or self._calculate_next_run(config.frequency)
        
        schedule = ScheduledReport(
            schedule_id=schedule_id,
            config_id=config.config_id,
            frequency=config.frequency,
            next_run=next_run,
        )
        
        self.schedules[schedule_id] = schedule
        logger.info(f"Created report schedule: {schedule_id}")
        
        return schedule
    
    def _calculate_next_run(self, frequency: ReportFrequency) -> datetime:
        """Calculate next run time based on frequency."""
        now = datetime.utcnow()
        
        if frequency == ReportFrequency.DAILY:
            return now + timedelta(days=1)
        elif frequency == ReportFrequency.WEEKLY:
            return now + timedelta(weeks=1)
        elif frequency == ReportFrequency.BIWEEKLY:
            return now + timedelta(weeks=2)
        elif frequency == ReportFrequency.MONTHLY:
            return now + timedelta(days=30)
        elif frequency == ReportFrequency.QUARTERLY:
            return now + timedelta(days=90)
        elif frequency == ReportFrequency.YEARLY:
            return now + timedelta(days=365)
        else:
            return now
    
    def get_due_schedules(self) -> List[ScheduledReport]:
        """Get schedules that are due for execution."""
        now = datetime.utcnow()
        due = []
        
        for schedule in self.schedules.values():
            if schedule.is_active and schedule.next_run <= now:
                due.append(schedule)
        
        return due
    
    def update_schedule_after_run(self, schedule_id: str):
        """Update schedule after successful run."""
        if schedule_id in self.schedules:
            schedule = self.schedules[schedule_id]
            schedule.last_run = datetime.utcnow()
            schedule.run_count += 1
            schedule.next_run = self._calculate_next_run(schedule.frequency)
            logger.info(f"Updated schedule {schedule_id}, next run: {schedule.next_run}")


class ReportDeliveryService:
    """
    Report delivery service.
    
    Handles report distribution via email and other channels.
    """
    
    def __init__(self):
        self.delivery_log: List[Dict[str, Any]] = []
    
    async def deliver_report(
        self,
        report: GeneratedReport,
        recipients: List[str],
        delivery_method: str = "email"
    ) -> bool:
        """Deliver report to recipients."""
        try:
            if delivery_method == "email":
                await self._send_email(report, recipients)
            elif delivery_method == "webhook":
                await self._send_webhook(report, recipients)
            elif delivery_method == "storage":
                await self._save_to_storage(report)
            
            self._log_delivery(report, recipients, delivery_method, True)
            return True
            
        except Exception as e:
            logger.error(f"Report delivery failed: {e}")
            self._log_delivery(report, recipients, delivery_method, False, str(e))
            return False
    
    async def _send_email(self, report: GeneratedReport, recipients: List[str]):
        """Send report via email."""
        # Email sending implementation
        logger.info(f"Sending report {report.report_id} to {len(recipients)} recipients")
        # In production, integrate with email service
    
    async def _send_webhook(self, report: GeneratedReport, recipients: List[str]):
        """Send report via webhook."""
        logger.info(f"Sending report {report.report_id} via webhook")
        # Webhook implementation
    
    async def _save_to_storage(self, report: GeneratedReport):
        """Save report to storage."""
        logger.info(f"Saving report {report.report_id} to storage")
        # Storage implementation
    
    def _log_delivery(
        self,
        report: GeneratedReport,
        recipients: List[str],
        method: str,
        success: bool,
        error: str = None
    ):
        """Log delivery attempt."""
        self.delivery_log.append({
            "report_id": report.report_id,
            "recipients": recipients,
            "method": method,
            "success": success,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        })


class BillingReportGenerator:
    """
    Main billing report generator.
    
    Orchestrates report generation, scheduling, and delivery.
    """
    
    def __init__(self):
        self.data_collector = ReportDataCollector()
        self.template_engine = ReportTemplateEngine()
        self.scheduler = ReportScheduler()
        self.delivery_service = ReportDeliveryService()
        self.configs: Dict[str, ReportConfig] = {}
        self.generated_reports: Dict[str, GeneratedReport] = {}
    
    def create_report_config(
        self,
        name: str,
        report_type: ReportType,
        format: ReportFormat = ReportFormat.PDF,
        frequency: ReportFrequency = ReportFrequency.MONTHLY,
        recipients: List[str] = None,
        **kwargs
    ) -> ReportConfig:
        """Create a new report configuration."""
        config_id = str(uuid4())
        
        config = ReportConfig(
            config_id=config_id,
            name=name,
            report_type=report_type,
            format=format,
            frequency=frequency,
            recipients=recipients or [],
            **kwargs
        )
        
        self.configs[config_id] = config
        logger.info(f"Created report config: {config_id} - {name}")
        
        return config
    
    async def generate_report(
        self,
        config: ReportConfig,
        tenant_id: str,
        start_date: date,
        end_date: date
    ) -> GeneratedReport:
        """Generate a report based on configuration."""
        report_id = str(uuid4())
        
        report = GeneratedReport(
            report_id=report_id,
            config_id=config.config_id,
            report_type=config.report_type,
            format=config.format,
            title=config.name,
            period_start=start_date,
            period_end=end_date,
            status=ReportStatus.GENERATING,
        )
        
        try:
            # Collect data based on report type
            data = await self._collect_report_data(
                config.report_type, tenant_id, start_date, end_date, config.filters
            )
            
            # Get template
            template = self.template_engine.get_template(config.report_type.value)
            if not template:
                template = {"sections": ["summary"], "styles": {}}
            
            # Generate sections
            sections = []
            for i, section_type in enumerate(template.get("sections", [])):
                section_data = data.get(section_type, {})
                section = self.template_engine.render_section(
                    section_type, section_data, template
                )
                section.order = i
                sections.append(section)
            
            report.sections = sections
            report.status = ReportStatus.COMPLETED
            report.generated_at = datetime.utcnow()
            
            # Generate file
            file_path = await self._generate_file(report, config.format)
            report.file_path = file_path
            
            self.generated_reports[report_id] = report
            logger.info(f"Generated report: {report_id}")
            
        except Exception as e:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            logger.error(f"Report generation failed: {e}")
        
        return report
    
    async def _collect_report_data(
        self,
        report_type: ReportType,
        tenant_id: str,
        start_date: date,
        end_date: date,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collect data for report generation."""
        if report_type == ReportType.BILLING_SUMMARY:
            return await self.data_collector.collect_billing_data(
                tenant_id, start_date, end_date, filters
            )
        elif report_type == ReportType.WORK_TIME_REPORT:
            return await self.data_collector.collect_work_time_data(
                tenant_id, start_date, end_date
            )
        elif report_type == ReportType.REWARD_REPORT:
            return await self.data_collector.collect_reward_data(
                tenant_id, start_date, end_date
            )
        elif report_type == ReportType.TAX_REPORT:
            return await self.data_collector.collect_tax_data(
                tenant_id, start_date, end_date
            )
        else:
            return {}
    
    async def _generate_file(
        self,
        report: GeneratedReport,
        format: ReportFormat
    ) -> str:
        """Generate report file."""
        base_path = Path("exports/reports")
        base_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{report.report_type.value}_{timestamp}.{format.value}"
        file_path = base_path / filename
        
        # File generation based on format
        if format == ReportFormat.JSON:
            await self._generate_json(report, file_path)
        elif format == ReportFormat.CSV:
            await self._generate_csv(report, file_path)
        # PDF and Excel generation would require additional libraries
        
        return str(file_path)
    
    async def _generate_json(self, report: GeneratedReport, file_path: Path):
        """Generate JSON report."""
        data = {
            "report_id": report.report_id,
            "title": report.title,
            "period": {
                "start": report.period_start.isoformat(),
                "end": report.period_end.isoformat(),
            },
            "sections": [
                {
                    "title": s.title,
                    "content_type": s.content_type,
                    "data": s.data,
                }
                for s in report.sections
            ],
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    async def _generate_csv(self, report: GeneratedReport, file_path: Path):
        """Generate CSV report."""
        # CSV generation for tabular data
        import csv
        
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Report", report.title])
            writer.writerow(["Period", f"{report.period_start} - {report.period_end}"])
            writer.writerow([])
            
            for section in report.sections:
                writer.writerow([section.title])
                if isinstance(section.data, dict):
                    for key, value in section.data.items():
                        writer.writerow([key, value])
                writer.writerow([])
    
    async def schedule_report(
        self,
        config: ReportConfig,
        start_time: datetime = None
    ) -> ScheduledReport:
        """Schedule a report for automatic generation."""
        return self.scheduler.create_schedule(config, start_time)
    
    async def run_scheduled_reports(self, tenant_id: str):
        """Run all due scheduled reports."""
        due_schedules = self.scheduler.get_due_schedules()
        
        for schedule in due_schedules:
            config = self.configs.get(schedule.config_id)
            if not config:
                continue
            
            # Calculate report period
            end_date = date.today()
            if config.frequency == ReportFrequency.DAILY:
                start_date = end_date - timedelta(days=1)
            elif config.frequency == ReportFrequency.WEEKLY:
                start_date = end_date - timedelta(weeks=1)
            elif config.frequency == ReportFrequency.MONTHLY:
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=30)
            
            # Generate report
            report = await self.generate_report(config, tenant_id, start_date, end_date)
            
            # Deliver report
            if report.status == ReportStatus.COMPLETED and config.recipients:
                await self.delivery_service.deliver_report(report, config.recipients)
                report.status = ReportStatus.DELIVERED
                report.delivered_at = datetime.utcnow()
            
            # Update schedule
            self.scheduler.update_schedule_after_run(schedule.schedule_id)
    
    def get_report(self, report_id: str) -> Optional[GeneratedReport]:
        """Get a generated report by ID."""
        return self.generated_reports.get(report_id)
    
    def list_reports(
        self,
        report_type: ReportType = None,
        status: ReportStatus = None,
        limit: int = 50
    ) -> List[GeneratedReport]:
        """List generated reports with optional filters."""
        reports = list(self.generated_reports.values())
        
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        
        if status:
            reports = [r for r in reports if r.status == status]
        
        # Sort by generation time, newest first
        reports.sort(
            key=lambda r: r.generated_at or datetime.min,
            reverse=True
        )
        
        return reports[:limit]


# Convenience function
def get_billing_report_generator() -> BillingReportGenerator:
    """Get BillingReportGenerator instance."""
    return BillingReportGenerator()
