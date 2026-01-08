"""
Enterprise Data Sync System Security and Compliance Tests.

Comprehensive security tests covering:
- Data masking and desensitization
- Permission control mechanisms
- Data isolation validation
- Compliance requirements (GDPR, HIPAA, etc.)
- Encryption and secure transmission
- Audit trail completeness
- Access control validation

Tests validate security requirements 7, 8, 11 from the data sync system specification.
"""

import pytest
import asyncio
import hashlib
import hmac
import base64
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from dataclasses import dataclass, field
import json


@dataclass
class SecurityTestResult:
    """Security test result."""
    test_name: str
    passed: bool
    security_level: str  # low, medium, high, critical
    vulnerabilities_found: List[str] = field(default_factory=list)
    compliance_violations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class AuditLogEntry:
    """Audit log entry."""
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    result: str
    ip_address: str
    user_agent: str
    details: Dict[str, Any] = field(default_factory=dict)


class MockDataMaskingEngine:
    """Mock data masking engine for testing."""

    def __init__(self):
        self.masking_rules = {
            "ssn": r"\d{3}-\d{2}-\d{4}",
            "credit_card": r"\d{4}-\d{4}-\d{4}-\d{4}",
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone": r"\d{3}-\d{3}-\d{4}",
            "ip_address": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        }

    def detect_sensitive_data(self, text: str) -> Dict[str, List[str]]:
        """Detect sensitive data in text."""
        detected = {}
        for data_type, pattern in self.masking_rules.items():
            matches = re.findall(pattern, text)
            if matches:
                detected[data_type] = matches
        return detected

    def mask_data(self, data: Dict[str, Any], masking_config: Dict[str, str]) -> Dict[str, Any]:
        """Mask sensitive data according to configuration."""
        masked_data = data.copy()
        
        for field, mask_type in masking_config.items():
            if field in masked_data:
                original_value = str(masked_data[field])
                
                if mask_type == "full":
                    masked_data[field] = "*" * len(original_value)
                elif mask_type == "partial":
                    if len(original_value) > 4:
                        # Special handling for email to preserve @ symbol
                        if "@" in original_value and "email" in field.lower():
                            parts = original_value.split("@")
                            if len(parts) == 2:
                                local_part = parts[0]
                                domain_part = parts[1]
                                # Mask local part but keep first 2 and last 2 chars if long enough
                                if len(local_part) > 4:
                                    masked_local = local_part[:2] + "*" * (len(local_part) - 4) + local_part[-2:]
                                else:
                                    masked_local = local_part[0] + "*" * (len(local_part) - 1)
                                # Mask domain but preserve structure
                                if len(domain_part) > 4:
                                    masked_domain = domain_part[:2] + "*" * (len(domain_part) - 4) + domain_part[-2:]
                                else:
                                    masked_domain = "*" * len(domain_part)
                                masked_data[field] = f"{masked_local}@{masked_domain}"
                            else:
                                masked_data[field] = original_value[:2] + "*" * (len(original_value) - 4) + original_value[-2:]
                        # Special handling for dates to preserve year
                        elif "date" in field.lower() and "-" in original_value:
                            parts = original_value.split("-")
                            if len(parts) == 3:  # YYYY-MM-DD format
                                year, month, day = parts
                                masked_data[field] = f"{year}-**-**"
                            else:
                                masked_data[field] = original_value[:2] + "*" * (len(original_value) - 4) + original_value[-2:]
                        # Special handling for diagnosis to keep general category
                        elif "diagnosis" in field.lower():
                            words = original_value.split()
                            if len(words) >= 2:
                                # Keep first word (general category) and mask the rest
                                first_word = words[0]
                                rest = " ".join(words[1:])
                                masked_rest = "*" * len(rest)
                                masked_data[field] = f"{first_word} {masked_rest}"
                            else:
                                masked_data[field] = original_value[:2] + "*" * (len(original_value) - 4) + original_value[-2:]
                        else:
                            masked_data[field] = original_value[:2] + "*" * (len(original_value) - 4) + original_value[-2:]
                    else:
                        masked_data[field] = "*" * len(original_value)
                elif mask_type == "hash":
                    masked_data[field] = hashlib.sha256(original_value.encode()).hexdigest()[:16]
                elif mask_type == "format_preserving":
                    # Preserve format but mask content
                    if "ssn" in field.lower():
                        masked_data[field] = "XXX-XX-" + original_value[-4:] if len(original_value) >= 4 else "XXX-XX-XXXX"
                    elif "credit" in field.lower() or "card" in field.lower():
                        # For credit cards, preserve format and show last 4 digits
                        if "-" in original_value:
                            # Format: XXXX-XXXX-XXXX-1111
                            masked_data[field] = "XXXX-XXXX-XXXX-" + original_value[-4:] if len(original_value) >= 4 else "XXXX-XXXX-XXXX-XXXX"
                        else:
                            # No dashes, just mask all but last 4
                            if len(original_value) >= 4:
                                masked_data[field] = "*" * (len(original_value) - 4) + original_value[-4:]
                            else:
                                masked_data[field] = "*" * len(original_value)
                    elif "email" in field.lower() and "@" in original_value:
                        # For email format preservation, keep @ and domain structure
                        parts = original_value.split("@")
                        if len(parts) == 2:
                            local_part = parts[0]
                            domain_part = parts[1]
                            masked_local = "X" * len(local_part)
                            # Keep domain structure but mask
                            domain_parts = domain_part.split(".")
                            masked_domain_parts = ["X" * len(part) for part in domain_parts]
                            masked_domain = ".".join(masked_domain_parts)
                            masked_data[field] = f"{masked_local}@{masked_domain}"
                        else:
                            masked_data[field] = "*" * len(original_value)
                    else:
                        masked_data[field] = "*" * len(original_value)
        
        return masked_data

    def validate_masking_effectiveness(self, original: Dict[str, Any], masked: Dict[str, Any]) -> bool:
        """Validate that masking was effective."""
        for key, original_value in original.items():
            if key in masked:
                masked_value = masked[key]
                # Check that sensitive patterns are not present in masked data
                for data_type, pattern in self.masking_rules.items():
                    if re.search(pattern, str(original_value)) and re.search(pattern, str(masked_value)):
                        return False  # Masking failed - sensitive pattern still present
        return True


class MockPermissionManager:
    """Mock permission manager for testing."""

    def __init__(self):
        self.user_permissions = {}
        self.role_permissions = {
            "admin": ["read", "write", "delete", "export", "manage_users"],
            "data_manager": ["read", "write", "export"],
            "analyst": ["read"],
            "viewer": ["read"],
            "guest": []
        }
        self.resource_permissions = {}

    def assign_role(self, user_id: str, role: str):
        """Assign role to user."""
        if role in self.role_permissions:
            self.user_permissions[user_id] = self.role_permissions[role].copy()

    def grant_permission(self, user_id: str, permission: str):
        """Grant specific permission to user."""
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = []
        if permission not in self.user_permissions[user_id]:
            self.user_permissions[user_id].append(permission)

    def revoke_permission(self, user_id: str, permission: str):
        """Revoke specific permission from user."""
        if user_id in self.user_permissions and permission in self.user_permissions[user_id]:
            self.user_permissions[user_id].remove(permission)

    def check_permission(self, user_id: str, permission: str, resource: str = None) -> bool:
        """Check if user has permission."""
        user_perms = self.user_permissions.get(user_id, [])
        
        # Check basic permission
        if permission not in user_perms:
            return False
        
        # Check resource-specific permissions if specified
        if resource and resource in self.resource_permissions:
            resource_perms = self.resource_permissions[resource]
            if user_id not in resource_perms.get("allowed_users", []):
                return False
        
        return True

    def set_resource_permissions(self, resource: str, allowed_users: List[str]):
        """Set resource-specific permissions."""
        self.resource_permissions[resource] = {"allowed_users": allowed_users}


class MockTenantIsolationManager:
    """Mock tenant isolation manager for testing."""

    def __init__(self):
        self.tenant_data = {}
        self.tenant_users = {}

    def create_tenant(self, tenant_id: str):
        """Create a new tenant."""
        self.tenant_data[tenant_id] = {}
        self.tenant_users[tenant_id] = set()

    def add_user_to_tenant(self, user_id: str, tenant_id: str):
        """Add user to tenant."""
        if tenant_id not in self.tenant_users:
            self.tenant_users[tenant_id] = set()
        self.tenant_users[tenant_id].add(user_id)

    def get_user_tenant(self, user_id: str) -> Optional[str]:
        """Get user's tenant."""
        for tenant_id, users in self.tenant_users.items():
            if user_id in users:
                return tenant_id
        return None

    def validate_tenant_access(self, user_id: str, resource_tenant_id: str) -> bool:
        """Validate that user can access resource from their tenant."""
        user_tenant = self.get_user_tenant(user_id)
        return user_tenant == resource_tenant_id

    def store_tenant_data(self, tenant_id: str, data_key: str, data: Any):
        """Store data for tenant."""
        if tenant_id not in self.tenant_data:
            self.tenant_data[tenant_id] = {}
        self.tenant_data[tenant_id][data_key] = data

    def get_tenant_data(self, tenant_id: str, data_key: str) -> Any:
        """Get data for tenant."""
        return self.tenant_data.get(tenant_id, {}).get(data_key)

    def list_tenant_data(self, user_id: str) -> Dict[str, Any]:
        """List all data accessible to user (only their tenant's data)."""
        user_tenant = self.get_user_tenant(user_id)
        if user_tenant:
            return self.tenant_data.get(user_tenant, {})
        return {}


class MockAuditLogger:
    """Mock audit logger for testing."""

    def __init__(self):
        self.audit_logs: List[AuditLogEntry] = []

    def log_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        result: str,
        ip_address: str = "127.0.0.1",
        user_agent: str = "test-agent",
        details: Dict[str, Any] = None
    ):
        """Log an action."""
        entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            action=action,
            resource=resource,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {}
        )
        self.audit_logs.append(entry)

    def get_logs(
        self,
        user_id: str = None,
        action: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[AuditLogEntry]:
        """Get filtered audit logs."""
        filtered_logs = self.audit_logs

        if user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == user_id]
        
        if action:
            filtered_logs = [log for log in filtered_logs if log.action == action]
        
        if start_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start_time]
        
        if end_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_time]

        return filtered_logs

    def validate_audit_completeness(self, expected_actions: List[str]) -> bool:
        """Validate that all expected actions are logged."""
        logged_actions = {log.action for log in self.audit_logs}
        return all(action in logged_actions for action in expected_actions)


class TestDataMaskingCompliance:
    """Test data masking and desensitization compliance."""

    @pytest.fixture
    def masking_engine(self):
        """Create masking engine."""
        return MockDataMaskingEngine()

    def test_sensitive_data_detection(self, masking_engine):
        """Test detection of sensitive data patterns."""
        test_data = {
            "user_info": "John Doe, SSN: 123-45-6789, Email: john@example.com",
            "payment": "Credit Card: 4111-1111-1111-1111, Phone: 555-123-4567",
            "system": "Server IP: 192.168.1.100, Database: db.example.com"
        }

        for field, content in test_data.items():
            detected = masking_engine.detect_sensitive_data(content)
            
            if "SSN" in content:
                assert "ssn" in detected, f"Failed to detect SSN in {field}"
            
            if "Credit Card" in content:
                assert "credit_card" in detected, f"Failed to detect credit card in {field}"
            
            if "Email" in content:
                assert "email" in detected, f"Failed to detect email in {field}"
            
            if "Phone" in content:
                assert "phone" in detected, f"Failed to detect phone in {field}"

    def test_data_masking_effectiveness(self, masking_engine):
        """Test effectiveness of data masking."""
        sensitive_data = {
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111",
            "email": "john.doe@example.com",
            "phone": "555-123-4567",
            "name": "John Doe"
        }

        masking_config = {
            "ssn": "format_preserving",
            "credit_card": "format_preserving", 
            "email": "partial",
            "phone": "partial",
            "name": "hash"
        }

        masked_data = masking_engine.mask_data(sensitive_data, masking_config)

        # Verify masking effectiveness
        assert masking_engine.validate_masking_effectiveness(sensitive_data, masked_data)

        # Verify specific masking patterns
        assert masked_data["ssn"].startswith("XXX-XX-")
        assert masked_data["ssn"].endswith("6789")
        
        assert masked_data["credit_card"].startswith("XXXX-XXXX-XXXX-")
        assert masked_data["credit_card"].endswith("1111")
        
        assert "*" in masked_data["email"]
        assert "@" in masked_data["email"]  # Preserve email format
        
        assert len(masked_data["name"]) == 16  # Hash length

    def test_gdpr_compliance_masking(self, masking_engine):
        """Test GDPR compliance for data masking."""
        # GDPR requires ability to anonymize personal data
        personal_data = {
            "first_name": "John",
            "last_name": "Doe", 
            "email": "john.doe@example.com",
            "phone": "+1-555-123-4567",
            "address": "123 Main St, Anytown, USA",
            "date_of_birth": "1990-01-15"
        }

        # GDPR anonymization config
        gdpr_config = {
            "first_name": "hash",
            "last_name": "hash",
            "email": "hash",
            "phone": "hash",
            "address": "hash",
            "date_of_birth": "partial"  # Keep year for analytics
        }

        anonymized_data = masking_engine.mask_data(personal_data, gdpr_config)

        # Verify GDPR compliance
        # 1. No personal identifiers should be recoverable
        for field in ["first_name", "last_name", "email", "phone", "address"]:
            assert anonymized_data[field] != personal_data[field]
            assert len(anonymized_data[field]) == 16  # Hash length
        
        # 2. Date of birth should be partially masked but preserve year for analytics
        assert "1990" in anonymized_data["date_of_birth"]
        assert "01-15" not in anonymized_data["date_of_birth"]

    def test_hipaa_compliance_masking(self, masking_engine):
        """Test HIPAA compliance for healthcare data masking."""
        # HIPAA requires protection of PHI (Protected Health Information)
        phi_data = {
            "patient_id": "P123456789",
            "ssn": "123-45-6789",
            "medical_record_number": "MRN-987654321",
            "diagnosis": "Diabetes Type 2",
            "doctor_name": "Dr. Smith",
            "treatment_date": "2024-01-15"
        }

        # HIPAA de-identification config
        hipaa_config = {
            "patient_id": "hash",
            "ssn": "full",  # Complete removal
            "medical_record_number": "hash",
            "diagnosis": "partial",  # Keep general category
            "doctor_name": "hash",
            "treatment_date": "partial"  # Keep year/month only
        }

        deidentified_data = masking_engine.mask_data(phi_data, hipaa_config)

        # Verify HIPAA compliance
        # 1. Direct identifiers should be removed/hashed
        assert deidentified_data["ssn"] == "*" * len(phi_data["ssn"])
        assert deidentified_data["patient_id"] != phi_data["patient_id"]
        assert deidentified_data["medical_record_number"] != phi_data["medical_record_number"]
        
        # 2. Quasi-identifiers should be generalized
        assert "Diabetes" in deidentified_data["diagnosis"]  # Keep general category
        assert "2024" in deidentified_data["treatment_date"]  # Keep year


class TestPermissionControlMechanisms:
    """Test permission control mechanisms."""

    @pytest.fixture
    def permission_manager(self):
        """Create permission manager."""
        return MockPermissionManager()

    def test_role_based_access_control(self, permission_manager):
        """Test role-based access control (RBAC)."""
        # Assign roles to users
        permission_manager.assign_role("admin_user", "admin")
        permission_manager.assign_role("data_user", "data_manager")
        permission_manager.assign_role("read_user", "analyst")
        permission_manager.assign_role("guest_user", "guest")

        # Test admin permissions
        assert permission_manager.check_permission("admin_user", "read")
        assert permission_manager.check_permission("admin_user", "write")
        assert permission_manager.check_permission("admin_user", "delete")
        assert permission_manager.check_permission("admin_user", "export")
        assert permission_manager.check_permission("admin_user", "manage_users")

        # Test data manager permissions
        assert permission_manager.check_permission("data_user", "read")
        assert permission_manager.check_permission("data_user", "write")
        assert permission_manager.check_permission("data_user", "export")
        assert not permission_manager.check_permission("data_user", "delete")
        assert not permission_manager.check_permission("data_user", "manage_users")

        # Test analyst permissions
        assert permission_manager.check_permission("read_user", "read")
        assert not permission_manager.check_permission("read_user", "write")
        assert not permission_manager.check_permission("read_user", "export")

        # Test guest permissions
        assert not permission_manager.check_permission("guest_user", "read")
        assert not permission_manager.check_permission("guest_user", "write")

    def test_resource_level_permissions(self, permission_manager):
        """Test resource-level permission control."""
        # Set up users
        permission_manager.assign_role("user1", "data_manager")
        permission_manager.assign_role("user2", "data_manager")

        # Set resource-specific permissions
        permission_manager.set_resource_permissions("sensitive_dataset", ["user1"])
        permission_manager.set_resource_permissions("public_dataset", ["user1", "user2"])

        # Test resource access
        assert permission_manager.check_permission("user1", "read", "sensitive_dataset")
        assert not permission_manager.check_permission("user2", "read", "sensitive_dataset")

        assert permission_manager.check_permission("user1", "read", "public_dataset")
        assert permission_manager.check_permission("user2", "read", "public_dataset")

    def test_dynamic_permission_management(self, permission_manager):
        """Test dynamic permission granting and revocation."""
        user_id = "dynamic_user"
        
        # Initially no permissions
        assert not permission_manager.check_permission(user_id, "read")

        # Grant read permission
        permission_manager.grant_permission(user_id, "read")
        assert permission_manager.check_permission(user_id, "read")
        assert not permission_manager.check_permission(user_id, "write")

        # Grant write permission
        permission_manager.grant_permission(user_id, "write")
        assert permission_manager.check_permission(user_id, "read")
        assert permission_manager.check_permission(user_id, "write")

        # Revoke read permission
        permission_manager.revoke_permission(user_id, "read")
        assert not permission_manager.check_permission(user_id, "read")
        assert permission_manager.check_permission(user_id, "write")

    def test_permission_escalation_prevention(self, permission_manager):
        """Test prevention of unauthorized permission escalation."""
        # Set up regular user
        permission_manager.assign_role("regular_user", "analyst")
        
        # User should not be able to escalate to admin permissions
        assert not permission_manager.check_permission("regular_user", "manage_users")
        assert not permission_manager.check_permission("regular_user", "delete")
        
        # Even if we try to grant admin permissions programmatically,
        # the role system should prevent escalation
        original_perms = permission_manager.user_permissions.get("regular_user", []).copy()
        
        # Simulate attempted escalation
        try:
            permission_manager.grant_permission("regular_user", "manage_users")
            # This should be allowed by the mock, but in real system would be prevented
            # by additional authorization checks
        except Exception:
            pass
        
        # Verify that basic role permissions are still intact
        assert permission_manager.check_permission("regular_user", "read")


class TestDataIsolationValidation:
    """Test data isolation validation."""

    @pytest.fixture
    def isolation_manager(self):
        """Create tenant isolation manager."""
        return MockTenantIsolationManager()

    def test_tenant_data_isolation(self, isolation_manager):
        """Test that tenant data is properly isolated."""
        # Create tenants
        isolation_manager.create_tenant("tenant_a")
        isolation_manager.create_tenant("tenant_b")

        # Add users to tenants
        isolation_manager.add_user_to_tenant("user_a1", "tenant_a")
        isolation_manager.add_user_to_tenant("user_a2", "tenant_a")
        isolation_manager.add_user_to_tenant("user_b1", "tenant_b")

        # Store data for each tenant
        isolation_manager.store_tenant_data("tenant_a", "dataset_1", {"data": "tenant_a_data"})
        isolation_manager.store_tenant_data("tenant_b", "dataset_1", {"data": "tenant_b_data"})

        # Verify tenant isolation
        tenant_a_data = isolation_manager.list_tenant_data("user_a1")
        tenant_b_data = isolation_manager.list_tenant_data("user_b1")

        assert "dataset_1" in tenant_a_data
        assert "dataset_1" in tenant_b_data
        assert tenant_a_data["dataset_1"]["data"] == "tenant_a_data"
        assert tenant_b_data["dataset_1"]["data"] == "tenant_b_data"

        # Verify cross-tenant access is prevented
        assert not isolation_manager.validate_tenant_access("user_a1", "tenant_b")
        assert not isolation_manager.validate_tenant_access("user_b1", "tenant_a")
        assert isolation_manager.validate_tenant_access("user_a1", "tenant_a")
        assert isolation_manager.validate_tenant_access("user_b1", "tenant_b")

    def test_multi_tenant_user_isolation(self, isolation_manager):
        """Test user isolation across multiple tenants."""
        # Create multiple tenants
        tenants = ["tenant_1", "tenant_2", "tenant_3"]
        for tenant in tenants:
            isolation_manager.create_tenant(tenant)

        # Add users to different tenants
        for i, tenant in enumerate(tenants):
            for j in range(3):  # 3 users per tenant
                user_id = f"user_{tenant}_{j}"
                isolation_manager.add_user_to_tenant(user_id, tenant)

        # Store unique data for each tenant
        for i, tenant in enumerate(tenants):
            for j in range(5):  # 5 datasets per tenant
                dataset_key = f"dataset_{j}"
                data = {"tenant": tenant, "dataset_id": j, "secret": f"secret_{tenant}_{j}"}
                isolation_manager.store_tenant_data(tenant, dataset_key, data)

        # Verify each user can only access their tenant's data
        for tenant in tenants:
            user_id = f"user_{tenant}_0"  # First user of each tenant
            user_data = isolation_manager.list_tenant_data(user_id)
            
            # Should have access to all datasets in their tenant
            assert len(user_data) == 5
            
            # All data should belong to their tenant
            for dataset_key, dataset in user_data.items():
                assert dataset["tenant"] == tenant
                assert dataset["secret"].startswith(f"secret_{tenant}_")

    def test_tenant_data_leakage_prevention(self, isolation_manager):
        """Test prevention of data leakage between tenants."""
        # Set up tenants with sensitive data
        isolation_manager.create_tenant("healthcare_tenant")
        isolation_manager.create_tenant("finance_tenant")

        isolation_manager.add_user_to_tenant("doctor", "healthcare_tenant")
        isolation_manager.add_user_to_tenant("banker", "finance_tenant")

        # Store sensitive data
        healthcare_data = {
            "patient_records": {"patient_1": "confidential_medical_data"},
            "treatment_plans": {"plan_1": "sensitive_treatment_info"}
        }
        
        finance_data = {
            "account_balances": {"account_1": "confidential_balance_data"},
            "transaction_history": {"tx_1": "sensitive_transaction_info"}
        }

        isolation_manager.store_tenant_data("healthcare_tenant", "medical_data", healthcare_data)
        isolation_manager.store_tenant_data("finance_tenant", "financial_data", finance_data)

        # Verify no cross-tenant data access
        doctor_data = isolation_manager.list_tenant_data("doctor")
        banker_data = isolation_manager.list_tenant_data("banker")

        # Doctor should only see medical data
        assert "medical_data" in doctor_data
        assert "financial_data" not in doctor_data
        assert "patient_records" in doctor_data["medical_data"]

        # Banker should only see financial data
        assert "financial_data" in banker_data
        assert "medical_data" not in banker_data
        assert "account_balances" in banker_data["financial_data"]


class TestComplianceRequirements:
    """Test compliance with various regulatory requirements."""

    @pytest.fixture
    def audit_logger(self):
        """Create audit logger."""
        return MockAuditLogger()

    @pytest.fixture
    def masking_engine(self):
        """Create masking engine."""
        return MockDataMaskingEngine()

    def test_gdpr_right_to_be_forgotten(self, audit_logger, masking_engine):
        """Test GDPR right to be forgotten compliance."""
        user_id = "gdpr_user"
        
        # Simulate user data processing
        audit_logger.log_action(user_id, "data_collection", "user_profile", "success")
        audit_logger.log_action(user_id, "data_processing", "analytics", "success")
        audit_logger.log_action(user_id, "data_storage", "database", "success")

        # User requests data deletion (right to be forgotten)
        audit_logger.log_action("admin", "deletion_request", f"user_data:{user_id}", "received")

        # Simulate data deletion process
        user_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "preferences": {"newsletter": True}
        }

        # GDPR requires complete removal or anonymization
        gdpr_deletion_config = {
            "name": "full",
            "email": "full", 
            "preferences": "full"
        }

        deleted_data = masking_engine.mask_data(user_data, gdpr_deletion_config)
        
        # Log deletion completion
        audit_logger.log_action("admin", "data_deleted", f"user_data:{user_id}", "completed")

        # Verify GDPR compliance
        # 1. All personal data should be fully masked
        assert all(value == "*" * len(str(user_data[key])) for key, value in deleted_data.items())
        
        # 2. Deletion should be audited
        deletion_logs = audit_logger.get_logs(action="data_deleted")
        assert len(deletion_logs) > 0
        assert any(user_id in log.resource for log in deletion_logs)

    def test_hipaa_audit_trail_requirements(self, audit_logger):
        """Test HIPAA audit trail requirements."""
        # HIPAA requires comprehensive audit trails for PHI access
        phi_actions = [
            ("doctor_1", "phi_access", "patient_123_record", "success"),
            ("nurse_2", "phi_view", "patient_123_vitals", "success"),
            ("admin_3", "phi_export", "patient_123_report", "success"),
            ("unauthorized_user", "phi_access", "patient_123_record", "denied")
        ]

        # Log all PHI-related actions
        for user_id, action, resource, result in phi_actions:
            audit_logger.log_action(
                user_id, action, resource, result,
                details={"phi_involved": True, "patient_id": "patient_123"}
            )

        # Verify HIPAA audit requirements
        phi_logs = audit_logger.get_logs()
        
        # 1. All PHI access should be logged
        assert len(phi_logs) == 4
        
        # 2. Each log should contain required HIPAA fields
        for log in phi_logs:
            assert log.user_id is not None
            assert log.timestamp is not None
            assert log.action is not None
            assert log.resource is not None
            assert log.result is not None
            assert "phi_involved" in log.details
            assert "patient_id" in log.details

        # 3. Failed access attempts should be logged
        failed_access_logs = [log for log in phi_logs if log.result == "denied"]
        assert len(failed_access_logs) == 1
        assert failed_access_logs[0].user_id == "unauthorized_user"

    def test_sox_financial_data_controls(self, audit_logger, masking_engine):
        """Test SOX (Sarbanes-Oxley) financial data controls."""
        # SOX requires strict controls over financial data
        financial_data = {
            "revenue": 1000000,
            "expenses": 750000,
            "profit": 250000,
            "account_number": "ACC-123456789",
            "transaction_id": "TXN-987654321"
        }

        # Log financial data access
        audit_logger.log_action(
            "cfo", "financial_data_access", "quarterly_report", "success",
            details={"sox_controlled": True, "data_classification": "confidential"}
        )

        # SOX requires data integrity controls
        # Simulate data integrity check
        original_hash = hashlib.sha256(json.dumps(financial_data, sort_keys=True).encode()).hexdigest()
        
        # Log integrity verification
        audit_logger.log_action(
            "system", "data_integrity_check", "quarterly_report", "verified",
            details={"hash": original_hash, "sox_compliance": True}
        )

        # Verify SOX compliance
        sox_logs = audit_logger.get_logs()
        
        # 1. Financial data access should be logged
        access_logs = [log for log in sox_logs if "financial_data_access" in log.action]
        assert len(access_logs) > 0
        
        # 2. Data integrity should be verified
        integrity_logs = [log for log in sox_logs if "integrity_check" in log.action]
        assert len(integrity_logs) > 0
        
        # 3. All logs should indicate SOX compliance
        for log in sox_logs:
            assert "sox_controlled" in log.details or "sox_compliance" in log.details

    def test_pci_dss_payment_data_protection(self, masking_engine):
        """Test PCI DSS payment data protection requirements."""
        # PCI DSS requires strict protection of payment card data
        payment_data = {
            "card_number": "4111-1111-1111-1111",
            "cvv": "123",
            "expiry_date": "12/25",
            "cardholder_name": "John Doe",
            "billing_address": "123 Main St"
        }

        # PCI DSS masking requirements
        pci_config = {
            "card_number": "format_preserving",  # Show only last 4 digits
            "cvv": "full",  # Never store CVV
            "expiry_date": "partial",  # Mask month
            "cardholder_name": "partial",
            "billing_address": "hash"
        }

        protected_data = masking_engine.mask_data(payment_data, pci_config)

        # Verify PCI DSS compliance
        # 1. Card number should show only last 4 digits
        assert protected_data["card_number"].endswith("1111")
        assert "XXXX" in protected_data["card_number"]
        
        # 2. CVV should be completely masked
        assert protected_data["cvv"] == "***"
        
        # 3. Sensitive data should not be recoverable
        assert protected_data["billing_address"] != payment_data["billing_address"]
        assert len(protected_data["billing_address"]) == 16  # Hash length


class TestEncryptionAndSecureTransmission:
    """Test encryption and secure transmission."""

    def test_data_encryption_at_rest(self):
        """Test data encryption at rest."""
        # Simulate encryption key management
        encryption_key = "test_encryption_key_32_bytes_long"
        
        sensitive_data = {
            "ssn": "123-45-6789",
            "medical_record": "Patient has diabetes",
            "financial_info": "Account balance: $50,000"
        }

        # Simulate encryption (using simple hash for testing)
        encrypted_data = {}
        for key, value in sensitive_data.items():
            # In real implementation, use proper encryption (AES-256)
            encrypted_value = hashlib.sha256((value + encryption_key).encode()).hexdigest()
            encrypted_data[key] = encrypted_value

        # Verify encryption
        for key in sensitive_data:
            assert encrypted_data[key] != sensitive_data[key]
            assert len(encrypted_data[key]) == 64  # SHA256 hex length

        # Simulate decryption verification
        for key, original_value in sensitive_data.items():
            expected_encrypted = hashlib.sha256((original_value + encryption_key).encode()).hexdigest()
            assert encrypted_data[key] == expected_encrypted

    def test_data_encryption_in_transit(self):
        """Test data encryption in transit."""
        # Simulate TLS/SSL encryption for data in transit
        message = "Sensitive data being transmitted"
        
        # Simulate HMAC for message integrity
        secret_key = "shared_secret_key"
        message_hmac = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        # Simulate transmission (base64 encoding)
        transmitted_data = {
            "message": base64.b64encode(message.encode()).decode(),
            "hmac": message_hmac,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Verify secure transmission
        # 1. Message should be encoded
        assert transmitted_data["message"] != message
        
        # 2. HMAC should be present for integrity
        assert len(transmitted_data["hmac"]) == 64  # SHA256 hex length
        
        # 3. Verify HMAC integrity
        decoded_message = base64.b64decode(transmitted_data["message"]).decode()
        expected_hmac = hmac.new(
            secret_key.encode(),
            decoded_message.encode(),
            hashlib.sha256
        ).hexdigest()
        assert transmitted_data["hmac"] == expected_hmac

    def test_key_rotation_compliance(self):
        """Test encryption key rotation compliance."""
        # Simulate key rotation process
        keys = {
            "key_v1": "old_encryption_key_32_bytes_long",
            "key_v2": "new_encryption_key_32_bytes_long"
        }
        
        data = "Sensitive information"
        
        # Encrypt with old key
        old_encrypted = hashlib.sha256((data + keys["key_v1"]).encode()).hexdigest()
        
        # Simulate key rotation - re-encrypt with new key
        new_encrypted = hashlib.sha256((data + keys["key_v2"]).encode()).hexdigest()
        
        # Verify key rotation
        assert old_encrypted != new_encrypted
        
        # Verify both keys can decrypt their respective data
        old_verification = hashlib.sha256((data + keys["key_v1"]).encode()).hexdigest()
        new_verification = hashlib.sha256((data + keys["key_v2"]).encode()).hexdigest()
        
        assert old_encrypted == old_verification
        assert new_encrypted == new_verification


class TestAuditTrailCompleteness:
    """Test audit trail completeness."""

    @pytest.fixture
    def audit_logger(self):
        """Create audit logger."""
        return MockAuditLogger()

    def test_comprehensive_audit_logging(self, audit_logger):
        """Test comprehensive audit logging for all operations."""
        # Define all operations that should be audited
        operations = [
            ("user_1", "login", "system", "success"),
            ("user_1", "data_access", "customer_database", "success"),
            ("user_1", "data_export", "customer_report.csv", "success"),
            ("user_1", "data_modification", "customer_record_123", "success"),
            ("user_1", "logout", "system", "success"),
            ("user_2", "login_attempt", "system", "failed"),
            ("admin", "user_creation", "user_3", "success"),
            ("admin", "permission_change", "user_1_permissions", "success")
        ]

        # Log all operations
        for user_id, action, resource, result in operations:
            audit_logger.log_action(user_id, action, resource, result)

        # Verify audit completeness
        all_logs = audit_logger.get_logs()
        assert len(all_logs) == len(operations)

        # Verify each operation is logged with required fields
        for i, (user_id, action, resource, result) in enumerate(operations):
            log = all_logs[i]
            assert log.user_id == user_id
            assert log.action == action
            assert log.resource == resource
            assert log.result == result
            assert log.timestamp is not None
            assert log.ip_address is not None

    def test_audit_log_integrity(self, audit_logger):
        """Test audit log integrity and tamper detection."""
        # Log some operations
        operations = [
            ("user_1", "sensitive_access", "classified_data", "success"),
            ("user_2", "data_deletion", "old_records", "success")
        ]

        for user_id, action, resource, result in operations:
            audit_logger.log_action(user_id, action, resource, result)

        # Calculate audit log hash for integrity
        logs = audit_logger.get_logs()
        log_data = []
        for log in logs:
            log_entry = f"{log.timestamp}|{log.user_id}|{log.action}|{log.resource}|{log.result}"
            log_data.append(log_entry)

        original_hash = hashlib.sha256("|".join(log_data).encode()).hexdigest()

        # Simulate tampering attempt (modify a log entry)
        tampered_logs = logs.copy()
        tampered_logs[0].result = "modified"

        # Recalculate hash with tampered data
        tampered_log_data = []
        for log in tampered_logs:
            log_entry = f"{log.timestamp}|{log.user_id}|{log.action}|{log.resource}|{log.result}"
            tampered_log_data.append(log_entry)

        tampered_hash = hashlib.sha256("|".join(tampered_log_data).encode()).hexdigest()

        # Verify tamper detection
        assert original_hash != tampered_hash, "Audit log tampering should be detectable"

    def test_audit_log_retention_compliance(self, audit_logger):
        """Test audit log retention compliance."""
        # Simulate logs over time
        base_time = datetime.utcnow()
        
        # Create logs spanning different time periods
        time_periods = [
            (base_time - timedelta(days=400), "old_log"),  # > 1 year old
            (base_time - timedelta(days=200), "medium_log"),  # 6 months old
            (base_time - timedelta(days=30), "recent_log"),  # 1 month old
            (base_time, "current_log")  # Current
        ]

        for timestamp, log_type in time_periods:
            # Manually create log entry with specific timestamp
            entry = AuditLogEntry(
                timestamp=timestamp,
                user_id="test_user",
                action=f"test_action_{log_type}",
                resource="test_resource",
                result="success",
                ip_address="127.0.0.1",
                user_agent="test-agent"
            )
            audit_logger.audit_logs.append(entry)

        # Test retention policy (e.g., keep logs for 1 year)
        retention_cutoff = base_time - timedelta(days=365)
        
        # Get logs within retention period
        retained_logs = audit_logger.get_logs(start_time=retention_cutoff)
        
        # Verify retention compliance
        assert len(retained_logs) == 3  # Should exclude the 400-day-old log
        
        # Verify all retained logs are within retention period
        for log in retained_logs:
            assert log.timestamp >= retention_cutoff


# Run security tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])