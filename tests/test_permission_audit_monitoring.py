"""
Comprehensive test suite for permission audit and monitoring system.

Tests the integration of RBAC permissions with audit system including:
- Permission check auditing
- Role assignment/revocation auditing
- Security alert generation
- Permission usage analysis
- Monitoring and reporting
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, AsyncMock

from src.security.permission_audit_integration import (
    PermissionAuditIntegration, PermissionEventType, get_permission_audit_integration
)
from src.security.rbac_controller import RBACController
from src.security.rbac_models import PermissionScope, ResourceType
from src.security.models import AuditAction, UserRole


class TestPermissionAuditIntegration:
    """Test the PermissionAuditIntegration class functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.audit_integration = PermissionAuditIntegration()
        self.user_id = uuid4()
        self.tenant_id = "test_tenant"
        self.permission_name = "read_data"
        
        # Mock database session
        self.mock_db = Mock()
    
    @pytest.mark.asyncio
    async def test_log_permission_check_success(self):
        """Test logging successful permission check."""
        with patch.object(self.audit_integration.audit_service, 'log_enhanced_audit_event') as mock_log:
            mock_log.return_value = {"status": "success", "audit_log_id": uuid4()}
            
            result = await self.audit_integration.log_permission_check(
                user_id=self.user_id,
                tenant_id=self.tenant_id,
                permission_name=self.permission_name,
                result=True,
                cache_hit=True,
                response_time_ms=5.2,
                db=self.mock_db
            )
            
            assert result["status"] == "success"
            mock_log.assert_called_once()
            
            # Verify call arguments
            call_args = mock_log.call_args
            assert call_args[1]["user_id"] == self.user_id
            assert call_args[1]["tenant_id"] == self.tenant_id
            assert call_args[1]["action"] == AuditAction.READ
            assert call_args[1]["resource_type"] == "permission"
            assert call_args[1]["resource_id"] == self.permission_name
            assert call_args[1]["details"]["check_result"] is True
            assert call_args[1]["details"]["cache_hit"] is True
            assert call_args[1]["details"]["response_time_ms"] == 5.2
    
    @pytest.mark.asyncio
    async def test_log_permission_check_denied(self):
        """Test logging denied permission check."""
        with patch.object(self.audit_integration.audit_service, 'log_enhanced_audit_event') as mock_log:
            mock_log.return_value = {"status": "success", "audit_log_id": uuid4()}
            
            with patch.object(self.audit_integration, '_analyze_permission_denial') as mock_analyze:
                mock_analyze.return_value = None
                
                result = await self.audit_integration.log_permission_check(
                    user_id=self.user_id,
                    tenant_id=self.tenant_id,
                    permission_name=self.permission_name,
                    result=False,
                    cache_hit=False,
                    response_time_ms=15.8,
                    db=self.mock_db
                )
                
                assert result["status"] == "success"
                mock_log.assert_called_once()
                mock_analyze.assert_called_once_with(
                    self.user_id, self.tenant_id, self.permission_name, self.mock_db
                )
                
                # Verify denied access uses LOGIN action
                call_args = mock_log.call_args
                assert call_args[1]["action"] == AuditAction.LOGIN
                assert call_args[1]["details"]["check_result"] is False
    
    @pytest.mark.asyncio
    async def test_log_role_assignment(self):
        """Test logging role assignment."""
        role_id = uuid4()
        assigned_by = uuid4()
        role_name = "data_analyst"
        
        with patch.object(self.audit_integration.audit_service, 'log_enhanced_audit_event') as mock_log:
            mock_log.return_value = {"status": "success", "audit_log_id": uuid4()}
            
            with patch.object(self.audit_integration, '_check_permission_escalation') as mock_check:
                mock_check.return_value = None
                
                result = await self.audit_integration.log_role_assignment(
                    user_id=self.user_id,
                    role_id=role_id,
                    assigned_by=assigned_by,
                    tenant_id=self.tenant_id,
                    role_name=role_name,
                    db=self.mock_db
                )
                
                assert result["status"] == "success"
                mock_log.assert_called_once()
                mock_check.assert_called_once()
                
                # Verify call arguments
                call_args = mock_log.call_args
                assert call_args[1]["user_id"] == assigned_by  # Executor of action
                assert call_args[1]["action"] == AuditAction.UPDATE
                assert call_args[1]["resource_type"] == "user_role"
                assert call_args[1]["resource_id"] == str(self.user_id)
                assert call_args[1]["details"]["role_name"] == role_name
                assert call_args[1]["details"]["event_type"] == PermissionEventType.ROLE_ASSIGNED.value
    
    @pytest.mark.asyncio
    async def test_log_role_revocation(self):
        """Test logging role revocation."""
        role_id = uuid4()
        revoked_by = uuid4()
        role_name = "data_analyst"
        
        with patch.object(self.audit_integration.audit_service, 'log_enhanced_audit_event') as mock_log:
            mock_log.return_value = {"status": "success", "audit_log_id": uuid4()}
            
            result = await self.audit_integration.log_role_revocation(
                user_id=self.user_id,
                role_id=role_id,
                revoked_by=revoked_by,
                tenant_id=self.tenant_id,
                role_name=role_name,
                db=self.mock_db
            )
            
            assert result["status"] == "success"
            mock_log.assert_called_once()
            
            # Verify call arguments
            call_args = mock_log.call_args
            assert call_args[1]["user_id"] == revoked_by  # Executor of action
            assert call_args[1]["action"] == AuditAction.DELETE
            assert call_args[1]["resource_type"] == "user_role"
            assert call_args[1]["details"]["event_type"] == PermissionEventType.ROLE_REVOKED.value
    
    @pytest.mark.asyncio
    async def test_log_bulk_permission_check(self):
        """Test logging bulk permission check."""
        permissions = ["read_data", "write_data", "delete_data"]
        results = {"read_data": True, "write_data": True, "delete_data": False}
        
        with patch.object(self.audit_integration.audit_service, 'log_enhanced_audit_event') as mock_log:
            mock_log.return_value = {"status": "success", "audit_log_id": uuid4()}
            
            with patch.object(self.audit_integration, '_check_bulk_permission_abuse') as mock_check:
                mock_check.return_value = None
                
                result = await self.audit_integration.log_bulk_permission_check(
                    user_id=self.user_id,
                    tenant_id=self.tenant_id,
                    permissions=permissions,
                    results=results,
                    cache_hits=2,
                    total_response_time_ms=25.5,
                    db=self.mock_db
                )
                
                assert result["status"] == "success"
                mock_log.assert_called_once()
                mock_check.assert_called_once()
                
                # Verify call arguments
                call_args = mock_log.call_args
                assert call_args[1]["action"] == AuditAction.READ
                assert call_args[1]["resource_type"] == "permission_batch"
                assert call_args[1]["details"]["total_permissions"] == 3
                assert call_args[1]["details"]["granted_permissions"] == 2
                assert call_args[1]["details"]["denied_permissions"] == 1
                assert call_args[1]["details"]["cache_hit_rate"] == (2/3) * 100
    
    @pytest.mark.asyncio
    async def test_analyze_permission_denial(self):
        """Test permission denial analysis."""
        with patch.object(self.audit_integration, '_count_recent_permission_denials') as mock_count:
            mock_count.return_value = 15  # High number of denials
            
            with patch.object(self.audit_integration, '_trigger_unusual_permission_pattern_alert') as mock_alert:
                mock_alert.return_value = None
                
                await self.audit_integration._analyze_permission_denial(
                    self.user_id, self.tenant_id, self.permission_name, self.mock_db
                )
                
                mock_count.assert_called_once()
                mock_alert.assert_called_once_with(
                    self.user_id, self.tenant_id, 15, self.mock_db
                )
    
    @pytest.mark.asyncio
    async def test_analyze_permission_usage(self):
        """Test permission usage analysis."""
        # Mock audit logs
        mock_logs = []
        
        # Create mock permission check logs
        for i in range(10):
            mock_log = Mock()
            mock_log.resource_type = "permission"
            mock_log.user_id = self.user_id
            mock_log.details = {
                "permission_name": f"permission_{i % 3}",
                "check_result": i % 4 != 0,  # 75% success rate
                "cache_hit": i % 2 == 0  # 50% cache hit rate
            }
            mock_logs.append(mock_log)
        
        # Create mock role change logs
        for i in range(3):
            mock_log = Mock()
            mock_log.resource_type = "user_role"
            mock_log.action = AuditAction.UPDATE if i < 2 else AuditAction.DELETE
            mock_log.user_id = self.user_id
            mock_log.details = {"role_name": f"role_{i}"}
            mock_logs.append(mock_log)
        
        # Create mock batch operation logs
        mock_log = Mock()
        mock_log.resource_type = "permission_batch"
        mock_log.user_id = self.user_id
        mock_log.details = {"total_permissions": 5}
        mock_logs.append(mock_log)
        
        with patch.object(self.mock_db, 'execute') as mock_execute:
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_logs
            mock_execute.return_value = mock_result
            
            with patch.object(self.audit_integration, '_count_permission_security_alerts') as mock_alerts:
                mock_alerts.return_value = {"permission_escalation": 2, "unusual_pattern": 1}
                
                result = await self.audit_integration.analyze_permission_usage(
                    self.tenant_id, 30, self.mock_db
                )
                
                assert result["analysis_period_days"] == 30
                assert result["total_permission_events"] == 14
                assert result["permission_checks"]["total"] == 10
                assert result["permission_checks"]["successful"] == 7  # 70% success
                assert result["permission_checks"]["success_rate"] == 70.0
                assert result["permission_checks"]["cache_hit_rate"] == 50.0
                assert result["role_changes"]["assignments"] == 2
                assert result["role_changes"]["revocations"] == 1
                assert result["batch_operations"]["total_permissions_checked"] == 5
                assert result["active_users_count"] == 1
                assert result["security_alerts"]["permission_escalation"] == 2
    
    @pytest.mark.asyncio
    async def test_generate_permission_report_summary(self):
        """Test generating summary permission report."""
        mock_usage_analysis = {
            "total_permission_events": 100,
            "permission_checks": {"success_rate": 85.5, "cache_hit_rate": 92.3},
            "active_users_count": 25,
            "security_alerts": {"permission_escalation": 2, "unusual_pattern": 1}
        }
        
        with patch.object(self.audit_integration, 'analyze_permission_usage') as mock_analyze:
            mock_analyze.return_value = mock_usage_analysis
            
            with patch.object(self.audit_integration, '_generate_permission_recommendations') as mock_recommendations:
                mock_recommendations.return_value = [
                    {
                        "type": "performance",
                        "priority": "low",
                        "title": "Cache performance is good",
                        "description": "Cache hit rate is above 90%"
                    }
                ]
                
                result = await self.audit_integration.generate_permission_report(
                    self.tenant_id, "summary", 30, self.mock_db
                )
                
                assert result["report_type"] == "permission_summary"
                assert result["tenant_id"] == self.tenant_id
                assert result["period_days"] == 30
                assert result["summary"]["total_events"] == 100
                assert result["summary"]["permission_success_rate"] == 85.5
                assert result["summary"]["cache_efficiency"] == 92.3
                assert result["summary"]["active_users"] == 25
                assert result["summary"]["security_alerts"] == 3
                assert len(result["recommendations"]) == 1
    
    @pytest.mark.asyncio
    async def test_generate_permission_recommendations(self):
        """Test generating permission optimization recommendations."""
        # Test low cache hit rate
        usage_analysis = {
            "permission_checks": {"cache_hit_rate": 65.0, "success_rate": 85.0},
            "security_alerts": {"permission_escalation": 2}
        }
        
        recommendations = await self.audit_integration._generate_permission_recommendations(usage_analysis)
        
        # Should recommend cache optimization
        cache_rec = next((r for r in recommendations if "缓存" in r["description"]), None)
        assert cache_rec is not None
        assert cache_rec["type"] == "performance"
        assert cache_rec["priority"] == "medium"
        
        # Test low success rate
        usage_analysis["permission_checks"]["success_rate"] = 60.0
        recommendations = await self.audit_integration._generate_permission_recommendations(usage_analysis)
        
        # Should recommend permission configuration review
        config_rec = next((r for r in recommendations if "权限配置" in r["description"]), None)
        assert config_rec is not None
        assert config_rec["type"] == "security"
        assert config_rec["priority"] == "high"
        
        # Test high security alerts
        usage_analysis["security_alerts"] = {"permission_escalation": 15, "unusual_pattern": 5}
        recommendations = await self.audit_integration._generate_permission_recommendations(usage_analysis)
        
        # Should recommend security review
        security_rec = next((r for r in recommendations if "安全告警" in r["description"]), None)
        assert security_rec is not None
        assert security_rec["type"] == "security"
        assert security_rec["priority"] == "high"


class TestRBACControllerAuditIntegration:
    """Test RBAC controller integration with audit system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.controller = RBACController()
        self.user_id = uuid4()
        self.tenant_id = "test_tenant"
        
        # Mock database session
        self.mock_db = Mock()
        
        # Mock user
        self.mock_user = Mock()
        self.mock_user.id = self.user_id
        self.mock_user.tenant_id = self.tenant_id
        self.mock_user.is_active = True
        self.mock_user.role = UserRole.VIEWER
    
    def test_check_user_permission_with_audit(self):
        """Test permission check with audit logging."""
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            with patch.object(self.controller, '_check_permission_through_roles') as mock_check:
                mock_check.return_value = True
                
                with patch.object(self.controller.permission_audit, 'log_permission_check') as mock_log:
                    # Mock async task creation
                    with patch('asyncio.get_event_loop') as mock_loop:
                        mock_event_loop = Mock()
                        mock_event_loop.create_task = Mock()
                        mock_loop.return_value = mock_event_loop
                        
                        result = self.controller.check_user_permission(
                            self.user_id, "read_data", db=self.mock_db,
                            ip_address="192.168.1.1", user_agent="test-agent"
                        )
                        
                        assert result is True
                        mock_event_loop.create_task.assert_called_once()
    
    def test_assign_role_to_user_with_audit(self):
        """Test role assignment with audit logging."""
        role_id = uuid4()
        assigned_by = uuid4()
        
        # Mock role
        mock_role = Mock()
        mock_role.id = role_id
        mock_role.name = "data_analyst"
        mock_role.tenant_id = self.tenant_id
        
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            with patch.object(self.controller, 'get_role_by_id') as mock_get_role:
                mock_get_role.return_value = mock_role
                
                # Mock database operations
                self.mock_db.query.return_value.filter.return_value.first.return_value = None
                self.mock_db.add = Mock()
                self.mock_db.commit = Mock()
                
                with patch.object(self.controller, 'log_user_action') as mock_log_action:
                    with patch.object(self.controller.permission_audit, 'log_role_assignment') as mock_log_audit:
                        # Mock async task creation
                        with patch('asyncio.get_event_loop') as mock_loop:
                            mock_event_loop = Mock()
                            mock_event_loop.create_task = Mock()
                            mock_loop.return_value = mock_event_loop
                            
                            result = self.controller.assign_role_to_user(
                                self.user_id, role_id, assigned_by, self.mock_db,
                                ip_address="192.168.1.1", user_agent="test-agent"
                            )
                            
                            assert result is True
                            mock_event_loop.create_task.assert_called_once()
                            mock_log_action.assert_called_once()
    
    def test_batch_check_permissions_with_audit(self):
        """Test batch permission check with audit logging."""
        permissions = ["read_data", "write_data", "delete_data"]
        
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            with patch.object(self.controller, 'check_user_permission') as mock_check:
                mock_check.side_effect = [True, True, False]  # Mixed results
                
                with patch.object(self.controller.permission_audit, 'log_bulk_permission_check') as mock_log:
                    # Mock async task creation
                    with patch('asyncio.get_event_loop') as mock_loop:
                        mock_event_loop = Mock()
                        mock_event_loop.create_task = Mock()
                        mock_loop.return_value = mock_event_loop
                        
                        results = self.controller.batch_check_permissions(
                            self.user_id, permissions, db=self.mock_db,
                            ip_address="192.168.1.1", user_agent="test-agent"
                        )
                        
                        assert results["read_data"] is True
                        assert results["write_data"] is True
                        assert results["delete_data"] is False
                        mock_event_loop.create_task.assert_called_once()


class TestPermissionMonitoringAPI:
    """Test permission monitoring API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tenant_id = "test_tenant"
        self.user_id = uuid4()
    
    @pytest.mark.asyncio
    async def test_permission_usage_analysis_api(self):
        """Test permission usage analysis API endpoint."""
        from src.api.permission_monitoring import get_permission_usage_analysis
        
        mock_analysis = {
            "analysis_period_days": 30,
            "total_permission_events": 150,
            "permission_checks": {
                "total": 100,
                "successful": 85,
                "success_rate": 85.0,
                "cache_hit_rate": 90.0
            },
            "role_changes": {"total": 10, "assignments": 7, "revocations": 3},
            "batch_operations": {"total": 5, "total_permissions_checked": 25},
            "most_used_permissions": {"read_data": 50, "write_data": 30},
            "active_users_count": 20,
            "security_alerts": {"permission_escalation": 2}
        }
        
        mock_db = Mock()
        
        with patch('src.api.permission_monitoring.permission_audit') as mock_audit:
            mock_audit.analyze_permission_usage = AsyncMock(return_value=mock_analysis)
            
            result = await get_permission_usage_analysis(self.tenant_id, 30, mock_db)
            
            assert result.analysis_period_days == 30
            assert result.total_permission_events == 150
            assert result.permission_checks["success_rate"] == 85.0
            assert result.active_users_count == 20
    
    @pytest.mark.asyncio
    async def test_generate_permission_report_api(self):
        """Test permission report generation API endpoint."""
        from src.api.permission_monitoring import generate_permission_report, PermissionReportRequest
        
        mock_report = {
            "report_type": "permission_summary",
            "tenant_id": self.tenant_id,
            "period_days": 30,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_events": 100,
                "permission_success_rate": 85.0,
                "cache_efficiency": 90.0,
                "active_users": 20,
                "security_alerts": 3
            },
            "recommendations": [
                {
                    "type": "performance",
                    "priority": "low",
                    "title": "Good performance",
                    "description": "System is performing well"
                }
            ]
        }
        
        request = PermissionReportRequest(
            tenant_id=self.tenant_id,
            report_type="summary",
            days=30
        )
        
        mock_db = Mock()
        
        with patch('src.api.permission_monitoring.permission_audit') as mock_audit:
            mock_audit.generate_permission_report = AsyncMock(return_value=mock_report)
            
            result = await generate_permission_report(request, mock_db)
            
            assert result.report_type == "permission_summary"
            assert result.tenant_id == self.tenant_id
            assert result.summary["total_events"] == 100
            assert len(result.recommendations) == 1


def test_global_permission_audit_integration_instance():
    """Test global permission audit integration instance management."""
    instance1 = get_permission_audit_integration()
    instance2 = get_permission_audit_integration()
    
    # Should return same instance
    assert instance1 is instance2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])