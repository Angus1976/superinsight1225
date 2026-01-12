"""
Comprehensive test suite for compliance report generation.

Tests the compliance report generator, API endpoints, and export functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.compliance.report_generator import (
    ComplianceReportGenerator,
    ComplianceStandard,
    ReportType,
    ComplianceStatus,
    ComplianceMetric,
    ComplianceViolation,
    ComplianceReport
)
from src.compliance.report_exporter import ComplianceReportExporter
from src.security.models import AuditAction, UserModel


class TestComplianceReportGenerator:
    """测试合规报告生成器"""
    
    @pytest.fixture
    def generator(self):
        """创建报告生成器实例"""
        return ComplianceReportGenerator()
    
    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        mock_db = Mock()
        mock_db.execute.return_value.scalar.return_value = 100
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        return mock_db
    
    @pytest.fixture
    def sample_report_data(self):
        """示例报告数据"""
        return {
            "tenant_id": "test-tenant-123",
            "standard": ComplianceStandard.GDPR,
            "report_type": ReportType.COMPREHENSIVE,
            "start_date": datetime.utcnow() - timedelta(days=30),
            "end_date": datetime.utcnow(),
            "generated_by": uuid4()
        }
    
    def test_generator_initialization(self, generator):
        """测试生成器初始化"""
        assert generator is not None
        assert hasattr(generator, 'compliance_standards')
        assert hasattr(generator, 'report_templates')
        assert hasattr(generator, 'compliance_thresholds')
        
        # 验证支持的合规标准
        assert ComplianceStandard.GDPR in generator.compliance_standards
        assert ComplianceStandard.SOX in generator.compliance_standards
        assert ComplianceStandard.ISO_27001 in generator.compliance_standards
    
    def test_generate_gdpr_report(self, generator, mock_db_session, sample_report_data):
        """测试生成GDPR合规报告"""
        sample_report_data["standard"] = ComplianceStandard.GDPR
        
        report = generator.generate_compliance_report(
            db=mock_db_session,
            **sample_report_data
        )
        
        assert report is not None
        assert isinstance(report, ComplianceReport)
        assert report.standard == ComplianceStandard.GDPR
        assert report.tenant_id == sample_report_data["tenant_id"]
        assert report.overall_compliance_score >= 0
        assert report.overall_compliance_score <= 100
        assert isinstance(report.metrics, list)
        assert isinstance(report.violations, list)
        assert isinstance(report.recommendations, list)
    
    def test_generate_sox_report(self, generator, mock_db_session, sample_report_data):
        """测试生成SOX合规报告"""
        sample_report_data["standard"] = ComplianceStandard.SOX
        
        report = generator.generate_compliance_report(
            db=mock_db_session,
            **sample_report_data
        )
        
        assert report is not None
        assert report.standard == ComplianceStandard.SOX
        assert len(report.report_id) > 0
        assert report.compliance_status in [
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.NON_COMPLIANT,
            ComplianceStatus.PARTIALLY_COMPLIANT
        ]
    
    def test_generate_iso27001_report(self, generator, mock_db_session, sample_report_data):
        """测试生成ISO 27001合规报告"""
        sample_report_data["standard"] = ComplianceStandard.ISO_27001
        
        report = generator.generate_compliance_report(
            db=mock_db_session,
            **sample_report_data
        )
        
        assert report is not None
        assert report.standard == ComplianceStandard.ISO_27001
        assert report.executive_summary is not None
        assert len(report.executive_summary) > 0
    
    def test_audit_statistics_collection(self, generator, mock_db_session):
        """测试审计统计数据收集"""
        tenant_id = "test-tenant"
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        stats = generator._collect_audit_statistics(
            tenant_id, start_date, end_date, mock_db_session
        )
        
        assert isinstance(stats, dict)
        assert "total_events" in stats
        assert "action_statistics" in stats
        assert "high_risk_events" in stats
        assert "failed_logins" in stats
        assert "active_users" in stats
        assert "audit_coverage" in stats
        
        # 验证数据类型
        assert isinstance(stats["total_events"], int)
        assert isinstance(stats["action_statistics"], dict)
        assert isinstance(stats["audit_coverage"], float)
    
    def test_security_statistics_collection(self, generator, mock_db_session):
        """测试安全统计数据收集"""
        tenant_id = "test-tenant"
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        stats = generator._collect_security_statistics(
            tenant_id, start_date, end_date, mock_db_session
        )
        
        assert isinstance(stats, dict)
        assert "security_events" in stats
        assert "threat_detections" in stats
        assert "unique_ip_addresses" in stats
        assert "security_incidents" in stats
        assert "response_times" in stats
    
    def test_compliance_metrics_generation(self, generator):
        """测试合规指标生成"""
        # 模拟统计数据
        audit_stats = {
            "total_events": 1000,
            "audit_coverage": 95.5,
            "high_risk_events": 5
        }
        security_stats = {
            "security_events": 10,
            "response_times": {"average_hours": 12.0}
        }
        data_protection_stats = {
            "encryption_coverage": 100.0,
            "desensitization_operations": {"total_operations": 50}
        }
        access_control_stats = {
            "access_control_effectiveness": 98.5,
            "permission_checks": 5000,
            "permission_violations": 2
        }
        
        # 测试GDPR指标
        metrics = generator._generate_gdpr_metrics(
            audit_stats, security_stats, data_protection_stats, access_control_stats
        )
        
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        
        for metric in metrics:
            assert isinstance(metric, ComplianceMetric)
            assert metric.name is not None
            assert metric.description is not None
            assert isinstance(metric.current_value, (int, float))
            assert isinstance(metric.target_value, (int, float))
            assert metric.unit is not None
            assert metric.status in [
                ComplianceStatus.COMPLIANT,
                ComplianceStatus.NON_COMPLIANT,
                ComplianceStatus.PARTIALLY_COMPLIANT
            ]
    
    def test_compliance_violations_detection(self, generator, mock_db_session):
        """测试合规违规检测"""
        tenant_id = "test-tenant"
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        violations = generator._detect_compliance_violations(
            ComplianceStandard.GDPR, tenant_id, start_date, end_date, mock_db_session
        )
        
        assert isinstance(violations, list)
        
        for violation in violations:
            assert isinstance(violation, ComplianceViolation)
            assert violation.violation_id is not None
            assert violation.standard == ComplianceStandard.GDPR
            assert violation.severity in ["low", "medium", "high", "critical"]
            assert violation.description is not None
            assert isinstance(violation.affected_resources, list)
            assert isinstance(violation.remediation_required, bool)
            assert isinstance(violation.remediation_steps, list)
    
    def test_overall_compliance_score_calculation(self, generator):
        """测试总体合规分数计算"""
        # 创建测试指标
        metrics = [
            ComplianceMetric(
                name="test_metric_1",
                description="Test metric 1",
                current_value=95.0,
                target_value=95.0,
                unit="percentage",
                status=ComplianceStatus.COMPLIANT,
                details={}
            ),
            ComplianceMetric(
                name="test_metric_2",
                description="Test metric 2",
                current_value=80.0,
                target_value=90.0,
                unit="percentage",
                status=ComplianceStatus.PARTIALLY_COMPLIANT,
                details={}
            )
        ]
        
        # 创建测试违规
        violations = [
            ComplianceViolation(
                violation_id="v1",
                standard=ComplianceStandard.GDPR,
                severity="medium",
                description="Test violation",
                affected_resources=["resource1"],
                detection_time=datetime.utcnow(),
                remediation_required=True,
                remediation_steps=["Fix it"]
            )
        ]
        
        score = generator._calculate_overall_compliance_score(metrics, violations)
        
        assert isinstance(score, float)
        assert 0 <= score <= 100
    
    def test_compliance_status_determination(self, generator):
        """测试合规状态确定"""
        # 测试高分数，无关键违规
        status = generator._determine_compliance_status(95.0, [])
        assert status == ComplianceStatus.COMPLIANT
        
        # 测试中等分数
        status = generator._determine_compliance_status(80.0, [])
        assert status == ComplianceStatus.PARTIALLY_COMPLIANT
        
        # 测试低分数
        status = generator._determine_compliance_status(60.0, [])
        assert status == ComplianceStatus.NON_COMPLIANT
        
        # 测试有关键违规
        critical_violation = ComplianceViolation(
            violation_id="cv1",
            standard=ComplianceStandard.GDPR,
            severity="critical",
            description="Critical violation",
            affected_resources=["resource1"],
            detection_time=datetime.utcnow(),
            remediation_required=True,
            remediation_steps=["Immediate fix required"]
        )
        
        status = generator._determine_compliance_status(95.0, [critical_violation])
        assert status == ComplianceStatus.NON_COMPLIANT
    
    def test_executive_summary_generation(self, generator):
        """测试执行摘要生成"""
        metrics = [
            ComplianceMetric(
                name="test_metric",
                description="Test",
                current_value=95.0,
                target_value=95.0,
                unit="%",
                status=ComplianceStatus.COMPLIANT,
                details={}
            )
        ]
        
        violations = []
        
        summary = generator._generate_executive_summary(
            ComplianceStandard.GDPR,
            95.0,
            ComplianceStatus.COMPLIANT,
            metrics,
            violations
        )
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "GDPR" in summary.upper()
        assert "95" in summary
        assert "COMPLIANT" in summary.upper()
    
    def test_recommendations_generation(self, generator):
        """测试建议生成"""
        metrics = [
            ComplianceMetric(
                name="low_metric",
                description="Low performing metric",
                current_value=70.0,
                target_value=95.0,
                unit="%",
                status=ComplianceStatus.NON_COMPLIANT,
                details={}
            )
        ]
        
        violations = [
            ComplianceViolation(
                violation_id="v1",
                standard=ComplianceStandard.GDPR,
                severity="high",
                description="Test violation",
                affected_resources=["resource1"],
                detection_time=datetime.utcnow(),
                remediation_required=True,
                remediation_steps=["Implement fix", "Monitor progress"]
            )
        ]
        
        recommendations = generator._generate_recommendations(
            ComplianceStandard.GDPR, metrics, violations
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # 应该包含来自违规的建议
        assert "Implement fix" in recommendations
        assert "Monitor progress" in recommendations
    
    def test_error_handling(self, generator):
        """测试错误处理"""
        # 测试无效的数据库会话
        with pytest.raises(Exception):
            generator.generate_compliance_report(
                tenant_id="test",
                standard=ComplianceStandard.GDPR,
                report_type=ReportType.COMPREHENSIVE,
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                generated_by=uuid4(),
                db=None  # 无效的数据库会话
            )


class TestComplianceReportExporter:
    """测试合规报告导出器"""
    
    @pytest.fixture
    def exporter(self):
        """创建报告导出器实例"""
        return ComplianceReportExporter()
    
    @pytest.fixture
    def sample_report(self):
        """创建示例报告"""
        return ComplianceReport(
            report_id="test-report-123",
            tenant_id="test-tenant",
            standard=ComplianceStandard.GDPR,
            report_type=ReportType.COMPREHENSIVE,
            generation_time=datetime.utcnow(),
            reporting_period={
                "start_date": datetime.utcnow() - timedelta(days=30),
                "end_date": datetime.utcnow()
            },
            overall_compliance_score=92.5,
            compliance_status=ComplianceStatus.COMPLIANT,
            executive_summary="Test executive summary",
            metrics=[
                ComplianceMetric(
                    name="test_metric",
                    description="Test metric",
                    current_value=95.0,
                    target_value=95.0,
                    unit="%",
                    status=ComplianceStatus.COMPLIANT,
                    details={}
                )
            ],
            violations=[],
            recommendations=["Improve monitoring", "Update policies"],
            audit_statistics={"total_events": 1000},
            security_statistics={"security_events": 10},
            data_protection_statistics={"encryption_coverage": 100.0},
            access_control_statistics={"effectiveness": 98.0},
            generated_by=uuid4(),
            report_format="json"
        )
    
    def test_exporter_initialization(self, exporter):
        """测试导出器初始化"""
        assert exporter is not None
        assert hasattr(exporter, 'export_directory')
        assert hasattr(exporter, 'supported_formats')
        assert "json" in exporter.supported_formats
        assert "pdf" in exporter.supported_formats
        assert "excel" in exporter.supported_formats
        assert "html" in exporter.supported_formats
    
    @pytest.mark.asyncio
    async def test_json_export(self, exporter, sample_report):
        """测试JSON格式导出"""
        file_path = await exporter._export_to_json(sample_report, "test_report")
        
        assert file_path is not None
        assert file_path.endswith(".json")
        
        # 验证文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["report_id"] == sample_report.report_id
        assert data["standard"] == sample_report.standard.value
        assert data["overall_compliance_score"] == sample_report.overall_compliance_score
        assert "metrics" in data
        assert "violations" in data
        assert "recommendations" in data
        
        # 清理测试文件
        import os
        os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_html_export(self, exporter, sample_report):
        """测试HTML格式导出"""
        file_path = await exporter._export_to_html(sample_report, "test_report")
        
        assert file_path is not None
        assert file_path.endswith(".html")
        
        # 验证文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "<!DOCTYPE html>" in content
        assert sample_report.report_id in content
        assert sample_report.standard.value.upper() in content
        assert str(sample_report.overall_compliance_score) in content
        
        # 清理测试文件
        import os
        os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_csv_export(self, exporter, sample_report):
        """测试CSV格式导出"""
        file_path = await exporter._export_to_csv(sample_report, "test_report")
        
        assert file_path is not None
        assert file_path.endswith(".csv")
        
        # 验证文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "Report Summary" in content
        assert sample_report.report_id in content
        assert sample_report.standard.value.upper() in content
        
        # 清理测试文件
        import os
        os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_export_with_custom_filename(self, exporter, sample_report):
        """测试自定义文件名导出"""
        custom_name = "custom_compliance_report"
        
        file_path = await exporter.export_report(
            sample_report, "json", custom_name
        )
        
        assert custom_name in file_path
        
        # 清理测试文件
        import os
        os.unlink(file_path)
    
    @pytest.mark.asyncio
    async def test_unsupported_format_error(self, exporter, sample_report):
        """测试不支持的格式错误"""
        with pytest.raises(ValueError, match="Unsupported export format"):
            await exporter.export_report(sample_report, "unsupported_format")
    
    def test_metric_to_dict_conversion(self, exporter):
        """测试指标转字典转换"""
        metric = ComplianceMetric(
            name="test_metric",
            description="Test metric",
            current_value=95.0,
            target_value=100.0,
            unit="%",
            status=ComplianceStatus.COMPLIANT,
            details={"extra": "info"}
        )
        
        metric_dict = exporter._metric_to_dict(metric)
        
        assert isinstance(metric_dict, dict)
        assert metric_dict["name"] == "test_metric"
        assert metric_dict["current_value"] == 95.0
        assert metric_dict["target_value"] == 100.0
        assert metric_dict["status"] == "compliant"
        assert metric_dict["details"]["extra"] == "info"
    
    def test_violation_to_dict_conversion(self, exporter):
        """测试违规转字典转换"""
        violation = ComplianceViolation(
            violation_id="v123",
            standard=ComplianceStandard.GDPR,
            severity="high",
            description="Test violation",
            affected_resources=["resource1", "resource2"],
            detection_time=datetime.utcnow(),
            remediation_required=True,
            remediation_steps=["Step 1", "Step 2"]
        )
        
        violation_dict = exporter._violation_to_dict(violation)
        
        assert isinstance(violation_dict, dict)
        assert violation_dict["violation_id"] == "v123"
        assert violation_dict["standard"] == "gdpr"
        assert violation_dict["severity"] == "high"
        assert violation_dict["affected_resources"] == ["resource1", "resource2"]
        assert violation_dict["remediation_required"] is True
    
    def test_html_content_generation(self, exporter, sample_report):
        """测试HTML内容生成"""
        html_content = exporter._generate_html_content(sample_report)
        
        assert isinstance(html_content, str)
        assert "<!DOCTYPE html>" in html_content
        assert "<html" in html_content
        assert "</html>" in html_content
        assert sample_report.report_id in html_content
        assert sample_report.executive_summary in html_content
    
    def test_text_content_generation(self, exporter, sample_report):
        """测试文本内容生成"""
        text_content = exporter._generate_text_content(sample_report)
        
        assert isinstance(text_content, str)
        assert "COMPLIANCE REPORT" in text_content
        assert sample_report.report_id in text_content
        assert sample_report.standard.value.upper() in text_content
        assert str(sample_report.overall_compliance_score) in text_content
    
    def test_export_statistics(self, exporter):
        """测试导出统计"""
        stats = exporter.get_export_statistics()
        
        assert isinstance(stats, dict)
        assert "total_files" in stats
        assert "formats" in stats
        assert "total_size_mb" in stats
        
        # 验证数据类型
        assert isinstance(stats["total_files"], int)
        assert isinstance(stats["formats"], dict)
        assert isinstance(stats["total_size_mb"], (int, float))
    
    def test_cleanup_old_exports(self, exporter):
        """测试清理旧导出文件"""
        cleanup_result = exporter.cleanup_old_exports(days_to_keep=30)
        
        assert isinstance(cleanup_result, dict)
        assert "deleted_files" in cleanup_result
        assert "size_freed_mb" in cleanup_result
        assert "cutoff_days" in cleanup_result
        
        # 验证数据类型
        assert isinstance(cleanup_result["deleted_files"], int)
        assert isinstance(cleanup_result["size_freed_mb"], (int, float))
        assert cleanup_result["cutoff_days"] == 30


class TestComplianceReportIntegration:
    """测试合规报告集成功能"""
    
    @pytest.fixture
    def generator(self):
        return ComplianceReportGenerator()
    
    @pytest.fixture
    def exporter(self):
        return ComplianceReportExporter()
    
    @pytest.fixture
    def mock_db_session(self):
        mock_db = Mock()
        mock_db.execute.return_value.scalar.return_value = 100
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        return mock_db
    
    @pytest.mark.asyncio
    async def test_end_to_end_report_generation_and_export(
        self, generator, exporter, mock_db_session
    ):
        """测试端到端报告生成和导出"""
        # 生成报告
        report = generator.generate_compliance_report(
            tenant_id="test-tenant",
            standard=ComplianceStandard.GDPR,
            report_type=ReportType.COMPREHENSIVE,
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            generated_by=uuid4(),
            db=mock_db_session
        )
        
        assert report is not None
        
        # 导出为多种格式
        formats_to_test = ["json", "html"]
        
        for format_type in formats_to_test:
            file_path = await exporter.export_report(report, format_type)
            assert file_path is not None
            
            # 验证文件存在
            import os
            assert os.path.exists(file_path)
            
            # 清理测试文件
            os.unlink(file_path)
    
    def test_multiple_standards_comparison(self, generator, mock_db_session):
        """测试多个合规标准的比较"""
        standards_to_test = [
            ComplianceStandard.GDPR,
            ComplianceStandard.SOX,
            ComplianceStandard.ISO_27001
        ]
        
        reports = []
        
        for standard in standards_to_test:
            report = generator.generate_compliance_report(
                tenant_id="test-tenant",
                standard=standard,
                report_type=ReportType.COMPREHENSIVE,
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                generated_by=uuid4(),
                db=mock_db_session
            )
            reports.append(report)
        
        # 验证所有报告都生成成功
        assert len(reports) == len(standards_to_test)
        
        # 验证每个报告都有不同的标准
        report_standards = [r.standard for r in reports]
        assert len(set(report_standards)) == len(standards_to_test)
        
        # 验证所有报告都有合理的合规分数
        for report in reports:
            assert 0 <= report.overall_compliance_score <= 100
    
    def test_report_consistency_across_time_periods(self, generator, mock_db_session):
        """测试不同时间段报告的一致性"""
        base_date = datetime.utcnow()
        
        # 生成不同时间段的报告
        time_periods = [
            (base_date - timedelta(days=7), base_date),  # 最近7天
            (base_date - timedelta(days=30), base_date),  # 最近30天
            (base_date - timedelta(days=90), base_date)   # 最近90天
        ]
        
        reports = []
        
        for start_date, end_date in time_periods:
            report = generator.generate_compliance_report(
                tenant_id="test-tenant",
                standard=ComplianceStandard.GDPR,
                report_type=ReportType.COMPREHENSIVE,
                start_date=start_date,
                end_date=end_date,
                generated_by=uuid4(),
                db=mock_db_session
            )
            reports.append(report)
        
        # 验证所有报告都生成成功
        assert len(reports) == len(time_periods)
        
        # 验证报告结构一致性
        for report in reports:
            assert report.standard == ComplianceStandard.GDPR
            assert isinstance(report.metrics, list)
            assert isinstance(report.violations, list)
            assert isinstance(report.recommendations, list)
            assert report.executive_summary is not None


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])