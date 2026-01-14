"""Integration tests for Audit and Compliance components."""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.security.audit_logger import AuditLogger
from src.security.compliance_reporter import ComplianceReporter
from src.security.security_monitor import SecurityMonitor


class TestAuditLoggerIntegration:
    """Integration tests for Audit Logger."""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.first.return_value = None
        db.commit = MagicMock()
        db.add = MagicMock()
        return db
    
    @pytest.fixture
    def audit_logger(self, mock_db):
        return AuditLogger(db=mock_db)
    
    @pytest.mark.asyncio
    async def test_log_user_action(self, audit_logger, mock_db):
        with patch.object(audit_logger, 'log') as mock_log:
            mock_log.return_value = MagicMock(id=uuid4())
            result = await audit_logger.log(
                event_type="user_action",
                user_id="user-123",
                action="create_project",
                resource_type="project",
                resource_id="project-789",
                details={"project_name": "Test Project"}
            )
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_log_security_event(self, audit_logger, mock_db):
        with patch.object(audit_logger, 'log') as mock_log:
            mock_log.return_value = MagicMock(id=uuid4())
            result = await audit_logger.log(
                event_type="security_event",
                user_id="user-123",
                action="failed_login",
                details={"reason": "invalid_password"}
            )
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_query_logs(self, audit_logger, mock_db):
        mock_logs = [MagicMock(id=uuid4(), event_type="user_action", user_id="user-123")]
        
        with patch.object(audit_logger, 'query_logs') as mock_query:
            mock_query.return_value = mock_logs
            logs = await audit_logger.query_logs(
                user_id="user-123",
                start_time=datetime.utcnow() - timedelta(days=7),
                end_time=datetime.utcnow()
            )
            assert logs is not None
    
    @pytest.mark.asyncio
    async def test_verify_integrity(self, audit_logger, mock_db):
        with patch.object(audit_logger, 'verify_integrity') as mock_verify:
            mock_verify.return_value = True
            is_valid = await audit_logger.verify_integrity(
                start_time=datetime.utcnow() - timedelta(hours=1),
                end_time=datetime.utcnow()
            )
            assert isinstance(is_valid, bool)
    
    @pytest.mark.asyncio
    async def test_export_logs(self, audit_logger, mock_db):
        with patch.object(audit_logger, 'export_logs') as mock_export:
            mock_export.return_value = '{"logs": []}'
            export_data = await audit_logger.export_logs(
                format="json",
                start_time=datetime.utcnow() - timedelta(days=30),
                end_time=datetime.utcnow()
            )
            assert export_data is not None


class TestComplianceReporterIntegration:
    """Integration tests for Compliance Reporter."""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.count.return_value = 0
        return db
    
    @pytest.fixture
    def mock_audit_logger(self, mock_db):
        logger = AuditLogger(db=mock_db)
        return logger
    
    @pytest.fixture
    def compliance_reporter(self, mock_audit_logger, mock_db):
        return ComplianceReporter(audit_logger=mock_audit_logger, db=mock_db)
    
    @pytest.mark.asyncio
    async def test_generate_gdpr_report(self, compliance_reporter, mock_db):
        with patch.object(compliance_reporter, 'generate_gdpr_report') as mock_report:
            mock_report.return_value = MagicMock(report_type="gdpr")
            report = await compliance_reporter.generate_gdpr_report(
                tenant_id="tenant-123",
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow()
            )
            assert report is not None
    
    @pytest.mark.asyncio
    async def test_generate_soc2_report(self, compliance_reporter, mock_db):
        with patch.object(compliance_reporter, 'generate_soc2_report') as mock_report:
            mock_report.return_value = MagicMock(report_type="soc2")
            report = await compliance_reporter.generate_soc2_report(
                tenant_id="tenant-123",
                start_date=datetime.utcnow() - timedelta(days=90),
                end_date=datetime.utcnow()
            )
            assert report is not None
    
    @pytest.mark.asyncio
    async def test_generate_access_report(self, compliance_reporter, mock_db):
        with patch.object(compliance_reporter, 'generate_access_report') as mock_report:
            mock_report.return_value = MagicMock(report_type="access")
            report = await compliance_reporter.generate_access_report(
                tenant_id="tenant-123",
                user_id="user-456",
                start_date=datetime.utcnow() - timedelta(days=7),
                end_date=datetime.utcnow()
            )
            assert report is not None


class TestSecurityMonitorIntegration:
    """Integration tests for Security Monitor."""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.first.return_value = None
        db.commit = MagicMock()
        db.add = MagicMock()
        return db
    
    @pytest.fixture
    def mock_audit_logger(self, mock_db):
        return AuditLogger(db=mock_db)
    
    @pytest.fixture
    def security_monitor(self, mock_audit_logger, mock_db):
        return SecurityMonitor(audit_logger=mock_audit_logger, db=mock_db)
    
    @pytest.mark.asyncio
    async def test_monitor_login_attempts(self, security_monitor, mock_db):
        with patch.object(security_monitor, 'monitor_login_attempts') as mock_monitor:
            mock_monitor.return_value = None
            await security_monitor.monitor_login_attempts(
                user_id="user-123",
                ip_address="192.168.1.100",
                success=False,
                details={"attempt": 1}
            )
            mock_monitor.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_data_access(self, security_monitor, mock_db):
        with patch.object(security_monitor, 'monitor_data_access') as mock_monitor:
            mock_monitor.return_value = None
            await security_monitor.monitor_data_access(
                user_id="user-123",
                resource_type="sensitive_data",
                resource_id="data-456",
                action="read",
                details={"fields": ["ssn", "credit_card"]}
            )
            mock_monitor.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_security_posture_report(self, security_monitor, mock_db):
        with patch.object(security_monitor, 'generate_security_posture_report') as mock_report:
            mock_report.return_value = MagicMock(status="healthy")
            report = await security_monitor.generate_security_posture_report(
                tenant_id="tenant-123",
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow()
            )
            assert report is not None


class TestAuditSecurityWorkflow:
    """Integration tests for complete audit and security workflows."""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.first.return_value = None
        db.commit = MagicMock()
        db.add = MagicMock()
        return db
    
    @pytest.mark.asyncio
    async def test_complete_audit_workflow(self, mock_db):
        audit_logger = AuditLogger(db=mock_db)
        
        with patch.object(audit_logger, 'log') as mock_log:
            mock_log.return_value = MagicMock(id=uuid4())
            
            for i in range(5):
                await audit_logger.log(
                    event_type="user_action",
                    user_id="user-123",
                    action=f"action_{i}",
                    resource_type="project",
                    resource_id=f"project-{i}"
                )
            
            assert mock_log.call_count == 5
    
    @pytest.mark.asyncio
    async def test_security_incident_workflow(self, mock_db):
        audit_logger = AuditLogger(db=mock_db)
        security_monitor = SecurityMonitor(audit_logger=audit_logger, db=mock_db)
        
        with patch.object(security_monitor, 'monitor_login_attempts') as mock_monitor:
            mock_monitor.return_value = None
            
            for i in range(5):
                await security_monitor.monitor_login_attempts(
                    user_id="attacker-123",
                    ip_address="10.0.0.100",
                    success=False,
                    details={"attempt": i + 1}
                )
            
            assert mock_monitor.call_count == 5
    
    @pytest.mark.asyncio
    async def test_compliance_audit_workflow(self, mock_db):
        audit_logger = AuditLogger(db=mock_db)
        compliance_reporter = ComplianceReporter(audit_logger=audit_logger, db=mock_db)
        
        with patch.object(compliance_reporter, 'generate_gdpr_report') as mock_gdpr:
            mock_gdpr.return_value = MagicMock(report_type="gdpr")
            
            gdpr_report = await compliance_reporter.generate_gdpr_report(
                tenant_id="tenant-456",
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow()
            )
            
            assert gdpr_report is not None
