"""
Tests for Permission Bypass Prevention System.

Comprehensive test suite to validate that the permission bypass prevention
system effectively blocks unauthorized access attempts.
"""

import pytest
import time
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, MagicMock

from src.security.permission_bypass_prevention import (
    PermissionBypassPrevention,
    PermissionValidator,
    BypassDetector,
    SecurityEnforcer,
    SecurityContext,
    BypassAttemptType,
    SecurityThreatLevel,
    get_bypass_prevention_system
)
from src.security.rbac_controller_secure import SecureRBACController, get_secure_rbac_controller
from src.security.rbac_controller import RBACController
from src.security.models import UserModel, UserRole
from src.security.rbac_models import RoleModel, PermissionModel, ResourceType, PermissionScope


class TestPermissionValidator:
    """Test the permission validation system."""
    
    @pytest.fixture
    def validator(self):
        return PermissionValidator()
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def security_context(self):
        return SecurityContext(
            user_id=uuid4(),
            tenant_id="test-tenant",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0",
            request_timestamp=datetime.utcnow()
        )
    
    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=UserModel)
        user.id = uuid4()
        user.tenant_id = "test-tenant"
        user.is_active = True
        user.role = UserRole.BUSINESS_EXPERT
        return user
    
    def test_validate_user_existence_success(self, validator, mock_db, security_context, mock_user):
        """Test successful user existence validation."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        is_valid, error_msg = validator._validate_user_existence(
            security_context, "read_data", None, None, mock_db
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_user_existence_user_not_found(self, validator, mock_db, security_context):
        """Test user existence validation when user doesn't exist."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        is_valid, error_msg = validator._validate_user_existence(
            security_context, "read_data", None, None, mock_db
        )
        
        assert is_valid is False
        assert "does not exist" in error_msg
    
    def test_validate_user_existence_tenant_mismatch(self, validator, mock_db, security_context, mock_user):
        """Test user existence validation with tenant mismatch."""
        mock_user.tenant_id = "different-tenant"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        is_valid, error_msg = validator._validate_user_existence(
            security_context, "read_data", None, None, mock_db
        )
        
        assert is_valid is False
        assert "tenant mismatch" in error_msg.lower()
    
    def test_validate_user_active_status_success(self, validator, mock_db, security_context, mock_user):
        """Test successful user active status validation."""
        mock_user.is_active = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        is_valid, error_msg = validator._validate_user_active_status(
            security_context, "read_data", None, None, mock_db
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_user_active_status_inactive_user(self, validator, mock_db, security_context, mock_user):
        """Test user active status validation with inactive user."""
        mock_user.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        is_valid, error_msg = validator._validate_user_active_status(
            security_context, "read_data", None, None, mock_db
        )
        
        assert is_valid is False
        assert "not active" in error_msg
    
    def test_validate_tenant_isolation_success(self, validator, mock_db, security_context, mock_user):
        """Test successful tenant isolation validation."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        is_valid, error_msg = validator._validate_tenant_isolation(
            security_context, "read_data", None, None, mock_db
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_role_integrity_admin_permission_non_admin(self, validator, mock_db, security_context, mock_user):
        """Test role integrity validation for admin permission by non-admin user."""
        mock_user.role = UserRole.BUSINESS_EXPERT
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        is_valid, error_msg = validator._validate_role_integrity(
            security_context, "manage_users", None, None, mock_db
        )
        
        assert is_valid is False
        assert "non-admin user attempting admin permission" in error_msg.lower()
    
    def test_validate_role_integrity_admin_permission_admin_user(self, validator, mock_db, security_context, mock_user):
        """Test role integrity validation for admin permission by admin user."""
        mock_user.role = UserRole.ADMIN
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        is_valid, error_msg = validator._validate_role_integrity(
            security_context, "manage_users", None, None, mock_db
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_permission_scope_success(self, validator, mock_db, security_context):
        """Test successful permission scope validation."""
        mock_permission = Mock(spec=PermissionModel)
        mock_permission.name = "read_data"
        mock_permission.resource_type = ResourceType.PROJECT
        mock_db.query.return_value.filter.return_value.first.return_value = mock_permission
        
        is_valid, error_msg = validator._validate_permission_scope(
            security_context, "read_data", None, ResourceType.PROJECT, mock_db
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_permission_scope_nonexistent_permission(self, validator, mock_db, security_context):
        """Test permission scope validation with nonexistent permission."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        is_valid, error_msg = validator._validate_permission_scope(
            security_context, "nonexistent_permission", None, None, mock_db
        )
        
        assert is_valid is False
        assert "does not exist" in error_msg
    
    def test_validate_temporal_constraints_recent_timestamp(self, validator, mock_db, security_context):
        """Test temporal constraints validation with recent timestamp."""
        security_context.request_timestamp = datetime.utcnow()
        
        is_valid, error_msg = validator._validate_temporal_constraints(
            security_context, "read_data", None, None, mock_db
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_temporal_constraints_old_timestamp(self, validator, mock_db, security_context):
        """Test temporal constraints validation with old timestamp."""
        security_context.request_timestamp = datetime.utcnow() - timedelta(minutes=10)
        
        is_valid, error_msg = validator._validate_temporal_constraints(
            security_context, "read_data", None, None, mock_db
        )
        
        assert is_valid is False
        assert "timestamp too old" in error_msg.lower()
    
    def test_validate_request_context_valid_ip(self, validator, mock_db, security_context):
        """Test request context validation with valid IP."""
        security_context.ip_address = "192.168.1.100"
        
        is_valid, error_msg = validator._validate_request_context(
            security_context, "read_data", None, None, mock_db
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_request_context_invalid_ip(self, validator, mock_db, security_context):
        """Test request context validation with invalid IP."""
        security_context.ip_address = "invalid-ip"
        
        is_valid, error_msg = validator._validate_request_context(
            security_context, "read_data", None, None, mock_db
        )
        
        assert is_valid is False
        assert "invalid ip address" in error_msg.lower()


class TestBypassDetector:
    """Test the bypass attempt detection system."""
    
    @pytest.fixture
    def detector(self):
        return BypassDetector()
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def security_context(self):
        return SecurityContext(
            user_id=uuid4(),
            tenant_id="test-tenant",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0"
        )
    
    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=UserModel)
        user.id = uuid4()
        user.tenant_id = "test-tenant"
        user.role = UserRole.BUSINESS_EXPERT
        return user
    
    def test_detect_privilege_escalation_admin_permission_non_admin(self, detector, mock_db, security_context, mock_user):
        """Test detection of privilege escalation attempt."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        attempts = detector._detect_privilege_escalation(
            security_context, "manage_users", False, [], mock_db
        )
        
        assert len(attempts) == 1
        assert attempts[0].attempt_type == BypassAttemptType.PRIVILEGE_ESCALATION
        assert attempts[0].threat_level == SecurityThreatLevel.HIGH
    
    def test_detect_privilege_escalation_regular_permission(self, detector, mock_db, security_context, mock_user):
        """Test no detection for regular permission."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        attempts = detector._detect_privilege_escalation(
            security_context, "read_data", True, [], mock_db
        )
        
        assert len(attempts) == 0
    
    def test_detect_tenant_boundary_violation(self, detector, mock_db, security_context):
        """Test detection of tenant boundary violation."""
        validation_errors = ["Cross-tenant access attempt detected"]
        
        attempts = detector._detect_tenant_boundary_violation(
            security_context, "read_data", False, validation_errors, mock_db
        )
        
        assert len(attempts) == 1
        assert attempts[0].attempt_type == BypassAttemptType.TENANT_BOUNDARY_VIOLATION
        assert attempts[0].threat_level == SecurityThreatLevel.CRITICAL
    
    def test_detect_role_impersonation(self, detector, mock_db, security_context):
        """Test detection of role impersonation attempt."""
        validation_errors = ["Role mismatch detected"]
        
        attempts = detector._detect_role_impersonation(
            security_context, "read_data", False, validation_errors, mock_db
        )
        
        assert len(attempts) == 1
        assert attempts[0].attempt_type == BypassAttemptType.ROLE_IMPERSONATION
        assert attempts[0].threat_level == SecurityThreatLevel.HIGH
    
    def test_detect_brute_force_permissions(self, detector, mock_db, security_context):
        """Test detection of brute force permission attempts."""
        # Simulate multiple failed attempts
        for _ in range(15):
            detector._record_activity(security_context, "read_data", False)
        
        attempts = detector._detect_brute_force_permissions(
            security_context, "read_data", False, [], mock_db
        )
        
        assert len(attempts) == 1
        assert attempts[0].attempt_type == BypassAttemptType.BRUTE_FORCE_PERMISSIONS
        assert attempts[0].threat_level == SecurityThreatLevel.MEDIUM
    
    def test_detect_suspicious_patterns_multiple_users_same_ip(self, detector, mock_db, security_context):
        """Test detection of suspicious IP patterns."""
        # Simulate multiple users from same IP
        for i in range(6):
            context = SecurityContext(
                user_id=uuid4(),
                tenant_id="test-tenant",
                ip_address="192.168.1.100"
            )
            detector._record_activity(context, "read_data", True)
        
        attempts = detector._detect_suspicious_patterns(
            security_context, "read_data", True, [], mock_db
        )
        
        assert len(attempts) == 1
        assert attempts[0].attempt_type == BypassAttemptType.SESSION_HIJACKING
        assert attempts[0].threat_level == SecurityThreatLevel.MEDIUM


class TestSecurityEnforcer:
    """Test the security enforcement system."""
    
    @pytest.fixture
    def enforcer(self):
        return SecurityEnforcer()
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def security_context(self):
        return SecurityContext(
            user_id=uuid4(),
            tenant_id="test-tenant",
            ip_address="192.168.1.100"
        )
    
    def test_is_user_blocked_not_blocked(self, enforcer):
        """Test checking if user is blocked when not blocked."""
        user_id = uuid4()
        assert enforcer.is_user_blocked(user_id) is False
    
    def test_is_user_blocked_temporarily_blocked(self, enforcer):
        """Test checking if user is temporarily blocked."""
        user_id = uuid4()
        enforcer._block_user_temporarily(user_id, hours=1)
        assert enforcer.is_user_blocked(user_id) is True
    
    def test_is_user_blocked_expired_block(self, enforcer):
        """Test checking if user block has expired."""
        user_id = uuid4()
        # Set block that expires immediately
        with enforcer._lock:
            enforcer.temporary_blocks[user_id] = datetime.utcnow() - timedelta(seconds=1)
        
        assert enforcer.is_user_blocked(user_id) is False
        # Block should be removed after check
        assert user_id not in enforcer.temporary_blocks
    
    def test_is_ip_blocked_not_blocked(self, enforcer):
        """Test checking if IP is blocked when not blocked."""
        assert enforcer.is_ip_blocked("192.168.1.100") is False
    
    def test_is_ip_blocked_temporarily_blocked(self, enforcer):
        """Test checking if IP is temporarily blocked."""
        ip_address = "192.168.1.100"
        enforcer._block_ip_temporarily(ip_address, hours=1)
        assert enforcer.is_ip_blocked(ip_address) is True
    
    @patch('src.security.models.AuditLogModel')
    def test_enforce_security_policy_critical_threat(self, mock_audit_model, enforcer, mock_db, security_context):
        """Test enforcement for critical threat level."""
        from src.security.permission_bypass_prevention import BypassAttempt
        
        attempt = BypassAttempt(
            attempt_type=BypassAttemptType.TENANT_BOUNDARY_VIOLATION,
            threat_level=SecurityThreatLevel.CRITICAL,
            user_id=security_context.user_id,
            tenant_id=security_context.tenant_id,
            ip_address=security_context.ip_address,
            timestamp=datetime.utcnow(),
            details={"test": "data"}
        )
        
        actions = enforcer.enforce_security_policy([attempt], security_context, mock_db)
        
        assert actions["blocked"] is True
        assert actions["user_suspended"] is True
        assert actions["ip_blocked"] is True
        assert actions["audit_logged"] is True
    
    @patch('src.security.models.AuditLogModel')
    def test_enforce_security_policy_high_threat(self, mock_audit_model, enforcer, mock_db, security_context):
        """Test enforcement for high threat level."""
        from src.security.permission_bypass_prevention import BypassAttempt
        
        attempt = BypassAttempt(
            attempt_type=BypassAttemptType.PRIVILEGE_ESCALATION,
            threat_level=SecurityThreatLevel.HIGH,
            user_id=security_context.user_id,
            tenant_id=security_context.tenant_id,
            ip_address=security_context.ip_address,
            timestamp=datetime.utcnow(),
            details={"test": "data"}
        )
        
        actions = enforcer.enforce_security_policy([attempt], security_context, mock_db)
        
        assert actions["blocked"] is True
        assert actions["user_suspended"] is True
        assert actions["ip_blocked"] is False  # Only user blocked for high threat
        assert actions["audit_logged"] is True
    
    def test_enforce_security_policy_no_attempts(self, enforcer, mock_db, security_context):
        """Test enforcement with no bypass attempts."""
        actions = enforcer.enforce_security_policy([], security_context, mock_db)
        
        assert actions["blocked"] is False
        assert actions["user_suspended"] is False
        assert actions["ip_blocked"] is False
        assert actions["audit_logged"] is False


class TestPermissionBypassPrevention:
    """Test the main bypass prevention system."""
    
    @pytest.fixture
    def bypass_prevention(self):
        return PermissionBypassPrevention()
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def security_context(self):
        return SecurityContext(
            user_id=uuid4(),
            tenant_id="test-tenant",
            ip_address="192.168.1.100",
            user_agent="TestAgent/1.0"
        )
    
    @patch('src.security.permission_bypass_prevention.PermissionValidator')
    @patch('src.security.permission_bypass_prevention.BypassDetector')
    @patch('src.security.permission_bypass_prevention.SecurityEnforcer')
    def test_check_permission_with_bypass_prevention_success(
        self, mock_enforcer_class, mock_detector_class, mock_validator_class,
        bypass_prevention, mock_db, security_context
    ):
        """Test successful permission check with bypass prevention."""
        # Mock validator
        mock_validator = Mock()
        mock_validator.validate_permission_request.return_value = (True, [])
        mock_validator_class.return_value = mock_validator
        
        # Mock detector
        mock_detector = Mock()
        mock_detector.detect_bypass_attempts.return_value = []
        mock_detector_class.return_value = mock_detector
        
        # Mock enforcer
        mock_enforcer = Mock()
        mock_enforcer.is_user_blocked.return_value = False
        mock_enforcer.is_ip_blocked.return_value = False
        mock_enforcer_class.return_value = mock_enforcer
        
        # Create new instance to use mocked classes
        bypass_prevention = PermissionBypassPrevention()
        
        result, security_info = bypass_prevention.check_permission_with_bypass_prevention(
            security_context, "read_data", None, None, mock_db
        )
        
        assert result is True
        assert security_info["validation_passed"] is True
        assert security_info["blocked"] is False
    
    @patch('src.security.permission_bypass_prevention.PermissionValidator')
    @patch('src.security.permission_bypass_prevention.BypassDetector')
    @patch('src.security.permission_bypass_prevention.SecurityEnforcer')
    def test_check_permission_with_bypass_prevention_blocked_user(
        self, mock_enforcer_class, mock_detector_class, mock_validator_class,
        bypass_prevention, mock_db, security_context
    ):
        """Test permission check with blocked user."""
        # Mock enforcer
        mock_enforcer = Mock()
        mock_enforcer.is_user_blocked.return_value = True
        mock_enforcer_class.return_value = mock_enforcer
        
        # Create new instance to use mocked classes
        bypass_prevention = PermissionBypassPrevention()
        
        result, security_info = bypass_prevention.check_permission_with_bypass_prevention(
            security_context, "read_data", None, None, mock_db
        )
        
        assert result is False
        assert security_info["blocked"] is True
        assert "User temporarily blocked" in security_info["block_reason"]
    
    @patch('src.security.permission_bypass_prevention.PermissionValidator')
    @patch('src.security.permission_bypass_prevention.BypassDetector')
    @patch('src.security.permission_bypass_prevention.SecurityEnforcer')
    def test_check_permission_with_bypass_prevention_validation_failed(
        self, mock_enforcer_class, mock_detector_class, mock_validator_class,
        bypass_prevention, mock_db, security_context
    ):
        """Test permission check with validation failure."""
        # Mock validator
        mock_validator = Mock()
        mock_validator.validate_permission_request.return_value = (False, ["Validation error"])
        mock_validator_class.return_value = mock_validator
        
        # Mock detector
        mock_detector = Mock()
        mock_detector.detect_bypass_attempts.return_value = []
        mock_detector_class.return_value = mock_detector
        
        # Mock enforcer
        mock_enforcer = Mock()
        mock_enforcer.is_user_blocked.return_value = False
        mock_enforcer.is_ip_blocked.return_value = False
        mock_enforcer_class.return_value = mock_enforcer
        
        # Create new instance to use mocked classes
        bypass_prevention = PermissionBypassPrevention()
        
        result, security_info = bypass_prevention.check_permission_with_bypass_prevention(
            security_context, "read_data", None, None, mock_db
        )
        
        assert result is False
        assert security_info["validation_passed"] is False
        assert "Validation error" in security_info["validation_errors"]
    
    def test_get_security_statistics(self, bypass_prevention):
        """Test getting security statistics."""
        stats = bypass_prevention.get_security_statistics()
        
        assert "total_checks" in stats
        assert "blocked_attempts" in stats
        assert "bypass_attempts_detected" in stats
        assert "validation_failures" in stats
        assert "enabled" in stats
    
    def test_enable_disable_bypass_prevention(self, bypass_prevention):
        """Test enabling and disabling bypass prevention."""
        bypass_prevention.disable_bypass_prevention()
        assert bypass_prevention.enabled is False
        
        bypass_prevention.enable_bypass_prevention()
        assert bypass_prevention.enabled is True


class TestSecureRBACController:
    """Test the secure RBAC controller."""
    
    @pytest.fixture
    def controller(self):
        return SecureRBACController()
    
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=UserModel)
        user.id = uuid4()
        user.tenant_id = "test-tenant"
        user.is_active = True
        user.role = UserRole.BUSINESS_EXPERT
        return user
    
    @patch('src.security.rbac_controller_secure.get_bypass_prevention_system')
    def test_check_user_permission_secure_success(self, mock_bypass_system, controller, mock_db, mock_user):
        """Test secure permission check success."""
        # Mock bypass prevention system
        mock_bypass = Mock()
        mock_bypass.check_permission_with_bypass_prevention.return_value = (
            True, {"validation_passed": True, "blocked": False}
        )
        mock_bypass_system.return_value = mock_bypass
        
        # Mock user lookup
        controller.get_user_by_id = Mock(return_value=mock_user)
        
        # Replace the controller's bypass prevention instance with the mock
        controller.bypass_prevention = mock_bypass
        
        # Mock parent permission check
        with patch.object(RBACController, 'check_user_permission', return_value=True):
            result, security_info = controller.check_user_permission_secure(
                user_id=mock_user.id,
                permission_name="read_data",
                db=mock_db,
                ip_address="192.168.1.100"
            )
        
        assert result is True
        assert security_info["validation_passed"] is True
        assert security_info["permission_granted"] is True
    
    @patch('src.security.rbac_controller_secure.get_bypass_prevention_system')
    def test_check_user_permission_secure_blocked(self, mock_bypass_system, controller, mock_db, mock_user):
        """Test secure permission check with blocked user."""
        # Mock bypass prevention system
        mock_bypass = Mock()
        mock_bypass.check_permission_with_bypass_prevention.return_value = (
            False, {"validation_passed": False, "blocked": True, "block_reason": "Security violation"}
        )
        mock_bypass_system.return_value = mock_bypass
        
        # Mock user lookup
        controller.get_user_by_id = Mock(return_value=mock_user)
        
        # Replace the controller's bypass prevention instance with the mock
        controller.bypass_prevention = mock_bypass
        
        result, security_info = controller.check_user_permission_secure(
            user_id=mock_user.id,
            permission_name="read_data",
            db=mock_db,
            ip_address="192.168.1.100"
        )
        
        assert result is False
        assert security_info["blocked"] is True
    
    def test_check_user_permission_secure_user_not_found(self, controller, mock_db):
        """Test secure permission check with user not found."""
        controller.get_user_by_id = Mock(return_value=None)
        
        result, security_info = controller.check_user_permission_secure(
            user_id=uuid4(),
            permission_name="read_data",
            db=mock_db
        )
        
        assert result is False
        assert "User not found" in security_info["error"]
        assert security_info["security_violation"] is True
    
    def test_validate_security_context_success(self, controller, mock_db, mock_user):
        """Test successful security context validation."""
        controller.get_user_by_id = Mock(return_value=mock_user)
        
        is_valid, details = controller.validate_security_context(
            user_id=mock_user.id,
            expected_tenant_id=mock_user.tenant_id,
            ip_address="192.168.1.100",
            db=mock_db
        )
        
        assert is_valid is True
        assert details["user_exists"] is True
        assert details["user_active"] is True
        assert details["tenant_match"] is True
    
    def test_validate_security_context_tenant_mismatch(self, controller, mock_db, mock_user):
        """Test security context validation with tenant mismatch."""
        controller.get_user_by_id = Mock(return_value=mock_user)
        
        is_valid, details = controller.validate_security_context(
            user_id=mock_user.id,
            expected_tenant_id="different-tenant",
            ip_address="192.168.1.100",
            db=mock_db
        )
        
        assert is_valid is False
        assert details["tenant_match"] is False
    
    def test_validate_security_context_inactive_user(self, controller, mock_db, mock_user):
        """Test security context validation with inactive user."""
        mock_user.is_active = False
        controller.get_user_by_id = Mock(return_value=mock_user)
        
        is_valid, details = controller.validate_security_context(
            user_id=mock_user.id,
            expected_tenant_id=mock_user.tenant_id,
            db=mock_db
        )
        
        assert is_valid is False
        assert details["user_active"] is False
    
    def test_enable_disable_strict_security(self, controller):
        """Test enabling and disabling strict security mode."""
        controller.enable_strict_security()
        assert controller.security_config["strict_validation"] is True
        assert controller.security_config["auto_block_threats"] is True
        
        controller.disable_strict_security()
        assert controller.security_config["strict_validation"] is False
        assert controller.security_config["auto_block_threats"] is False


class TestIntegration:
    """Integration tests for the complete bypass prevention system."""
    
    @pytest.fixture
    def system(self):
        return get_bypass_prevention_system()
    
    @pytest.fixture
    def controller(self):
        return get_secure_rbac_controller()
    
    def test_global_instances(self, system, controller):
        """Test that global instances are properly created."""
        assert system is not None
        assert controller is not None
        assert isinstance(system, PermissionBypassPrevention)
        assert isinstance(controller, SecureRBACController)
    
    def test_system_integration(self, system):
        """Test that the system components work together."""
        # Test that the system is enabled by default
        assert system.enabled is True
        
        # Test statistics are available
        stats = system.get_security_statistics()
        assert isinstance(stats, dict)
        assert "total_checks" in stats
    
    def test_controller_integration(self, controller):
        """Test that the controller integrates with bypass prevention."""
        # Test that bypass prevention system is available
        assert controller.bypass_prevention is not None
        
        # Test security configuration
        assert isinstance(controller.security_config, dict)
        assert "strict_validation" in controller.security_config


# Property-based tests for comprehensive validation
class TestPermissionBypassPreventionProperties:
    """Property-based tests for permission bypass prevention."""
    
    @pytest.fixture
    def system(self):
        return PermissionBypassPrevention()
    
    def test_property_no_bypass_for_blocked_users(self, system):
        """
        Property: Blocked users should never be granted permissions.
        
        **Validates: Requirements 3.3 - Permission Control No Bypass**
        
        For any blocked user, all permission checks should return False.
        """
        # Block a user
        user_id = uuid4()
        system.enforcer._block_user_temporarily(user_id, hours=1)
        
        # Create security context
        context = SecurityContext(
            user_id=user_id,
            tenant_id="test-tenant",
            ip_address="192.168.1.100"
        )
        
        # Mock database
        mock_db = Mock()
        
        # Test various permissions
        permissions = ["read_data", "write_data", "admin_access", "manage_users"]
        
        for permission in permissions:
            result, security_info = system.check_permission_with_bypass_prevention(
                context, permission, None, None, mock_db
            )
            
            # Blocked users should never get permissions
            assert result is False
            assert security_info["blocked"] is True
    
    def test_property_tenant_isolation_enforcement(self, system):
        """
        Property: Cross-tenant access should always be blocked.
        
        **Validates: Requirements 3.3 - Permission Control No Bypass**
        
        For any user attempting to access resources from a different tenant,
        the request should be blocked.
        """
        user_id = uuid4()
        
        # Create contexts for different tenants
        user_tenant = "tenant-a"
        target_tenant = "tenant-b"
        
        context = SecurityContext(
            user_id=user_id,
            tenant_id=target_tenant,  # Different from user's actual tenant
            ip_address="192.168.1.100"
        )
        
        # Mock user in different tenant
        mock_user = Mock(spec=UserModel)
        mock_user.id = user_id
        mock_user.tenant_id = user_tenant  # User's actual tenant
        mock_user.is_active = True
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result, security_info = system.check_permission_with_bypass_prevention(
            context, "read_data", None, None, mock_db
        )
        
        # Cross-tenant access should be blocked
        assert result is False
        assert not security_info.get("validation_passed", True)
    
    def test_property_admin_permissions_require_admin_role(self, system):
        """
        Property: Admin permissions should only be granted to admin users.
        
        **Validates: Requirements 3.3 - Permission Control No Bypass**
        
        For any non-admin user requesting admin permissions,
        the request should be blocked.
        """
        user_id = uuid4()
        
        context = SecurityContext(
            user_id=user_id,
            tenant_id="test-tenant",
            ip_address="192.168.1.100"
        )
        
        # Mock non-admin user
        mock_user = Mock(spec=UserModel)
        mock_user.id = user_id
        mock_user.tenant_id = "test-tenant"
        mock_user.is_active = True
        mock_user.role = UserRole.BUSINESS_EXPERT  # Non-admin role
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Test admin permissions
        admin_permissions = ["manage_users", "manage_roles", "system_admin"]
        
        for permission in admin_permissions:
            result, security_info = system.check_permission_with_bypass_prevention(
                context, permission, None, None, mock_db
            )
            
            # Non-admin users should not get admin permissions
            assert result is False
            
            # Should detect privilege escalation attempt or validation failure
            bypass_attempts = security_info.get("bypass_attempts", [])
            validation_passed = security_info.get("validation_passed", True)
            
            # Either bypass attempt detected OR validation failed
            privilege_escalation_detected = any(
                attempt["type"] == BypassAttemptType.PRIVILEGE_ESCALATION.value
                for attempt in bypass_attempts
            )
            
            assert privilege_escalation_detected or not validation_passed
    
    def test_property_inactive_users_denied_access(self, system):
        """
        Property: Inactive users should be denied all access.
        
        **Validates: Requirements 3.3 - Permission Control No Bypass**
        
        For any inactive user, all permission checks should return False.
        """
        user_id = uuid4()
        
        context = SecurityContext(
            user_id=user_id,
            tenant_id="test-tenant",
            ip_address="192.168.1.100"
        )
        
        # Mock inactive user
        mock_user = Mock(spec=UserModel)
        mock_user.id = user_id
        mock_user.tenant_id = "test-tenant"
        mock_user.is_active = False  # Inactive user
        mock_user.role = UserRole.BUSINESS_EXPERT
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Test various permissions
        permissions = ["read_data", "write_data", "view_reports"]
        
        for permission in permissions:
            result, security_info = system.check_permission_with_bypass_prevention(
                context, permission, None, None, mock_db
            )
            
            # Inactive users should be denied access
            assert result is False
            assert not security_info.get("validation_passed", True)
    
    def test_property_brute_force_detection_and_blocking(self, system):
        """
        Property: Repeated failed attempts should trigger blocking.
        
        **Validates: Requirements 3.3 - Permission Control No Bypass**
        
        For any user making repeated failed permission attempts,
        the system should detect and block further attempts.
        """
        user_id = uuid4()
        
        context = SecurityContext(
            user_id=user_id,
            tenant_id="test-tenant",
            ip_address="192.168.1.100"
        )
        
        # Mock user
        mock_user = Mock(spec=UserModel)
        mock_user.id = user_id
        mock_user.tenant_id = "test-tenant"
        mock_user.is_active = True
        mock_user.role = UserRole.BUSINESS_EXPERT
        
        mock_db = Mock()
        # Mock user query to return the mock user, permission query to return None
        def mock_query_side_effect(model_class):
            mock_query = Mock()
            if model_class == UserModel:
                mock_query.filter.return_value.first.return_value = mock_user
            else:  # PermissionModel or other models
                mock_query.filter.return_value.first.return_value = None
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Simulate multiple failed attempts by requesting nonexistent permission
        brute_force_detected = False
        user_blocked = False
        
        for i in range(15):  # More than the threshold
            result, security_info = system.check_permission_with_bypass_prevention(
                context, "nonexistent_permission", None, None, mock_db
            )
            
            # Check if brute force is detected
            bypass_attempts = security_info.get("bypass_attempts", [])
            if any(attempt["type"] == BypassAttemptType.BRUTE_FORCE_PERMISSIONS.value for attempt in bypass_attempts):
                brute_force_detected = True
            
            # Check if user gets blocked
            if security_info.get("enforcement_actions", {}).get("blocked", False):
                user_blocked = True
                break
            
            # Check if user is blocked in subsequent requests
            if security_info.get("blocked", False):
                user_blocked = True
                break
        
        # Should have detected brute force OR blocked the user
        assert brute_force_detected or user_blocked, "Brute force should be detected or user should be blocked"