"""
Compliance Report Exporter for SuperInsight Platform.

Exports compliance reports to various formats including PDF, Excel, and JSON.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile

from src.compliance.report_generator import ComplianceReport, ComplianceMetric, ComplianceViolation

logger = logging.getLogger(__name__)


class ComplianceReportExporter:
    """
    企业级合规报告导出器
    
    支持多种格式的报告导出：
    - PDF: 专业格式的合规报告
    - Excel: 数据分析友好的格式
    - JSON: 机器可读的格式
    - HTML: 网页查看格式
    """
    
    def __init__(self, export_directory: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # 设置导出目录
        if export_directory:
            self.export_directory = Path(export_directory)
        else:
            self.export_directory = Path("exports/compliance_reports")
        
        # 确保导出目录存在
        self.export_directory.mkdir(parents=True, exist_ok=True)
        
        # 支持的导出格式
        self.supported_formats = ["pdf", "excel", "json", "html", "csv"]
    
    async def export_report(
        self,
        report: ComplianceReport,
        export_format: str,
        custom_filename: Optional[str] = None
    ) -> str:
        """
        导出合规报告到指定格式
        
        Args:
            report: 合规报告对象
            export_format: 导出格式 (pdf, excel, json, html)
            custom_filename: 自定义文件名
            
        Returns:
            str: 导出文件的路径
        """
        try:
            if export_format not in self.supported_formats:
                raise ValueError(f"Unsupported export format: {export_format}")
            
            # 生成文件名
            if custom_filename:
                filename = custom_filename
            else:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"compliance_report_{report.standard.value}_{timestamp}"
            
            # 根据格式导出
            if export_format == "json":
                file_path = await self._export_to_json(report, filename)
            elif export_format == "pdf":
                file_path = await self._export_to_pdf(report, filename)
            elif export_format == "excel":
                file_path = await self._export_to_excel(report, filename)
            elif export_format == "html":
                file_path = await self._export_to_html(report, filename)
            elif export_format == "csv":
                file_path = await self._export_to_csv(report, filename)
            else:
                raise ValueError(f"Export format {export_format} not implemented")
            
            self.logger.info(f"Successfully exported report {report.report_id} to {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to export report {report.report_id}: {e}")
            raise
    
    async def _export_to_json(self, report: ComplianceReport, filename: str) -> str:
        """导出为JSON格式"""
        
        file_path = self.export_directory / f"{filename}.json"
        
        # 转换报告为可序列化的字典
        report_dict = {
            "report_id": report.report_id,
            "tenant_id": report.tenant_id,
            "standard": report.standard.value,
            "report_type": report.report_type.value,
            "generation_time": report.generation_time.isoformat(),
            "reporting_period": {
                "start_date": report.reporting_period["start_date"].isoformat(),
                "end_date": report.reporting_period["end_date"].isoformat()
            },
            "overall_compliance_score": report.overall_compliance_score,
            "compliance_status": report.compliance_status.value,
            "executive_summary": report.executive_summary,
            "metrics": [self._metric_to_dict(m) for m in report.metrics],
            "violations": [self._violation_to_dict(v) for v in report.violations],
            "recommendations": report.recommendations,
            "statistics": {
                "audit": report.audit_statistics,
                "security": report.security_statistics,
                "data_protection": report.data_protection_statistics,
                "access_control": report.access_control_statistics
            },
            "metadata": {
                "generated_by": str(report.generated_by),
                "report_format": report.report_format,
                "export_time": datetime.utcnow().isoformat()
            }
        }
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        return str(file_path)
    
    async def _export_to_pdf(self, report: ComplianceReport, filename: str) -> str:
        """导出为PDF格式"""
        
        file_path = self.export_directory / f"{filename}.pdf"
        
        # 生成HTML内容
        html_content = self._generate_html_content(report)
        
        try:
            # 尝试使用weasyprint生成PDF
            import weasyprint
            
            # 创建临时HTML文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as temp_html:
                temp_html.write(html_content)
                temp_html_path = temp_html.name
            
            try:
                # 生成PDF
                weasyprint.HTML(filename=temp_html_path).write_pdf(str(file_path))
            finally:
                # 清理临时文件
                os.unlink(temp_html_path)
                
        except ImportError:
            # 如果weasyprint不可用，生成简单的文本PDF
            self.logger.warning("weasyprint not available, generating text-based PDF")
            await self._export_to_text_pdf(report, file_path)
        
        return str(file_path)
    
    async def _export_to_excel(self, report: ComplianceReport, filename: str) -> str:
        """导出为Excel格式"""
        
        file_path = self.export_directory / f"{filename}.xlsx"
        
        try:
            import pandas as pd
            
            # 创建Excel写入器
            with pd.ExcelWriter(str(file_path), engine='openpyxl') as writer:
                
                # 报告摘要工作表
                summary_data = {
                    "Metric": [
                        "Report ID", "Standard", "Generation Time", 
                        "Compliance Score", "Status", "Total Metrics",
                        "Compliant Metrics", "Total Violations", "Critical Violations"
                    ],
                    "Value": [
                        report.report_id,
                        report.standard.value.upper(),
                        report.generation_time.strftime("%Y-%m-%d %H:%M:%S"),
                        f"{report.overall_compliance_score}%",
                        report.compliance_status.value.title(),
                        len(report.metrics),
                        sum(1 for m in report.metrics if m.status.value == "compliant"),
                        len(report.violations),
                        sum(1 for v in report.violations if v.severity == "critical")
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name="Summary", index=False)
                
                # 合规指标工作表
                if report.metrics:
                    metrics_data = []
                    for metric in report.metrics:
                        metrics_data.append({
                            "Name": metric.name,
                            "Description": metric.description,
                            "Current Value": metric.current_value,
                            "Target Value": metric.target_value,
                            "Unit": metric.unit,
                            "Status": metric.status.value.title(),
                            "Gap": metric.target_value - metric.current_value
                        })
                    
                    metrics_df = pd.DataFrame(metrics_data)
                    metrics_df.to_excel(writer, sheet_name="Metrics", index=False)
                
                # 违规工作表
                if report.violations:
                    violations_data = []
                    for violation in report.violations:
                        violations_data.append({
                            "Violation ID": violation.violation_id,
                            "Severity": violation.severity.title(),
                            "Description": violation.description,
                            "Affected Resources": ", ".join(violation.affected_resources),
                            "Detection Time": violation.detection_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "Remediation Required": "Yes" if violation.remediation_required else "No"
                        })
                    
                    violations_df = pd.DataFrame(violations_data)
                    violations_df.to_excel(writer, sheet_name="Violations", index=False)
                
                # 统计数据工作表
                stats_data = []
                
                # 审计统计
                for key, value in report.audit_statistics.items():
                    stats_data.append({
                        "Category": "Audit",
                        "Metric": key.replace("_", " ").title(),
                        "Value": str(value)
                    })
                
                # 安全统计
                for key, value in report.security_statistics.items():
                    stats_data.append({
                        "Category": "Security",
                        "Metric": key.replace("_", " ").title(),
                        "Value": str(value)
                    })
                
                # 数据保护统计
                for key, value in report.data_protection_statistics.items():
                    stats_data.append({
                        "Category": "Data Protection",
                        "Metric": key.replace("_", " ").title(),
                        "Value": str(value)
                    })
                
                # 访问控制统计
                for key, value in report.access_control_statistics.items():
                    stats_data.append({
                        "Category": "Access Control",
                        "Metric": key.replace("_", " ").title(),
                        "Value": str(value)
                    })
                
                if stats_data:
                    stats_df = pd.DataFrame(stats_data)
                    stats_df.to_excel(writer, sheet_name="Statistics", index=False)
                
                # 建议工作表
                if report.recommendations:
                    recommendations_data = {
                        "Recommendation": report.recommendations,
                        "Priority": ["High"] * len(report.recommendations),  # 简化优先级
                        "Status": ["Pending"] * len(report.recommendations)
                    }
                    recommendations_df = pd.DataFrame(recommendations_data)
                    recommendations_df.to_excel(writer, sheet_name="Recommendations", index=False)
                
        except ImportError:
            # 如果pandas不可用，生成简单的CSV文件
            self.logger.warning("pandas not available, generating CSV instead of Excel")
            await self._export_to_csv(report, filename)
            file_path = self.export_directory / f"{filename}.csv"
        
        return str(file_path)
    
    async def _export_to_html(self, report: ComplianceReport, filename: str) -> str:
        """导出为HTML格式"""
        
        file_path = self.export_directory / f"{filename}.html"
        
        html_content = self._generate_html_content(report)
        
        # 写入HTML文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(file_path)
    
    async def _export_to_csv(self, report: ComplianceReport, filename: str) -> str:
        """导出为CSV格式（作为Excel的备选）"""
        
        file_path = self.export_directory / f"{filename}.csv"
        
        # 生成CSV内容
        csv_lines = []
        
        # 报告摘要
        csv_lines.append("Report Summary")
        csv_lines.append(f"Report ID,{report.report_id}")
        csv_lines.append(f"Standard,{report.standard.value.upper()}")
        csv_lines.append(f"Generation Time,{report.generation_time}")
        csv_lines.append(f"Compliance Score,{report.overall_compliance_score}%")
        csv_lines.append(f"Status,{report.compliance_status.value}")
        csv_lines.append("")
        
        # 合规指标
        if report.metrics:
            csv_lines.append("Compliance Metrics")
            csv_lines.append("Name,Description,Current Value,Target Value,Unit,Status")
            for metric in report.metrics:
                csv_lines.append(
                    f'"{metric.name}","{metric.description}",'
                    f'{metric.current_value},{metric.target_value},'
                    f'"{metric.unit}","{metric.status.value}"'
                )
            csv_lines.append("")
        
        # 违规
        if report.violations:
            csv_lines.append("Violations")
            csv_lines.append("Violation ID,Severity,Description,Detection Time")
            for violation in report.violations:
                csv_lines.append(
                    f'"{violation.violation_id}","{violation.severity}",'
                    f'"{violation.description}","{violation.detection_time}"'
                )
        
        # 写入CSV文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(csv_lines))
        
        return str(file_path)
    
    async def _export_to_text_pdf(self, report: ComplianceReport, file_path: Path):
        """生成简单的文本PDF（当weasyprint不可用时）"""
        
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            
            # 创建PDF文档
            doc = SimpleDocTemplate(str(file_path), pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # 标题
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1  # 居中
            )
            story.append(Paragraph(f"Compliance Report - {report.standard.value.upper()}", title_style))
            story.append(Spacer(1, 20))
            
            # 报告信息
            info_data = [
                ["Report ID:", report.report_id],
                ["Generation Time:", report.generation_time.strftime("%Y-%m-%d %H:%M:%S")],
                ["Compliance Score:", f"{report.overall_compliance_score}%"],
                ["Status:", report.compliance_status.value.title()],
                ["Total Metrics:", str(len(report.metrics))],
                ["Total Violations:", str(len(report.violations))]
            ]
            
            info_table = Table(info_data, colWidths=[2*inch, 3*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 20))
            
            # 执行摘要
            story.append(Paragraph("Executive Summary", styles['Heading2']))
            story.append(Paragraph(report.executive_summary, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # 合规指标
            if report.metrics:
                story.append(Paragraph("Compliance Metrics", styles['Heading2']))
                
                metrics_data = [["Metric", "Current", "Target", "Status"]]
                for metric in report.metrics:
                    metrics_data.append([
                        metric.name,
                        f"{metric.current_value} {metric.unit}",
                        f"{metric.target_value} {metric.unit}",
                        metric.status.value.title()
                    ])
                
                metrics_table = Table(metrics_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
                metrics_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(metrics_table)
                story.append(Spacer(1, 20))
            
            # 违规
            if report.violations:
                story.append(Paragraph("Violations", styles['Heading2']))
                
                for violation in report.violations:
                    story.append(Paragraph(f"<b>{violation.severity.upper()}:</b> {violation.description}", styles['Normal']))
                    story.append(Spacer(1, 10))
            
            # 建议
            if report.recommendations:
                story.append(Paragraph("Recommendations", styles['Heading2']))
                
                for i, recommendation in enumerate(report.recommendations, 1):
                    story.append(Paragraph(f"{i}. {recommendation}", styles['Normal']))
                    story.append(Spacer(1, 5))
            
            # 生成PDF
            doc.build(story)
            
        except ImportError:
            # 如果reportlab也不可用，生成纯文本文件
            self.logger.warning("reportlab not available, generating text file instead of PDF")
            text_content = self._generate_text_content(report)
            text_path = file_path.with_suffix('.txt')
            
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
    
    def _generate_html_content(self, report: ComplianceReport) -> str:
        """生成HTML内容"""
        
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compliance Report - {standard}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #333;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #333;
            margin: 0;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .summary-card .value {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        .metrics-table, .violations-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .metrics-table th, .metrics-table td,
        .violations-table th, .violations-table td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        .metrics-table th, .violations-table th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        .status-compliant {{
            color: #28a745;
            font-weight: bold;
        }}
        .status-non-compliant {{
            color: #dc3545;
            font-weight: bold;
        }}
        .status-partially-compliant {{
            color: #ffc107;
            font-weight: bold;
        }}
        .severity-critical {{
            color: #dc3545;
            font-weight: bold;
        }}
        .severity-high {{
            color: #fd7e14;
            font-weight: bold;
        }}
        .severity-medium {{
            color: #ffc107;
            font-weight: bold;
        }}
        .severity-low {{
            color: #28a745;
            font-weight: bold;
        }}
        .recommendations {{
            background-color: #e7f3ff;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        .recommendations ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .recommendations li {{
            margin-bottom: 10px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Compliance Report</h1>
            <p><strong>{standard}</strong> | Generated: {generation_time}</p>
        </div>
        
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Compliance Score</h3>
                <div class="value">{compliance_score}%</div>
            </div>
            <div class="summary-card">
                <h3>Status</h3>
                <div class="value status-{status_class}">{status}</div>
            </div>
            <div class="summary-card">
                <h3>Total Metrics</h3>
                <div class="value">{total_metrics}</div>
            </div>
            <div class="summary-card">
                <h3>Violations</h3>
                <div class="value">{total_violations}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Executive Summary</h2>
            <p>{executive_summary}</p>
        </div>
        
        {metrics_section}
        
        {violations_section}
        
        {recommendations_section}
        
        <div class="footer">
            <p>Report ID: {report_id} | Tenant: {tenant_id}</p>
            <p>Generated by SuperInsight Compliance System</p>
        </div>
    </div>
</body>
</html>
        """
        
        # 生成指标表格
        metrics_html = ""
        if report.metrics:
            metrics_rows = ""
            for metric in report.metrics:
                status_class = metric.status.value.replace("_", "-")
                metrics_rows += f"""
                <tr>
                    <td>{metric.name}</td>
                    <td>{metric.description}</td>
                    <td>{metric.current_value} {metric.unit}</td>
                    <td>{metric.target_value} {metric.unit}</td>
                    <td class="status-{status_class}">{metric.status.value.replace("_", " ").title()}</td>
                </tr>
                """
            
            metrics_html = f"""
            <div class="section">
                <h2>Compliance Metrics</h2>
                <table class="metrics-table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Description</th>
                            <th>Current Value</th>
                            <th>Target Value</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {metrics_rows}
                    </tbody>
                </table>
            </div>
            """
        
        # 生成违规表格
        violations_html = ""
        if report.violations:
            violations_rows = ""
            for violation in report.violations:
                violations_rows += f"""
                <tr>
                    <td class="severity-{violation.severity}">{violation.severity.upper()}</td>
                    <td>{violation.description}</td>
                    <td>{", ".join(violation.affected_resources)}</td>
                    <td>{violation.detection_time.strftime("%Y-%m-%d %H:%M:%S")}</td>
                </tr>
                """
            
            violations_html = f"""
            <div class="section">
                <h2>Violations</h2>
                <table class="violations-table">
                    <thead>
                        <tr>
                            <th>Severity</th>
                            <th>Description</th>
                            <th>Affected Resources</th>
                            <th>Detection Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {violations_rows}
                    </tbody>
                </table>
            </div>
            """
        
        # 生成建议部分
        recommendations_html = ""
        if report.recommendations:
            recommendations_list = ""
            for recommendation in report.recommendations:
                recommendations_list += f"<li>{recommendation}</li>"
            
            recommendations_html = f"""
            <div class="section">
                <h2>Recommendations</h2>
                <div class="recommendations">
                    <ul>
                        {recommendations_list}
                    </ul>
                </div>
            </div>
            """
        
        # 填充模板
        return html_template.format(
            standard=report.standard.value.upper(),
            generation_time=report.generation_time.strftime("%Y-%m-%d %H:%M:%S"),
            compliance_score=report.overall_compliance_score,
            status=report.compliance_status.value.replace("_", " ").title(),
            status_class=report.compliance_status.value.replace("_", "-"),
            total_metrics=len(report.metrics),
            total_violations=len(report.violations),
            executive_summary=report.executive_summary.replace("\n", "<br>"),
            metrics_section=metrics_html,
            violations_section=violations_html,
            recommendations_section=recommendations_html,
            report_id=report.report_id,
            tenant_id=report.tenant_id
        )
    
    def _generate_text_content(self, report: ComplianceReport) -> str:
        """生成纯文本内容"""
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"COMPLIANCE REPORT - {report.standard.value.upper()}")
        lines.append("=" * 60)
        lines.append("")
        
        lines.append(f"Report ID: {report.report_id}")
        lines.append(f"Generation Time: {report.generation_time}")
        lines.append(f"Compliance Score: {report.overall_compliance_score}%")
        lines.append(f"Status: {report.compliance_status.value.title()}")
        lines.append("")
        
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 20)
        lines.append(report.executive_summary)
        lines.append("")
        
        if report.metrics:
            lines.append("COMPLIANCE METRICS")
            lines.append("-" * 20)
            for metric in report.metrics:
                lines.append(f"• {metric.name}: {metric.current_value}/{metric.target_value} {metric.unit} ({metric.status.value})")
            lines.append("")
        
        if report.violations:
            lines.append("VIOLATIONS")
            lines.append("-" * 20)
            for violation in report.violations:
                lines.append(f"• [{violation.severity.upper()}] {violation.description}")
            lines.append("")
        
        if report.recommendations:
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 20)
            for i, recommendation in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {recommendation}")
            lines.append("")
        
        lines.append("=" * 60)
        lines.append(f"Generated by SuperInsight Compliance System")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _metric_to_dict(self, metric: ComplianceMetric) -> Dict[str, Any]:
        """将ComplianceMetric转换为字典"""
        return {
            "name": metric.name,
            "description": metric.description,
            "current_value": metric.current_value,
            "target_value": metric.target_value,
            "unit": metric.unit,
            "status": metric.status.value,
            "details": metric.details
        }
    
    def _violation_to_dict(self, violation: ComplianceViolation) -> Dict[str, Any]:
        """将ComplianceViolation转换为字典"""
        return {
            "violation_id": violation.violation_id,
            "standard": violation.standard.value,
            "severity": violation.severity,
            "description": violation.description,
            "affected_resources": violation.affected_resources,
            "detection_time": violation.detection_time.isoformat(),
            "remediation_required": violation.remediation_required,
            "remediation_steps": violation.remediation_steps
        }
    
    def get_export_statistics(self) -> Dict[str, Any]:
        """获取导出统计信息"""
        
        try:
            # 统计导出目录中的文件
            files = list(self.export_directory.glob("*"))
            
            stats = {
                "total_files": len(files),
                "formats": {},
                "total_size_mb": 0,
                "oldest_file": None,
                "newest_file": None
            }
            
            if files:
                # 按格式统计
                for file in files:
                    ext = file.suffix.lower()
                    if ext in stats["formats"]:
                        stats["formats"][ext] += 1
                    else:
                        stats["formats"][ext] = 1
                    
                    # 计算总大小
                    stats["total_size_mb"] += file.stat().st_size / (1024 * 1024)
                
                # 找到最新和最旧的文件
                files_with_time = [(f, f.stat().st_mtime) for f in files]
                files_with_time.sort(key=lambda x: x[1])
                
                stats["oldest_file"] = {
                    "name": files_with_time[0][0].name,
                    "modified": datetime.fromtimestamp(files_with_time[0][1]).isoformat()
                }
                stats["newest_file"] = {
                    "name": files_with_time[-1][0].name,
                    "modified": datetime.fromtimestamp(files_with_time[-1][1]).isoformat()
                }
                
                stats["total_size_mb"] = round(stats["total_size_mb"], 2)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get export statistics: {e}")
            return {"error": str(e)}
    
    def cleanup_old_exports(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """清理旧的导出文件"""
        
        try:
            cutoff_time = datetime.utcnow().timestamp() - (days_to_keep * 24 * 3600)
            
            deleted_files = []
            total_size_freed = 0
            
            for file in self.export_directory.glob("*"):
                if file.is_file() and file.stat().st_mtime < cutoff_time:
                    size = file.stat().st_size
                    deleted_files.append(file.name)
                    total_size_freed += size
                    file.unlink()
            
            return {
                "deleted_files": len(deleted_files),
                "files": deleted_files,
                "size_freed_mb": round(total_size_freed / (1024 * 1024), 2),
                "cutoff_days": days_to_keep
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old exports: {e}")
            return {"error": str(e)}