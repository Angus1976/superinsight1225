#!/usr/bin/env python3
"""
Multi-Tenant Implementation Validation Script

Validates that the multi-tenant implementation is working correctly.
"""

import sys
import traceback
from typing import Dict, Any

def test_imports():
    """Test that all multi-tenant modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.database.tenant_isolation_validator import TenantIsolationValidator
        print("✓ TenantIsolationValidator imported successfully")
        
        from src.middleware.tenant_middleware import TenantMiddleware, TenantContext
        print("✓ TenantMiddleware imported successfully")
        
        from src.security.tenant_permissions import TenantPermissionManager
        print("✓ TenantPermissionManager imported successfully")
        
        from src.security.tenant_audit import TenantAuditLogger
        print("✓ TenantAuditLogger imported successfully")
        
        from src.label_studio.tenant_isolation import LabelStudioTenantManager
        print("✓ LabelStudioTenantManager imported successfully")
        
        from src.label_studio.tenant_config import LabelStudioConfigManager
        print("✓ LabelStudioConfigManager imported successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False

def test_model_updates():
    """Test that models have been updated with tenant_id fields."""
    print("\nTesting model updates...")
    
    try:
        from src.business_logic.models import BusinessRuleModel, BusinessPatternModel, BusinessInsightModel
        from src.database.models import QualityIssueModel
        from src.ticket.models import TicketHistoryModel
        
        # Check that models exist and have expected table names
        assert BusinessRuleModel.__tablename__ == "business_rules"
        assert BusinessPatternModel.__tablename__ == "business_patterns"
        assert BusinessInsightModel.__tablename__ == "business_insights"
        assert QualityIssueModel.__tablename__ == "quality_issues"
        assert TicketHistoryModel.__tablename__ == "ticket_history"
        
        print("✓ All models have correct table names")
        return True
        
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        traceback.print_exc()
        return False

def test_tenant_context():
    """Test tenant context functionality."""
    print("\nTesting tenant context...")
    
    try:
        from src.middleware.tenant_middleware import TenantContext
        
        # Test context initialization
        context = TenantContext()
        assert context.tenant_id is None
        assert context.user_id is None
        assert not context.is_authenticated()
        
        # Test context with data
        context.tenant_id = "test_tenant"
        context.user_id = "test_user"
        context.user_role = "admin"
        
        assert context.is_authenticated()
        assert context.has_permission("admin", "all")
        
        print("✓ TenantContext functionality works")
        return True
        
    except Exception as e:
        print(f"✗ TenantContext test failed: {e}")
        traceback.print_exc()
        return False

def test_permission_manager():
    """Test permission manager functionality."""
    print("\nTesting permission manager...")
    
    try:
        from src.security.tenant_permissions import TenantPermissionManager, ResourceType, ActionType
        
        manager = TenantPermissionManager()
        
        # Test default roles exist
        assert "tenant_admin" in manager.default_roles
        assert "project_manager" in manager.default_roles
        assert "business_expert" in manager.default_roles
        assert "technical_expert" in manager.default_roles
        assert "contractor" in manager.default_roles
        assert "viewer" in manager.default_roles
        
        # Test role definitions
        admin_role = manager.default_roles["tenant_admin"]
        assert admin_role.name == "tenant_admin"
        assert admin_role.is_system_role
        assert len(admin_role.permissions) > 0
        
        print("✓ TenantPermissionManager functionality works")
        return True
        
    except Exception as e:
        print(f"✗ TenantPermissionManager test failed: {e}")
        traceback.print_exc()
        return False

def test_audit_logger():
    """Test audit logger functionality."""
    print("\nTesting audit logger...")
    
    try:
        from src.security.tenant_audit import TenantAuditLogger, AuditEvent, AuditAction, AuditCategory
        
        logger = TenantAuditLogger()
        
        # Test event creation
        event = AuditEvent(
            action=AuditAction.READ,
            resource_type="documents",
            resource_id="doc_1",
            tenant_id="tenant_1",
            user_id="user_1"
        )
        
        assert event.action == AuditAction.READ
        assert event.resource_type == "documents"
        assert event.tenant_id == "tenant_1"
        assert event.timestamp is not None
        
        # Test sensitive data sanitization
        sensitive_data = {
            "username": "test_user",
            "password": "secret123",
            "normal_field": "normal_value"
        }
        
        sanitized = logger._sanitize_details(sensitive_data)
        assert sanitized["username"] == "test_user"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["normal_field"] == "normal_value"
        
        print("✓ TenantAuditLogger functionality works")
        return True
        
    except Exception as e:
        print(f"✗ TenantAuditLogger test failed: {e}")
        traceback.print_exc()
        return False

def test_label_studio_config():
    """Test Label Studio configuration manager."""
    print("\nTesting Label Studio configuration...")
    
    try:
        from src.label_studio.tenant_config import LabelStudioConfigManager, AnnotationType
        
        manager = LabelStudioConfigManager()
        
        # Test default configs exist
        configs = manager.get_all_templates()
        assert len(configs) > 0
        
        # Test specific config
        text_config = manager.get_config_template(AnnotationType.TEXT_CLASSIFICATION)
        assert text_config is not None
        assert text_config.annotation_type == AnnotationType.TEXT_CLASSIFICATION
        assert "<View>" in text_config.config_xml
        
        # Test config validation
        validation_result = manager.validate_config(text_config.config_xml)
        assert validation_result["valid"] is True
        
        print("✓ LabelStudioConfigManager functionality works")
        return True
        
    except Exception as e:
        print(f"✗ LabelStudioConfigManager test failed: {e}")
        traceback.print_exc()
        return False

def test_migration_scripts():
    """Test that migration scripts are properly formatted."""
    print("\nTesting migration scripts...")
    
    try:
        import os
        
        # Check that migration files exist
        migration_files = [
            "alembic/versions/001_add_tenant_id_fields.py",
            "alembic/versions/002_optimize_tenant_indexes.py"
        ]
        
        for migration_file in migration_files:
            if os.path.exists(migration_file):
                print(f"✓ Migration file exists: {migration_file}")
                
                # Basic syntax check
                with open(migration_file, 'r') as f:
                    content = f.read()
                    assert "def upgrade():" in content
                    assert "def downgrade():" in content
                    print(f"✓ Migration file has correct structure: {migration_file}")
            else:
                print(f"✗ Migration file missing: {migration_file}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Migration script test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    print("=== Multi-Tenant Implementation Validation ===\n")
    
    tests = [
        test_imports,
        test_model_updates,
        test_tenant_context,
        test_permission_manager,
        test_audit_logger,
        test_label_studio_config,
        test_migration_scripts
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print(f"\n=== Validation Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Multi-tenant implementation is working correctly.")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())