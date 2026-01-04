"""
Unit tests for Security Controller health check functionality.

Tests encryption, JWT token operations, and audit logging for health monitoring.
Validates Requirements 3.1, 3.2, 3.3, 3.4, 3.5.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
import jwt
from datetime import datetime, timedelta

from src.security.controller import SecurityController
from src.security.models import AuditAction, AuditLogModel


class TestSecurityControllerEncryptionHealthCheck:
    """Test encryption health check functionality - Requirement 3.1, 3.2, 3.3"""
    
    def setup_method(self):
        """Set up test environment."""
        self.security_controller = SecurityController()
    
    def test_encryption_health_check_success(self):
        """Test that encryption health check returns True when working correctly."""
        # Act
        result = self.security_controller.test_encryption()
        
        # Assert
        assert result is True
    
    def test_encryption_health_check_password_hashing(self):
        """Test that encryption health check verifies password hashing functionality."""
        # Arrange
        test_password = "health_check_test_password_123"
        
        # Act
        # The test_encryption method should hash and verify a password
        result = self.security_controller.test_encryption()
        
        # Assert
        assert result is True
        
        # Verify that hashing actually works by testing it directly
        hashed = self.security_controller.hash_password(test_password)
        assert hashed != test_password
        assert self.security_controller.verify_password(test_password, hashed)
    
    def test_encryption_health_check_rejects_wrong_password(self):
        """Test that encryption health check verifies wrong passwords are rejected."""
        # Arrange
        test_password = "health_check_test_password_123"
        wrong_password = "wrong_password"
        
        # Act
        result = self.security_controller.test_encryption()
        
        # Assert
        assert result is True
        
        # Verify that wrong password verification fails
        hashed = self.security_controller.hash_password(test_password)
        assert not self.security_controller.verify_password(wrong_password, hashed)
    
    def test_encryption_health_check_handles_exception(self):
        """Test that encryption health check handles exceptions gracefully."""
        # Arrange
        controller = SecurityController()
        
        # Mock hash_password to raise an exception
        with patch.object(controller, 'hash_password', side_effect=Exception("Hash error")):
            # Act
            result = controller.test_encryption()
        
        # Assert
        assert result is False
    
    def test_encryption_health_check_detects_empty_hash(self):
        """Test that encryption health check detects when hash is empty."""
        # Arrange
        controller = SecurityController()
        
        # Mock hash_password to return empty string
        with patch.object(controller, 'hash_password', return_value=""):
            # Act
            result = controller.test_encryption()
        
        # Assert
        assert result is False
    
    def test_encryption_health_check_detects_plaintext_hash(self):
        """Test that encryption health check detects when hash equals plaintext."""
        # Arrange
        controller = SecurityController()
        test_password = "test_password"
        
        # Mock hash_password to return the plaintext (bad hashing)
        with patch.object(controller, 'hash_password', return_value=test_password):
            # Act
            result = controller.test_encryption()
        
        # Assert
        assert result is False
    
    def test_encryption_health_check_detects_verify_failure(self):
        """Test that encryption health check detects when verification fails."""
        # Arrange
        controller = SecurityController()
        
        # Mock verify_password to return False
        with patch.object(controller, 'verify_password', return_value=False):
            # Act
            result = controller.test_encryption()
        
        # Assert
        assert result is False
    
    def test_encryption_health_check_detects_wrong_password_accepted(self):
        """Test that encryption health check detects when wrong password is accepted."""
        # Arrange
        controller = SecurityController()
        
        # Mock verify_password to incorrectly accept wrong password
        call_count = [0]
        def verify_side_effect(plain, hashed):
            call_count[0] += 1
            # First call (correct password) returns True, second call (wrong password) also returns True
            return True
        
        with patch.object(controller, 'verify_password', side_effect=verify_side_effect):
            # Act
            result = controller.test_encryption()
        
        # Assert
        assert result is False


class TestSecurityControllerAuthenticationHealthCheck:
    """Test JWT token authentication health check - Requirement 3.4"""
    
    def setup_method(self):
        """Set up test environment."""
        self.security_controller = SecurityController()
    
    def test_authentication_health_check_success(self):
        """Test that authentication health check returns True when working correctly."""
        # Act
        result = self.security_controller.test_authentication()
        
        # Assert
        assert result is True
    
    def test_authentication_health_check_token_generation(self):
        """Test that authentication health check verifies token generation."""
        # Arrange
        test_user_id = "health_check_user"
        test_tenant_id = "health_check_tenant"
        
        # Act
        result = self.security_controller.test_authentication()
        
        # Assert
        assert result is True
        
        # Verify token generation works
        token = self.security_controller.create_access_token(test_user_id, test_tenant_id)
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_authentication_health_check_token_verification(self):
        """Test that authentication health check verifies token verification."""
        # Arrange
        test_user_id = "health_check_user"
        test_tenant_id = "health_check_tenant"
        
        # Act
        result = self.security_controller.test_authentication()
        
        # Assert
        assert result is True
        
        # Verify token verification works
        token = self.security_controller.create_access_token(test_user_id, test_tenant_id)
        payload = self.security_controller.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == test_user_id
        assert payload["tenant_id"] == test_tenant_id
    
    def test_authentication_health_check_payload_contents(self):
        """Test that authentication health check verifies payload contents."""
        # Arrange
        test_user_id = "health_check_user"
        test_tenant_id = "health_check_tenant"
        
        # Act
        result = self.security_controller.test_authentication()
        
        # Assert
        assert result is True
        
        # Verify payload contains correct data
        token = self.security_controller.create_access_token(test_user_id, test_tenant_id)
        payload = self.security_controller.verify_token(token)
        assert payload["user_id"] == test_user_id
        assert payload["tenant_id"] == test_tenant_id
    
    def test_authentication_health_check_handles_token_generation_failure(self):
        """Test that authentication health check handles token generation failure."""
        # Arrange
        controller = SecurityController()
        
        # Mock create_access_token to return None
        with patch.object(controller, 'create_access_token', return_value=None):
            # Act
            result = controller.test_authentication()
        
        # Assert
        assert result is False
    
    def test_authentication_health_check_handles_token_verification_failure(self):
        """Test that authentication health check handles token verification failure."""
        # Arrange
        controller = SecurityController()
        
        # Mock verify_token to return None
        with patch.object(controller, 'verify_token', return_value=None):
            # Act
            result = controller.test_authentication()
        
        # Assert
        assert result is False
    
    def test_authentication_health_check_detects_missing_user_id(self):
        """Test that authentication health check detects missing user_id in payload."""
        # Arrange
        controller = SecurityController()
        
        # Mock verify_token to return payload without user_id
        with patch.object(controller, 'verify_token', return_value={"tenant_id": "test"}):
            # Act
            result = controller.test_authentication()
        
        # Assert
        assert result is False
    
    def test_authentication_health_check_detects_missing_tenant_id(self):
        """Test that authentication health check detects missing tenant_id in payload."""
        # Arrange
        controller = SecurityController()
        
        # Mock verify_token to return payload without tenant_id
        with patch.object(controller, 'verify_token', return_value={"user_id": "test"}):
            # Act
            result = controller.test_authentication()
        
        # Assert
        assert result is False
    
    def test_authentication_health_check_detects_wrong_user_id(self):
        """Test that authentication health check detects wrong user_id in payload."""
        # Arrange
        controller = SecurityController()
        
        # Mock verify_token to return wrong user_id
        with patch.object(controller, 'verify_token', return_value={
            "user_id": "wrong_user",
            "tenant_id": "health_check_tenant"
        }):
            # Act
            result = controller.test_authentication()
        
        # Assert
        assert result is False
    
    def test_authentication_health_check_detects_wrong_tenant_id(self):
        """Test that authentication health check detects wrong tenant_id in payload."""
        # Arrange
        controller = SecurityController()
        
        # Mock verify_token to return wrong tenant_id
        with patch.object(controller, 'verify_token', return_value={
            "user_id": "health_check_user",
            "tenant_id": "wrong_tenant"
        }):
            # Act
            result = controller.test_authentication()
        
        # Assert
        assert result is False
    
    def test_authentication_health_check_handles_exception(self):
        """Test that authentication health check handles exceptions gracefully."""
        # Arrange
        controller = SecurityController()
        
        # Mock create_access_token to raise an exception
        with patch.object(controller, 'create_access_token', side_effect=Exception("Token error")):
            # Act
            result = controller.test_authentication()
        
        # Assert
        assert result is False


class TestSecurityControllerAuditLoggingHealthCheck:
    """Test audit logging health check functionality - Requirement 3.5"""
    
    def setup_method(self):
        """Set up test environment."""
        self.security_controller = SecurityController()
    
    def test_audit_logging_health_check_success(self):
        """Test that audit logging health check returns True when working correctly."""
        # Act
        result = self.security_controller.test_audit_logging()
        
        # Assert
        assert result is True
    
    def test_audit_logging_health_check_verifies_audit_action_enum(self):
        """Test that audit logging health check verifies AuditAction enum is available."""
        # Act
        result = self.security_controller.test_audit_logging()
        
        # Assert
        assert result is True
        
        # Verify AuditAction enum has required attributes
        assert hasattr(AuditAction, 'LOGIN')
        assert hasattr(AuditAction, 'CREATE')
        assert hasattr(AuditAction, 'READ')
        assert hasattr(AuditAction, 'UPDATE')
        assert hasattr(AuditAction, 'DELETE')
    
    def test_audit_logging_health_check_verifies_audit_log_model(self):
        """Test that audit logging health check verifies AuditLogModel is available."""
        # Act
        result = self.security_controller.test_audit_logging()
        
        # Assert
        assert result is True
        
        # Verify AuditLogModel is available
        assert AuditLogModel is not None
    
    def test_audit_logging_health_check_verifies_log_method_exists(self):
        """Test that audit logging health check verifies log_user_action method exists."""
        # Act
        result = self.security_controller.test_audit_logging()
        
        # Assert
        assert result is True
        
        # Verify log_user_action method exists and is callable
        assert callable(getattr(self.security_controller, 'log_user_action', None))
    
    def test_audit_logging_health_check_handles_missing_audit_action(self):
        """Test that audit logging health check handles missing AuditAction enum."""
        # Arrange
        controller = SecurityController()
        
        # Mock AuditAction to not have LOGIN attribute
        with patch('src.security.controller.AuditAction', create=True) as mock_action:
            mock_action.LOGIN = None
            del mock_action.LOGIN  # Remove the attribute
            
            # Act
            result = controller.test_audit_logging()
        
        # Assert
        assert result is False
    
    def test_audit_logging_health_check_handles_missing_audit_log_model(self):
        """Test that audit logging health check handles missing AuditLogModel."""
        # Arrange
        controller = SecurityController()
        
        # Mock AuditLogModel to be None
        with patch('src.security.controller.AuditLogModel', None):
            # Act
            result = controller.test_audit_logging()
        
        # Assert
        assert result is False
    
    def test_audit_logging_health_check_handles_missing_log_method(self):
        """Test that audit logging health check handles missing log_user_action method."""
        # Arrange
        controller = SecurityController()
        
        # Mock getattr to return None for log_user_action
        with patch('builtins.getattr', side_effect=lambda obj, name, default=None: 
                   None if name == 'log_user_action' else getattr(obj, name, default)):
            # Act
            result = controller.test_audit_logging()
        
        # Assert
        assert result is False
    
    def test_audit_logging_health_check_handles_exception(self):
        """Test that audit logging health check handles exceptions gracefully."""
        # Arrange
        controller = SecurityController()
        
        # Mock hasattr to raise an exception
        with patch('builtins.hasattr', side_effect=Exception("Attribute error")):
            # Act
            result = controller.test_audit_logging()
        
        # Assert
        assert result is False


class TestSecurityControllerHealthCheckIntegration:
    """Integration tests for security health checks."""
    
    def setup_method(self):
        """Set up test environment."""
        self.security_controller = SecurityController()
    
    def test_all_health_checks_pass_together(self):
        """Test that all health checks pass when run together."""
        # Act
        encryption_result = self.security_controller.test_encryption()
        authentication_result = self.security_controller.test_authentication()
        audit_logging_result = self.security_controller.test_audit_logging()
        
        # Assert
        assert encryption_result is True
        assert authentication_result is True
        assert audit_logging_result is True
    
    def test_health_checks_are_independent(self):
        """Test that health checks are independent and don't affect each other."""
        # Act - Run checks multiple times
        for _ in range(3):
            encryption_result = self.security_controller.test_encryption()
            authentication_result = self.security_controller.test_authentication()
            audit_logging_result = self.security_controller.test_audit_logging()
            
            # Assert
            assert encryption_result is True
            assert authentication_result is True
            assert audit_logging_result is True
    
    def test_health_checks_with_different_secret_keys(self):
        """Test that health checks work with different secret keys."""
        # Arrange
        controller1 = SecurityController(secret_key="secret_key_1")
        controller2 = SecurityController(secret_key="secret_key_2")
        
        # Act
        result1_encryption = controller1.test_encryption()
        result1_auth = controller1.test_authentication()
        result1_audit = controller1.test_audit_logging()
        
        result2_encryption = controller2.test_encryption()
        result2_auth = controller2.test_authentication()
        result2_audit = controller2.test_audit_logging()
        
        # Assert
        assert result1_encryption is True
        assert result1_auth is True
        assert result1_audit is True
        assert result2_encryption is True
        assert result2_auth is True
        assert result2_audit is True
    
    def test_health_check_consistency_across_calls(self):
        """Test that health checks return consistent results across multiple calls."""
        # Act
        results_encryption = [self.security_controller.test_encryption() for _ in range(5)]
        results_auth = [self.security_controller.test_authentication() for _ in range(5)]
        results_audit = [self.security_controller.test_audit_logging() for _ in range(5)]
        
        # Assert
        assert all(r is True for r in results_encryption)
        assert all(r is True for r in results_auth)
        assert all(r is True for r in results_audit)
    
    def test_health_checks_do_not_modify_state(self):
        """Test that health checks don't modify controller state."""
        # Arrange
        original_secret_key = self.security_controller.secret_key
        original_token_expire = self.security_controller.token_expire_hours
        
        # Act
        self.security_controller.test_encryption()
        self.security_controller.test_authentication()
        self.security_controller.test_audit_logging()
        
        # Assert
        assert self.security_controller.secret_key == original_secret_key
        assert self.security_controller.token_expire_hours == original_token_expire
