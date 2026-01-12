"""
Quality Report Generator for SuperInsight Platform.

Provides quality governance report generation:
- Multiple report types
- Template-based generation
- Multi-format export
- Scheduled generation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid
import json

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    """Types of quality reports."""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_SUMMARY = "weekly_summary"
    MONTHLY_SUMMARY = "monthly_summary"
    QUALITY_METRICS = "quality_metrics"
    ANOMALY_REPORT = "anomaly_report"
    ANNOTATOR_PERFORMANCE = "annotator_performance"
    PROJECT_STATUS = "project_status"
    COMPLIANCE_REPORT = "compliance_report"
    TREND_ANALYSIS = "trend_analysis"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Report output formats."""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    MARKDOWN = "markdown"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    """Represents a section in a report."""
    section_id: str
    title: str
    content_type: str  # text, table, chart, metrics
    content: Any
    order: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "content_type": self.content_type,
            "content": self.content,
            "order": self.order,
            "metadata": self.metadata
        }


@dataclass
class QualityReport:
    """Represents a generated quality report."""
    report_id: str
    report_type: ReportType
    title: str
    description: Optional[str] = None
    status: ReportStatus = ReportStatus.PENDING
    format: ReportFormat = ReportFormat.JSON
    sections: List[ReportSection] = field(default_factory=list)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    project_id: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    generated_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    file_path: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "format": self.format.value,
            "sections": [s.to_dict() for s in self.sections],
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "project_id": self.project_id,
            "filters": self.filters,
            "summary": self.summary,
            "generated_by": self.generated_by,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "file_path": self.file_path,
            "error_message": self.error_message
        }


@dataclass
class ReportTemplate:
    """Template for report generation."""
    template_id: str
    name: str
    report_type: ReportType
    description: str
    section_configs: List[Dict[str, Any]] = field(default_factory=list)
    default_filters: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None  # cron expression
    recipients: List[str] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "report_type": self.report_type.value,
            "description": self.description,
            "section_configs": self.section_configs,
            "default_filters": self.default_filters,
            "schedule": self.schedule,
            "recipients": self.recipients,
            "enabled": self.enabled
        }


class ReportDataCollector:
    """Collects data for report generation."""

    def __init__(self):
        self.data_sources: Dict[str, Any] = {}

    def register_data_source(self, name: str, source: Any):
        """Register a data source."""
        self.data_sources[name] = source

    async def collect_quality_metrics(
        self,
        project_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Collect quality metrics data."""
        # Placeholder - would integrate with actual quality systems
        return {
            "overall_accuracy": 0.92,
            "agreement_rate": 0.85,
            "completion_rate": 0.88,
            "rejection_rate": 0.05,
            "avg_quality_score": 0.89,
            "total_annotations": 15000,
            "reviewed_annotations": 12000,
            "period": {
                "start": period_start.isoformat() if period_start else None,
                "end": period_end.isoformat() if period_end else None
            }
        }

    async def collect_anomaly_data(
        self,
        project_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Collect anomaly detection data."""
        return {
            "total_anomalies": 45,
            "resolved_anomalies": 38,
            "pending_anomalies": 7,
            "by_type": {
                "statistical": 20,
                "threshold": 15,
                "pattern": 10
            },
            "by_severity": {
                "critical": 5,
                "high": 12,
                "medium": 18,
                "low": 10
            },
            "resolution_rate": 0.84,
            "avg_resolution_time_hours": 4.5
        }

    async def collect_annotator_performance(
        self,
        project_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Collect annotator performance data."""
        return {
            "total_annotators": 25,
            "active_annotators": 20,
            "top_performers": [
                {"id": "ann_001", "name": "标注员A", "accuracy": 0.96, "tasks": 500},
                {"id": "ann_002", "name": "标注员B", "accuracy": 0.94, "tasks": 480},
                {"id": "ann_003", "name": "标注员C", "accuracy": 0.93, "tasks": 450}
            ],
            "avg_accuracy": 0.89,
            "avg_tasks_per_day": 45,
            "training_needed": 3
        }

    async def collect_project_status(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """Collect project status data."""
        return {
            "project_id": project_id,
            "total_tasks": 10000,
            "completed_tasks": 7500,
            "in_progress_tasks": 1500,
            "pending_tasks": 1000,
            "completion_rate": 0.75,
            "quality_score": 0.91,
            "estimated_completion": (datetime.now() + timedelta(days=14)).isoformat()
        }

    async def collect_compliance_data(
        self,
        project_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Collect compliance data."""
        return {
            "compliance_score": 0.95,
            "checks_passed": 48,
            "checks_failed": 2,
            "checks_warning": 5,
            "by_category": {
                "data_privacy": {"passed": 15, "failed": 0, "warning": 1},
                "quality_standards": {"passed": 18, "failed": 1, "warning": 2},
                "process_compliance": {"passed": 15, "failed": 1, "warning": 2}
            },
            "issues": [
                {"id": "issue_001", "category": "quality_standards", "severity": "medium", "description": "部分标注缺少必要字段"},
                {"id": "issue_002", "category": "process_compliance", "severity": "low", "description": "审核流程延迟"}
            ]
        }


class ReportFormatter:
    """Formats reports into different output formats."""

    def format_json(self, report: QualityReport) -> str:
        """Format report as JSON."""
        return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)

    def format_markdown(self, report: QualityReport) -> str:
        """Format report as Markdown."""
        lines = [
            f"# {report.title}",
            "",
            f"**报告类型**: {report.report_type.value}",
            f"**生成时间**: {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        
        if report.period_start and report.period_end:
            lines.append(f"**报告周期**: {report.period_start.strftime('%Y-%m-%d')} 至 {report.period_end.strftime('%Y-%m-%d')}")
        
        if report.description:
            lines.extend(["", report.description])
        
        # Summary section
        if report.summary:
            lines.extend(["", "## 摘要", ""])
            for key, value in report.summary.items():
                lines.append(f"- **{key}**: {value}")
        
        # Content sections
        for section in sorted(report.sections, key=lambda s: s.order):
            lines.extend(["", f"## {section.title}", ""])
            
            if section.content_type == "text":
                lines.append(str(section.content))
            elif section.content_type == "metrics":
                for key, value in section.content.items():
                    if isinstance(value, float):
                        lines.append(f"- **{key}**: {value:.2%}" if value <= 1 else f"- **{key}**: {value:.2f}")
                    else:
                        lines.append(f"- **{key}**: {value}")
            elif section.content_type == "table":
                lines.extend(self._format_table_markdown(section.content))
            elif section.content_type == "list":
                for item in section.content:
                    lines.append(f"- {item}")
        
        return "\n".join(lines)

    def _format_table_markdown(self, table_data: Dict[str, Any]) -> List[str]:
        """Format table data as Markdown."""
        lines = []
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        
        if headers:
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        for row in rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
        
        return lines

    def format_html(self, report: QualityReport) -> str:
        """Format report as HTML."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            f"<title>{report.title}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; }",
            "h2 { color: #666; border-bottom: 1px solid #ddd; }",
            "table { border-collapse: collapse; width: 100%; margin: 10px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f4f4f4; }",
            ".metric { display: inline-block; margin: 10px; padding: 15px; background: #f9f9f9; border-radius: 5px; }",
            ".metric-value { font-size: 24px; font-weight: bold; color: #333; }",
            ".metric-label { font-size: 12px; color: #666; }",
            "</style>",
            "</head><body>",
            f"<h1>{report.title}</h1>",
            f"<p><strong>生成时间:</strong> {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>"
        ]
        
        if report.period_start and report.period_end:
            html_parts.append(
                f"<p><strong>报告周期:</strong> {report.period_start.strftime('%Y-%m-%d')} 至 {report.period_end.strftime('%Y-%m-%d')}</p>"
            )
        
        # Summary
        if report.summary:
            html_parts.append("<h2>摘要</h2><div class='metrics'>")
            for key, value in report.summary.items():
                display_value = f"{value:.2%}" if isinstance(value, float) and value <= 1 else str(value)
                html_parts.append(
                    f"<div class='metric'><div class='metric-value'>{display_value}</div>"
                    f"<div class='metric-label'>{key}</div></div>"
                )
            html_parts.append("</div>")
        
        # Sections
        for section in sorted(report.sections, key=lambda s: s.order):
            html_parts.append(f"<h2>{section.title}</h2>")
            
            if section.content_type == "text":
                html_parts.append(f"<p>{section.content}</p>")
            elif section.content_type == "metrics":
                html_parts.append("<div class='metrics'>")
                for key, value in section.content.items():
                    display_value = f"{value:.2%}" if isinstance(value, float) and value <= 1 else str(value)
                    html_parts.append(
                        f"<div class='metric'><div class='metric-value'>{display_value}</div>"
                        f"<div class='metric-label'>{key}</div></div>"
                    )
                html_parts.append("</div>")
            elif section.content_type == "table":
                html_parts.extend(self._format_table_html(section.content))
        
        html_parts.extend(["</body></html>"])
        return "\n".join(html_parts)

    def _format_table_html(self, table_data: Dict[str, Any]) -> List[str]:
        """Format table data as HTML."""
        lines = ["<table>"]
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        
        if headers:
            lines.append("<thead><tr>")
            for header in headers:
                lines.append(f"<th>{header}</th>")
            lines.append("</tr></thead>")
        
        lines.append("<tbody>")
        for row in rows:
            lines.append("<tr>")
            for cell in row:
                lines.append(f"<td>{cell}</td>")
            lines.append("</tr>")
        lines.append("</tbody></table>")
        
        return lines

    def format_csv(self, report: QualityReport) -> str:
        """Format report as CSV (for tabular data)."""
        lines = []
        
        for section in report.sections:
            if section.content_type == "table":
                table_data = section.content
                headers = table_data.get("headers", [])
                rows = table_data.get("rows", [])
                
                if headers:
                    lines.append(",".join(f'"{h}"' for h in headers))
                
                for row in rows:
                    lines.append(",".join(f'"{cell}"' for cell in row))
                
                lines.append("")  # Empty line between tables
        
        return "\n".join(lines)


class QualityReportGenerator:
    """
    Quality report generation service.
    
    Provides:
    - Multiple report types
    - Template-based generation
    - Multi-format export
    - Report scheduling
    """

    def __init__(self):
        self.reports: Dict[str, QualityReport] = {}
        self.templates: Dict[str, ReportTemplate] = {}
        self.data_collector = ReportDataCollector()
        self.formatter = ReportFormatter()
        self._initialize_default_templates()

    def _initialize_default_templates(self):
        """Initialize default report templates."""
        templates = [
            ReportTemplate(
                template_id="daily_quality",
                name="每日质量报告",
                report_type=ReportType.DAILY_SUMMARY,
                description="每日质量指标汇总",
                section_configs=[
                    {"type": "metrics", "title": "质量指标", "data_source": "quality_metrics"},
                    {"type": "table", "title": "异常汇总", "data_source": "anomaly_summary"},
                    {"type": "metrics", "title": "完成情况", "data_source": "completion_stats"}
                ],
                schedule="0 9 * * *"  # Daily at 9 AM
            ),
            ReportTemplate(
                template_id="weekly_performance",
                name="每周绩效报告",
                report_type=ReportType.WEEKLY_SUMMARY,
                description="每周标注员绩效汇总",
                section_configs=[
                    {"type": "metrics", "title": "整体绩效", "data_source": "performance_metrics"},
                    {"type": "table", "title": "标注员排名", "data_source": "annotator_ranking"},
                    {"type": "text", "title": "改进建议", "data_source": "recommendations"}
                ],
                schedule="0 9 * * 1"  # Weekly on Monday at 9 AM
            ),
            ReportTemplate(
                template_id="monthly_compliance",
                name="月度合规报告",
                report_type=ReportType.COMPLIANCE_REPORT,
                description="月度合规检查报告",
                section_configs=[
                    {"type": "metrics", "title": "合规评分", "data_source": "compliance_score"},
                    {"type": "table", "title": "检查结果", "data_source": "compliance_checks"},
                    {"type": "list", "title": "待解决问题", "data_source": "compliance_issues"}
                ],
                schedule="0 9 1 * *"  # Monthly on 1st at 9 AM
            )
        ]
        
        for template in templates:
            self.templates[template.template_id] = template

    def register_template(self, template: ReportTemplate):
        """Register a report template."""
        self.templates[template.template_id] = template

    async def generate_report(
        self,
        report_type: ReportType,
        title: str,
        format: ReportFormat = ReportFormat.JSON,
        project_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        filters: Optional[Dict[str, Any]] = None,
        generated_by: Optional[str] = None
    ) -> QualityReport:
        """
        Generate a quality report.
        
        Args:
            report_type: Type of report
            title: Report title
            format: Output format
            project_id: Project filter
            period_start: Period start date
            period_end: Period end date
            filters: Additional filters
            generated_by: User generating the report
            
        Returns:
            Generated QualityReport
        """
        report = QualityReport(
            report_id=str(uuid.uuid4()),
            report_type=report_type,
            title=title,
            format=format,
            project_id=project_id,
            period_start=period_start or datetime.now() - timedelta(days=7),
            period_end=period_end or datetime.now(),
            filters=filters or {},
            generated_by=generated_by
        )
        
        report.status = ReportStatus.GENERATING
        self.reports[report.report_id] = report
        
        try:
            # Collect data based on report type
            await self._populate_report(report)
            
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now()
            
            logger.info(f"Generated report {report.report_id}: {title}")
            
        except Exception as e:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            logger.error(f"Report generation failed: {e}")
        
        return report

    async def _populate_report(self, report: QualityReport):
        """Populate report with data."""
        if report.report_type == ReportType.QUALITY_METRICS:
            await self._populate_quality_metrics_report(report)
        elif report.report_type == ReportType.ANOMALY_REPORT:
            await self._populate_anomaly_report(report)
        elif report.report_type == ReportType.ANNOTATOR_PERFORMANCE:
            await self._populate_annotator_report(report)
        elif report.report_type == ReportType.PROJECT_STATUS:
            await self._populate_project_report(report)
        elif report.report_type == ReportType.COMPLIANCE_REPORT:
            await self._populate_compliance_report(report)
        elif report.report_type in [ReportType.DAILY_SUMMARY, ReportType.WEEKLY_SUMMARY, ReportType.MONTHLY_SUMMARY]:
            await self._populate_summary_report(report)
        else:
            await self._populate_summary_report(report)

    async def _populate_quality_metrics_report(self, report: QualityReport):
        """Populate quality metrics report."""
        metrics = await self.data_collector.collect_quality_metrics(
            report.project_id, report.period_start, report.period_end
        )
        
        report.summary = {
            "整体准确率": metrics["overall_accuracy"],
            "一致性率": metrics["agreement_rate"],
            "完成率": metrics["completion_rate"]
        }
        
        report.sections.append(ReportSection(
            section_id="metrics",
            title="质量指标详情",
            content_type="metrics",
            content=metrics,
            order=1
        ))

    async def _populate_anomaly_report(self, report: QualityReport):
        """Populate anomaly report."""
        anomaly_data = await self.data_collector.collect_anomaly_data(
            report.project_id, report.period_start, report.period_end
        )
        
        report.summary = {
            "总异常数": anomaly_data["total_anomalies"],
            "已解决": anomaly_data["resolved_anomalies"],
            "解决率": anomaly_data["resolution_rate"]
        }
        
        report.sections.append(ReportSection(
            section_id="overview",
            title="异常概览",
            content_type="metrics",
            content={
                "总异常数": anomaly_data["total_anomalies"],
                "已解决": anomaly_data["resolved_anomalies"],
                "待处理": anomaly_data["pending_anomalies"],
                "平均解决时间(小时)": anomaly_data["avg_resolution_time_hours"]
            },
            order=1
        ))
        
        report.sections.append(ReportSection(
            section_id="by_type",
            title="按类型分布",
            content_type="table",
            content={
                "headers": ["类型", "数量"],
                "rows": [[k, v] for k, v in anomaly_data["by_type"].items()]
            },
            order=2
        ))
        
        report.sections.append(ReportSection(
            section_id="by_severity",
            title="按严重程度分布",
            content_type="table",
            content={
                "headers": ["严重程度", "数量"],
                "rows": [[k, v] for k, v in anomaly_data["by_severity"].items()]
            },
            order=3
        ))

    async def _populate_annotator_report(self, report: QualityReport):
        """Populate annotator performance report."""
        perf_data = await self.data_collector.collect_annotator_performance(
            report.project_id, report.period_start, report.period_end
        )
        
        report.summary = {
            "活跃标注员": perf_data["active_annotators"],
            "平均准确率": perf_data["avg_accuracy"],
            "日均任务量": perf_data["avg_tasks_per_day"]
        }
        
        report.sections.append(ReportSection(
            section_id="top_performers",
            title="优秀标注员",
            content_type="table",
            content={
                "headers": ["姓名", "准确率", "完成任务数"],
                "rows": [
                    [p["name"], f"{p['accuracy']:.2%}", p["tasks"]]
                    for p in perf_data["top_performers"]
                ]
            },
            order=1
        ))

    async def _populate_project_report(self, report: QualityReport):
        """Populate project status report."""
        if not report.project_id:
            return
        
        status_data = await self.data_collector.collect_project_status(report.project_id)
        
        report.summary = {
            "完成率": status_data["completion_rate"],
            "质量评分": status_data["quality_score"],
            "预计完成": status_data["estimated_completion"]
        }
        
        report.sections.append(ReportSection(
            section_id="progress",
            title="项目进度",
            content_type="metrics",
            content={
                "总任务数": status_data["total_tasks"],
                "已完成": status_data["completed_tasks"],
                "进行中": status_data["in_progress_tasks"],
                "待处理": status_data["pending_tasks"]
            },
            order=1
        ))

    async def _populate_compliance_report(self, report: QualityReport):
        """Populate compliance report."""
        compliance_data = await self.data_collector.collect_compliance_data(
            report.project_id, report.period_start, report.period_end
        )
        
        report.summary = {
            "合规评分": compliance_data["compliance_score"],
            "通过检查": compliance_data["checks_passed"],
            "失败检查": compliance_data["checks_failed"]
        }
        
        report.sections.append(ReportSection(
            section_id="overview",
            title="合规概览",
            content_type="metrics",
            content={
                "合规评分": compliance_data["compliance_score"],
                "通过": compliance_data["checks_passed"],
                "失败": compliance_data["checks_failed"],
                "警告": compliance_data["checks_warning"]
            },
            order=1
        ))
        
        if compliance_data["issues"]:
            report.sections.append(ReportSection(
                section_id="issues",
                title="待解决问题",
                content_type="table",
                content={
                    "headers": ["ID", "类别", "严重程度", "描述"],
                    "rows": [
                        [i["id"], i["category"], i["severity"], i["description"]]
                        for i in compliance_data["issues"]
                    ]
                },
                order=2
            ))

    async def _populate_summary_report(self, report: QualityReport):
        """Populate summary report."""
        metrics = await self.data_collector.collect_quality_metrics(
            report.project_id, report.period_start, report.period_end
        )
        anomalies = await self.data_collector.collect_anomaly_data(
            report.project_id, report.period_start, report.period_end
        )
        
        report.summary = {
            "准确率": metrics["overall_accuracy"],
            "完成率": metrics["completion_rate"],
            "异常数": anomalies["total_anomalies"],
            "解决率": anomalies["resolution_rate"]
        }
        
        report.sections.append(ReportSection(
            section_id="quality",
            title="质量指标",
            content_type="metrics",
            content=metrics,
            order=1
        ))
        
        report.sections.append(ReportSection(
            section_id="anomalies",
            title="异常情况",
            content_type="metrics",
            content={
                "总异常": anomalies["total_anomalies"],
                "已解决": anomalies["resolved_anomalies"],
                "待处理": anomalies["pending_anomalies"]
            },
            order=2
        ))

    def export_report(
        self,
        report_id: str,
        format: Optional[ReportFormat] = None
    ) -> Optional[str]:
        """Export report in specified format."""
        report = self.reports.get(report_id)
        if not report or report.status != ReportStatus.COMPLETED:
            return None
        
        export_format = format or report.format
        
        if export_format == ReportFormat.JSON:
            return self.formatter.format_json(report)
        elif export_format == ReportFormat.MARKDOWN:
            return self.formatter.format_markdown(report)
        elif export_format == ReportFormat.HTML:
            return self.formatter.format_html(report)
        elif export_format == ReportFormat.CSV:
            return self.formatter.format_csv(report)
        else:
            return self.formatter.format_json(report)

    def get_report(self, report_id: str) -> Optional[QualityReport]:
        """Get a report by ID."""
        return self.reports.get(report_id)

    def list_reports(
        self,
        report_type: Optional[ReportType] = None,
        project_id: Optional[str] = None,
        status: Optional[ReportStatus] = None,
        limit: int = 50
    ) -> List[QualityReport]:
        """List reports with filters."""
        reports = list(self.reports.values())
        
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        if project_id:
            reports = [r for r in reports if r.project_id == project_id]
        if status:
            reports = [r for r in reports if r.status == status]
        
        return sorted(reports, key=lambda r: r.created_at, reverse=True)[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get report generation statistics."""
        by_type = defaultdict(int)
        by_status = defaultdict(int)
        
        for report in self.reports.values():
            by_type[report.report_type.value] += 1
            by_status[report.status.value] += 1
        
        return {
            "total_reports": len(self.reports),
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "templates_count": len(self.templates),
            "generated_at": datetime.now().isoformat()
        }


# Global instance
quality_report_generator = QualityReportGenerator()
