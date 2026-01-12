"""
Tests for Security Dashboard functionality.

Tests the security dashboard service, API endpoints, and real-time updates.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import WebSocket

from src.security.security_dashboard_service import (
    SecurityDashboardService,
    DashboardTimeRange,
    SecurityMetrics,
    ComplianceMetrics,
    DashboardData
)
from src.security.security_event_monitor import SecurityEvent, SecurityEventType, ThreatLevel
from src.security.models import UserModel, AuditLogModel, AuditAction
from src.security.audit_service import RiskLevel
from src.app import app


class TestSecurityDashboardService:
    """Test SecurityDashboardService functionality."""
    
    @pytest.fixture
    def dashboard_service(self):
        """Create dashboard service instance."""
        return SecurityDashboardService()
    
    @pytest.fixture
    def mock_tenant_id(self):
        """Mock tenant ID."""
        return "test-tenant-123"
    
    @pytest.fixture
    def mock_security_events(self):
        """Mock security events."""
        return [
            SecurityEvent(
                event_id="event-1",
                event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
                threat_level=ThreatLevel.HIGH,
                tenant_id="test-tenant-123",
                user_id=uuid4(),
                ip_address="192.168.1.100",
                timestamp=datetime.now() - timedelta(hours=1),
                description="Brute force attack detected",
                resolved=False
            ),
            SecurityEvent(
                event_id="event-2",
                event_type=SecurityEventType.PRIVILEGE_ESCALATION,
                threat_level=ThreatLevel.CRITICAL,
                tenant_id="test-tenant-123",
                user_id=uuid4(),
                ip_address="192.168.1.101",
                timestamp=datetime.now() - timedelta(hours=2),
                description="Privilege escalation attempt",
                resolved=True
            )
        ]
    
    def test_calculate_start_time(self, dashboard_service):
        """Test time range calculation."""
        end_time = datetime(2024, 1, 15, 12, 0, 0)
        
        # Test different time ranges
        start_1h = dashboard_service._calculate_start_time(end_time, DashboardTimeRange.LAST_HOUR)
        assert start_1h == datetime(2024, 1, 15, 11, 0, 0)
        
        start_24h = dashboard_service._calculate_start_time(end_time, DashboardTimeRange.LAST_24_HOURS)
        assert start_24h == datetime(2024, 1, 14, 12, 0, 0)
        
        start_7d = dashboard_service._calculate_start_time(end_time, DashboardTimeRange.LAST_7_DAYS)
        assert start_7d == datetime(2024, 1, 8, 12, 0, 0)
    
    def test_group_events_by_hour(self, dashboard_service, mock_security_events):
        """Test grouping events by hour."""
        start_time = datetime.now() - timedelta(hours=3)
        end_time = datetime.now()
        
        grouped = dashboard_service._group_events_by_hour(mock_security_events, start_time, end_time)
        
        assert len(grouped) == 4  # 3 hours + current hour
        assert all("hour" in item for item in grouped)
        assert all("total_events" in item for item in grouped)
        assert all("critical_events" in item for item in grouped)
    
    def test_severity_from_score(self, dashboard_service):
        """Test severity calculation from score."""
        assert dashboard_service._severity_from_score(5.0) == "critical"
        assert dashboard_service._severity_from_score(4.0) == "high"
        assert dashboard_service._severity_from_score(3.0) == "medium"
        assert dashboard_service._severity_from_score(2.0) == "low"
        assert dashboard_service._severity_from_score(1.0) == "info"
    
    @pytest.mark.asyncio
    async def test_get_recent_events(self, dashboard_service, mock_tenant_id):
        """Test getting recent events."""
        with patch('src.security.security_dashboard_service.security_event_monitor') as mock_monitor:
            mock_monitor.get_events_by_tenant.return_value = []
            
            recent_events = await dashboard_service._get_recent_events(mock_tenant_id, limit=10)
            
            assert isinstance(recent_events, list)
            mock_monitor.get_events_by_tenant.assert_called_once_with(mock_tenant_id)
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, dashboard_service, mock_tenant_id):
        """Test getting active alerts."""
        with patch('src.security.security_dashboard_service.security_event_monitor') as mock_monitor:
            mock_monitor.get_events_by_tenant.return_value = []
            
            active_alerts = await dashboard_service._get_active_alerts(mock_tenant_id)
            
            assert isinstance(active_alerts, list)
            mock_monitor.get_events_by_tenant.assert_called_once_with(mock_tenant_id)
    
    @pytest.mark.asyncio
    async def test_get_system_status(self, dashboard_service, mock_tenant_id):
        """Test getting system status."""
        with patch('src.security.security_dashboard_service.security_event_monitor') as mock_monitor:
            mock_monitor.is_monitoring_active.return_value = True
            
            with patch('src.security.security_dashboard_service.threat_detector') as mock_detector:
                mock_detector.is_active.return_value = True
                
                system_status = await dashboard_service._get_system_status(mock_tenant_id)
                
                assert isinstance(system_status, dict)
                assert "monitoring_active" in system_status
                assert "services_status" in system_status
                assert "performance_metrics" in system_status
    
    @pytest.mark.asyncio
    async def test_get_security_metrics(self, dashboard_service, mock_tenant_id, mock_security_events):
        """Test getting security metrics."""
        start_time = datetime.now() - timedelta(hours=24)
        end_time = datetime.now()
        
        with patch('src.security.security_dashboard_service.security_event_monitor') as mock_monitor:
            mock_monitor.get_events_by_tenant.return_value = mock_security_events
            mock_monitor.get_monitoring_status.return_value = "active"
            mock_monitor.get_last_scan_time.return_value = datetime.now()
            
            with patch.object(dashboard_service, '_get_top_threats', return_value=[]):
                with patch.object(dashboard_service, '_get_threat_trends', return_value=[]):
                    with patch.object(dashboard_service, '_get_user_activity_stats', return_value={
                        "active_users": 10,
                        "suspicious_users": [],
                        "failed_logins": 5
                    }):
                        
                        metrics = await dashboard_service._get_security_metrics(
                            mock_tenant_id, start_time, end_time
                        )
                        
                        assert isinstance(metrics, SecurityMetrics)
                        assert metrics.total_events >= 0
                        assert metrics.security_score >= 0
                        assert isinstance(metrics.events_by_type, dict)
                        assert isinstance(metrics.events_by_threat_level, dict)
    
    @pytest.mark.asyncio
    async def test_get_compliance_metrics(self, dashboard_service, mock_tenant_id):
        """Test getting compliance metrics."""
        start_time = datetime.now() - timedelta(hours=24)
        end_time = datetime.now()
        
        # Mock compliance report generator
        mock_report = Mock()
        mock_report.overall_compliance_score = 85.0
        mock_report.metrics = []
        mock_report.violations = []
        mock_report.audit_statistics = {"coverage_percentage": 90.0}
        mock_report.data_protection_statistics = {"protection_score": 88.0}
        mock_report.access_control_statistics = {"control_score": 92.0}
        
        with patch.object(dashboard_service.compliance_generator, 'generate_compliance_report', return_value=mock_report):
            with patch.object(dashboard_service, '_get_compliance_trends', return_value=[]):
                with patch.object(dashboard_service, '_get_violation_trends', return_value=[]):
                    
                    metrics = await dashboard_service._get_compliance_metrics(
                        mock_tenant_id, start_time, end_time
                    )
                    
                    assert isinstance(metrics, ComplianceMetrics)
                    assert metrics.overall_score >= 0
                    assert metrics.gdpr_score >= 0
                    assert metrics.sox_score >= 0
                    assert metrics.iso27001_score >= 0
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, dashboard_service, mock_tenant_id):
        """Test getting complete dashboard data."""
        with patch.object(dashboard_service, '_get_security_metrics') as mock_security:
            with patch.object(dashboard_service, '_get_compliance_metrics') as mock_compliance:
                with patch.object(dashboard_service, '_get_recent_events', return_value=[]):
                    with patch.object(dashboard_service, '_get_active_alerts', return_value=[]):
                        with patch.object(dashboard_service, '_get_system_status', return_value={}):
                            with patch.object(dashboard_service, '_get_security_trends', return_value=[]):
                                with patch.object(dashboard_service, '_get_threat_heatmap', return_value={}):
                                    with patch.object(dashboard_service, '_get_user_activity_map', return_value={}):
                                        
                                        # Mock return values
                                        mock_security.return_value = SecurityMetrics(
                                            total_events=10, critical_events=2, high_risk_events=3,
                                            resolved_events=5, active_threats=5, security_score=85.0,
                                            compliance_score=80.0, events_by_type={}, events_by_threat_level={},
                                            events_by_hour=[], top_threats=[], threat_trends=[],
                                            active_users=15, suspicious_users=[], failed_logins=3,
                                            monitoring_status="active", last_scan_time=datetime.now(),
                                            system_health="healthy"
                                        )
                                        
                                        mock_compliance.return_value = ComplianceMetrics(
                                            overall_score=85.0, gdpr_score=88.0, sox_score=82.0, iso27001_score=85.0,
                                            compliant_controls=45, total_controls=50, violations=5, critical_violations=1,
                                            audit_coverage=90.0, data_protection_score=88.0, access_control_score=92.0,
                                            compliance_trends=[], violation_trends=[]
                                        )
                                        
                                        dashboard_data = await dashboard_service.get_dashboard_data(
                                            mock_tenant_id, DashboardTimeRange.LAST_24_HOURS
                                        )
                                        
                                        assert isinstance(dashboard_data, DashboardData)
                                        assert dashboard_data.tenant_id == mock_tenant_id
                                        assert dashboard_data.time_range == DashboardTimeRange.LAST_24_HOURS
                                        assert isinstance(dashboard_data.security_metrics, SecurityMetrics)
                                        assert isinstance(dashboard_data.compliance_metrics, ComplianceMetrics)
    
    def test_get_dashboard_summary(self, dashboard_service, mock_tenant_id):
        """Test getting dashboard summary."""
        # Mock cached data
        mock_data = DashboardData(
            timestamp=datetime.now(),
            tenant_id=mock_tenant_id,
            time_range=DashboardTimeRange.LAST_24_HOURS,
            security_metrics=SecurityMetrics(
                total_events=10, critical_events=2, high_risk_events=3,
                resolved_events=5, active_threats=5, security_score=85.0,
                compliance_score=80.0, events_by_type={}, events_by_threat_level={},
                events_by_hour=[], top_threats=[], threat_trends=[],
                active_users=15, suspicious_users=[], failed_logins=3,
                monitoring_status="active", last_scan_time=datetime.now(),
                system_health="healthy"
            ),
            compliance_metrics=ComplianceMetrics(
                overall_score=85.0, gdpr_score=88.0, sox_score=82.0, iso27001_score=85.0,
                compliant_controls=45, total_controls=50, violations=5, critical_violations=1,
                audit_coverage=90.0, data_protection_score=88.0, access_control_score=92.0,
                compliance_trends=[], violation_trends=[]
            ),
            recent_events=[], active_alerts=[], system_status={},
            security_trends=[], threat_heatmap={}, user_activity_map={}
        )
        
        cache_key = f"{mock_tenant_id}:{DashboardTimeRange.LAST_24_HOURS.value}"
        dashboard_service.dashboard_cache[cache_key] = (mock_data, datetime.now())
        
        summary = dashboard_service.get_dashboard_summary(mock_tenant_id)
        
        assert isinstance(summary, dict)
        assert summary["tenant_id"] == mock_tenant_id
        assert "security_score" in summary
        assert "compliance_score" in summary
        assert "active_threats" in summary
    
    @pytest.mark.asyncio
    async def test_websocket_connection_management(self, dashboard_service, mock_tenant_id):
        """Test WebSocket connection management."""
        mock_websocket = Mock(spec=WebSocket)
        
        # Test adding connection
        await dashboard_service.add_websocket_connection(mock_tenant_id, mock_websocket)
        assert mock_tenant_id in dashboard_service.active_connections
        assert mock_websocket in dashboard_service.active_connections[mock_tenant_id]
        
        # Test removing connection
        await dashboard_service.remove_websocket_connection(mock_tenant_id, mock_websocket)
        assert mock_tenant_id not in dashboard_service.active_connections
    
    @pytest.mark.asyncio
    async def test_real_time_updates_lifecycle(self, dashboard_service):
        """Test real-time updates start/stop."""
        # Test starting updates
        await dashboard_service.start_real_time_updates()
        assert dashboard_service.is_running
        assert dashboard_service.update_task is not None
        
        # Test stopping updates
        await dashboard_service.stop_real_time_updates()
        assert not dashboard_service.is_running


class TestSecurityDashboardAPI:
    """Test Security Dashboard API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return UserModel(
            id=uuid4(),
            username="test_user",
            email="test@example.com",
            tenant_id="test-tenant-123",
            is_active=True
        )
    
    @pytest.fixture
    def auth_headers(self, mock_user):
        """Mock authentication headers."""
        return {"Authorization": "Bearer mock-token"}
    
    def test_get_dashboard_summary_unauthorized(self, client):
        """Test dashboard summary without authentication."""
        response = client.get("/api/security-dashboard/summary/test-tenant-123")
        assert response.status_code == 401
    
    @patch('src.api.security_dashboard_api.get_current_active_user')
    @patch('src.api.security_dashboard_api.require_role')
    @patch('src.api.security_dashboard_api.audit_action')
    @patch('src.api.security_dashboard_api.security_dashboard_service')
    def test_get_dashboard_summary_success(
        self, mock_service, mock_audit, mock_require_role, mock_get_user, client, mock_user, auth_headers
    ):
        """Test successful dashboard summary retrieval."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_require_role.return_value = True
        mock_audit.return_value = None
        mock_service.get_dashboard_summary.return_value = {
            "tenant_id": "test-tenant-123",
            "last_updated": datetime.now().isoformat(),
            "security_score": 85.0,
            "compliance_score": 80.0,
            "active_threats": 5,
            "critical_events": 2,
            "total_violations": 3,
            "monitoring_status": "active"
        }
        
        response = client.get(
            "/api/security-dashboard/summary/test-tenant-123",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant-123"
        assert "security_score" in data
        assert "compliance_score" in data
    
    @patch('src.api.security_dashboard_api.get_current_active_user')
    @patch('src.api.security_dashboard_api.require_role')
    def test_get_dashboard_summary_forbidden(
        self, mock_require_role, mock_get_user, client, mock_user, auth_headers
    ):
        """Test dashboard summary with insufficient permissions."""
        mock_get_user.return_value = mock_user
        mock_require_role.return_value = False
        
        response = client.get(
            "/api/security-dashboard/summary/test-tenant-123",
            headers=auth_headers
        )
        
        assert response.status_code == 403
    
    @patch('src.api.security_dashboard_api.get_current_active_user')
    @patch('src.api.security_dashboard_api.require_role')
    @patch('src.api.security_dashboard_api.audit_action')
    @patch('src.api.security_dashboard_api.security_dashboard_service')
    def test_get_dashboard_data_success(
        self, mock_service, mock_audit, mock_require_role, mock_get_user, client, mock_user, auth_headers
    ):
        """Test successful dashboard data retrieval."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_require_role.return_value = True
        mock_audit.return_value = None
        
        mock_dashboard_data = DashboardData(
            timestamp=datetime.now(),
            tenant_id="test-tenant-123",
            time_range=DashboardTimeRange.LAST_24_HOURS,
            security_metrics=SecurityMetrics(
                total_events=10, critical_events=2, high_risk_events=3,
                resolved_events=5, active_threats=5, security_score=85.0,
                compliance_score=80.0, events_by_type={}, events_by_threat_level={},
                events_by_hour=[], top_threats=[], threat_trends=[],
                active_users=15, suspicious_users=[], failed_logins=3,
                monitoring_status="active", last_scan_time=datetime.now(),
                system_health="healthy"
            ),
            compliance_metrics=ComplianceMetrics(
                overall_score=85.0, gdpr_score=88.0, sox_score=82.0, iso27001_score=85.0,
                compliant_controls=45, total_controls=50, violations=5, critical_violations=1,
                audit_coverage=90.0, data_protection_score=88.0, access_control_score=92.0,
                compliance_trends=[], violation_trends=[]
            ),
            recent_events=[], active_alerts=[], system_status={},
            security_trends=[], threat_heatmap={}, user_activity_map={}
        )
        
        mock_service.get_dashboard_data.return_value = mock_dashboard_data
        
        response = client.get(
            "/api/security-dashboard/data/test-tenant-123",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant-123"
        assert "security_metrics" in data
        assert "compliance_metrics" in data
    
    @patch('src.api.security_dashboard_api.get_current_active_user')
    @patch('src.api.security_dashboard_api.require_role')
    @patch('src.api.security_dashboard_api.audit_action')
    def test_refresh_dashboard_data_success(
        self, mock_audit, mock_require_role, mock_get_user, client, mock_user, auth_headers
    ):
        """Test successful dashboard data refresh."""
        mock_get_user.return_value = mock_user
        mock_require_role.return_value = True
        mock_audit.return_value = None
        
        with patch('src.api.security_dashboard_api.security_dashboard_service') as mock_service:
            mock_dashboard_data = Mock()
            mock_dashboard_data.timestamp = datetime.now()
            mock_service.get_dashboard_data.return_value = mock_dashboard_data
            
            response = client.post(
                "/api/security-dashboard/refresh/test-tenant-123",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "timestamp" in data
    
    def test_get_dashboard_service_status(self, client):
        """Test dashboard service status endpoint."""
        with patch('src.api.security_dashboard_api.security_dashboard_service') as mock_service:
            mock_service.is_running = True
            mock_service.active_connections = {"tenant1": [Mock(), Mock()]}
            mock_service.dashboard_cache = {"key1": Mock(), "key2": Mock()}
            
            response = client.get("/api/security-dashboard/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "security_dashboard"
            assert data["status"] == "healthy"
            assert data["real_time_updates_active"] is True
            assert data["active_connections"] == 2
            assert data["active_tenants"] == 1
            assert data["cache_entries"] == 2


class TestIntegration:
    """Integration tests for security dashboard."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_dashboard_workflow(self):
        """Test complete dashboard workflow."""
        dashboard_service = SecurityDashboardService()
        tenant_id = "integration-test-tenant"
        
        try:
            # Test getting dashboard data
            with patch.object(dashboard_service, 'security_event_monitor') as mock_monitor:
                with patch.object(dashboard_service.compliance_generator, 'generate_report') as mock_report_gen:
                    # Setup mocks
                    mock_monitor.get_events_by_tenant.return_value = []
                    mock_monitor.get_monitoring_status.return_value = "active"
                    mock_monitor.get_last_scan_time.return_value = datetime.now()
                    mock_monitor.is_monitoring_active.return_value = True
                    
                    mock_report = Mock()
                    mock_report.overall_compliance_score = 85.0
                    mock_report.metrics = []
                    mock_report.violations = []
                    mock_report.audit_statistics = {"coverage_percentage": 90.0}
                    mock_report.data_protection_statistics = {"protection_score": 88.0}
                    mock_report.access_control_statistics = {"control_score": 92.0}
                    mock_report_gen.return_value = mock_report
                    
                    with patch.object(dashboard_service, 'threat_detector') as mock_detector:
                        mock_detector.is_active.return_value = True
                        
                        # Get dashboard data
                        dashboard_data = await dashboard_service.get_dashboard_data(
                            tenant_id, DashboardTimeRange.LAST_24_HOURS
                        )
                        
                        # Verify data structure
                        assert isinstance(dashboard_data, DashboardData)
                        assert dashboard_data.tenant_id == tenant_id
                        assert isinstance(dashboard_data.security_metrics, SecurityMetrics)
                        assert isinstance(dashboard_data.compliance_metrics, ComplianceMetrics)
                        
                        # Test caching
                        cached_data = await dashboard_service.get_dashboard_data(
                            tenant_id, DashboardTimeRange.LAST_24_HOURS
                        )
                        assert cached_data.timestamp == dashboard_data.timestamp
                        
                        # Test summary
                        summary = dashboard_service.get_dashboard_summary(tenant_id)
                        assert isinstance(summary, dict)
                        assert summary["tenant_id"] == tenant_id
                        
        finally:
            # Cleanup
            if dashboard_service.is_running:
                await dashboard_service.stop_real_time_updates()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])