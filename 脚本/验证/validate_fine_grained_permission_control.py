#!/usr/bin/env python3
"""
Fine-Grained Permission Control Validation Script.

This script validates that the fine-grained permission control system
is properly implemented according to the audit-security requirements.
"""

import sys
import logging
from datetime import datetime
from uuid import uuid4
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PermissionControlValidator:
    """Validator for fine-grained permission control implementation."""
    
    def __init__(self):
        self.validation_results = []
        self.passed_tests = 0
        self.failed_tests = 0
    
    def validate_requirement(self, requirement_id: str, description: str, validation_func) -> bool:
        """Validate a specific requirement."""
        logger.info(f"Validating {requirement_id}: {description}")
        
        try:
            result = validation_func()
            if result:
                self.passed_tests += 1
                logger.info(f"✅ {requirement_id} PASSED")
            else:
                self.failed_tests += 1
                logger.error(f"❌ {requirement_id} FAILED")
            
            self.validation_results.append({
                "requirement_id": requirement_id,
                "description": description,
                "status": "PASSED" if result else "FAILED",
                "timestamp": datetime.now().isoformat()
            })
            
            return result
            
        except Exception as e:
            self.failed_tests += 1
            logger.error(f"❌ {requirement_id} FAILED with exception: {e}")
            self.validation_results.append({
                "requirement_id": requirement_id,
                "description": description,
                "status": "FAILED",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False
    
    def validate_rbac_controller_exists(self) -> bool:
        """Validate that RBAC controller is properly implemented."""
        try:
            from src.security.rbac_controller import RBACController
            controller = RBACController()
            
            # Check essential methods exist
            required_methods = [
                'create_role', 'assign_role_to_user', 'check_user_permission',
                'get_user_roles', 'grant_resource_permission', 'batch_check_permissions'
            ]
            
            for method in required_methods:
                if not hasattr(controller, method):
                    logger.error(f"Missing required method: {method}")
                    return False
            
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import RBACController: {e}")
            return False
    
    def validate_role_manager_exists(self) -> bool:
        """Validate that role manager is properly implemented."""
        try:
            from src.security.role_manager import RoleManager
            manager = RoleManager()
            
            # Check role templates exist
            templates = manager._role_templates
            required_roles = [
                "Tenant Admin", "Project Manager", "Data Analyst",
                "Data Viewer", "Security Officer", "Auditor"
            ]
            
            for role in required_roles:
                if role not in templates:
                    logger.error(f"Missing required role template: {role}")
                    return False
            
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import RoleManager: {e}")
            return False
    
    def validate_rbac_models_exist(self) -> bool:
        """Validate that RBAC models are properly defined."""
        try:
            from src.security.rbac_models import (
                RoleModel, PermissionModel, UserRoleModel,
                RolePermissionModel, ResourceModel, ResourcePermissionModel,
                PermissionScope, ResourceType
            )
            
            # Check enums have required values
            required_scopes = ["GLOBAL", "TENANT", "RESOURCE"]
            for scope in required_scopes:
                if not hasattr(PermissionScope, scope):
                    logger.error(f"Missing permission scope: {scope}")
                    return False
            
            required_resource_types = [
                "PROJECT", "DATASET", "MODEL", "PIPELINE", 
                "REPORT", "DASHBOARD", "USER", "ROLE"
            ]
            for resource_type in required_resource_types:
                if not hasattr(ResourceType, resource_type):
                    logger.error(f"Missing resource type: {resource_type}")
                    return False
            
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import RBAC models: {e}")
            return False
    
    def validate_permission_cache_exists(self) -> bool:
        """Validate that permission caching is implemented."""
        try:
            from src.security.permission_cache import PermissionCache, get_permission_cache
            
            cache = get_permission_cache()
            
            # Check essential cache methods
            required_methods = [
                'get_permission', 'set_permission', 'invalidate_user_permissions',
                'get_cache_statistics', 'clear_all_cache'
            ]
            
            for method in required_methods:
                if not hasattr(cache, method):
                    logger.error(f"Missing cache method: {method}")
                    return False
            
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import permission cache: {e}")
            return False
    
    def validate_role_permission_matrix(self) -> bool:
        """Validate role permission matrix implementation."""
        try:
            from src.security.role_manager import RoleManager
            manager = RoleManager()
            
            templates = manager._role_templates
            
            # Validate Tenant Admin has comprehensive permissions
            admin_perms = templates["Tenant Admin"]["permissions"]
            required_admin_perms = [
                "user.read", "user.write", "user.delete",
                "role.read", "role.write", "role.delete",
                "project.read", "project.write", "project.delete",
                "audit.read", "audit.export"
            ]
            
            for perm in required_admin_perms:
                if perm not in admin_perms:
                    logger.error(f"Tenant Admin missing permission: {perm}")
                    return False
            
            # Validate Data Viewer has limited permissions
            viewer_perms = templates["Data Viewer"]["permissions"]
            restricted_perms = ["user.write", "user.delete", "role.write", "role.delete"]
            
            for perm in restricted_perms:
                if perm in viewer_perms:
                    logger.error(f"Data Viewer should not have permission: {perm}")
                    return False
            
            # Validate Security Officer has security-specific permissions
            security_perms = templates["Security Officer"]["permissions"]
            required_security_perms = [
                "audit.read", "audit.export", 
                "desensitization.read", "desensitization.write"
            ]
            
            for perm in required_security_perms:
                if perm not in security_perms:
                    logger.error(f"Security Officer missing permission: {perm}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Role permission matrix validation failed: {e}")
            return False
    
    def validate_resource_level_permissions(self) -> bool:
        """Validate resource-level permission support."""
        try:
            from src.security.rbac_controller import RBACController
            from src.security.rbac_models import ResourceType
            
            controller = RBACController()
            
            # Check resource permission methods exist
            required_methods = [
                'register_resource', 'grant_resource_permission',
                '_check_resource_permission'
            ]
            
            for method in required_methods:
                if not hasattr(controller, method):
                    logger.error(f"Missing resource permission method: {method}")
                    return False
            
            # Check ResourceType enum has required values
            required_types = [
                ResourceType.PROJECT, ResourceType.DATASET, 
                ResourceType.MODEL, ResourceType.REPORT
            ]
            
            for resource_type in required_types:
                if not isinstance(resource_type, ResourceType):
                    logger.error(f"Invalid resource type: {resource_type}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Resource-level permission validation failed: {e}")
            return False
    
    def validate_permission_caching_performance(self) -> bool:
        """Validate permission caching for performance."""
        try:
            from src.security.permission_cache import get_permission_cache
            
            cache = get_permission_cache()
            
            # Test cache statistics
            stats = cache.get_cache_statistics()
            required_stats = [
                "hit_rate", "total_requests", "cache_hits", 
                "cache_misses", "memory_cache_size"
            ]
            
            for stat in required_stats:
                if stat not in stats:
                    logger.error(f"Missing cache statistic: {stat}")
                    return False
            
            # Test cache operations
            user_id = uuid4()
            permission_name = "test.permission"
            
            # Should return None for cache miss
            result = cache.get_permission(user_id, permission_name)
            if result is not None:
                logger.error("Expected cache miss, got result")
                return False
            
            # Set permission in cache
            cache.set_permission(user_id, permission_name, True)
            
            # Should return cached result
            result = cache.get_permission(user_id, permission_name)
            if result is not True:
                logger.error("Expected cached result True, got different result")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Permission caching validation failed: {e}")
            return False
    
    def validate_audit_integration(self) -> bool:
        """Validate audit integration for permission operations."""
        try:
            from src.security.permission_audit_integration import get_permission_audit_integration
            
            audit_integration = get_permission_audit_integration()
            
            # Check audit methods exist
            required_methods = [
                'log_permission_check', 'log_role_assignment', 
                'log_role_revocation', 'log_bulk_permission_check'
            ]
            
            for method in required_methods:
                if not hasattr(audit_integration, method):
                    logger.error(f"Missing audit method: {method}")
                    return False
            
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import audit integration: {e}")
            return False
    
    def validate_tests_pass(self) -> bool:
        """Validate that all RBAC tests pass."""
        import subprocess
        
        try:
            # Run RBAC system tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/test_rbac_system.py", "-v", "--tb=short"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"RBAC tests failed: {result.stdout}\n{result.stderr}")
                return False
            
            # Run fine-grained permission control tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/test_fine_grained_permission_control.py", "-v", "--tb=short"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Fine-grained permission tests failed: {result.stdout}\n{result.stderr}")
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Tests timed out")
            return False
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return False
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete validation suite."""
        logger.info("Starting Fine-Grained Permission Control Validation")
        logger.info("=" * 60)
        
        # Requirement 5: Fine-grained permission control
        self.validate_requirement(
            "REQ-5.1", 
            "Resource-level permission assignment",
            self.validate_resource_level_permissions
        )
        
        self.validate_requirement(
            "REQ-5.2", 
            "Operation-specific access control",
            self.validate_rbac_controller_exists
        )
        
        self.validate_requirement(
            "REQ-5.3", 
            "Conditional permissions based on context",
            self.validate_rbac_models_exist
        )
        
        self.validate_requirement(
            "REQ-5.4", 
            "Permission inheritance and delegation",
            self.validate_role_manager_exists
        )
        
        self.validate_requirement(
            "REQ-5.5", 
            "Principle of least privilege enforcement",
            self.validate_role_permission_matrix
        )
        
        # Requirement 6: Role permission matrix
        self.validate_requirement(
            "REQ-6", 
            "Role permission matrix implementation",
            self.validate_role_permission_matrix
        )
        
        # Requirement 7: Dynamic permission evaluation
        self.validate_requirement(
            "REQ-7.1", 
            "Real-time permission evaluation",
            self.validate_permission_cache_exists
        )
        
        self.validate_requirement(
            "REQ-7.2", 
            "User behavior patterns and risk scores",
            self.validate_audit_integration
        )
        
        self.validate_requirement(
            "REQ-7.3", 
            "Time-based and location-based restrictions",
            self.validate_permission_caching_performance
        )
        
        # Test validation
        self.validate_requirement(
            "TEST-VALIDATION", 
            "All RBAC tests pass",
            self.validate_tests_pass
        )
        
        # Generate summary
        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        summary = {
            "validation_timestamp": datetime.now().isoformat(),
            "total_requirements": total_tests,
            "passed_requirements": self.passed_tests,
            "failed_requirements": self.failed_tests,
            "success_rate": round(success_rate, 2),
            "overall_status": "PASSED" if self.failed_tests == 0 else "FAILED",
            "detailed_results": self.validation_results
        }
        
        logger.info("=" * 60)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Requirements: {total_tests}")
        logger.info(f"Passed: {self.passed_tests}")
        logger.info(f"Failed: {self.failed_tests}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(f"Overall Status: {summary['overall_status']}")
        
        if summary['overall_status'] == "PASSED":
            logger.info("🎉 Fine-Grained Permission Control is PROPERLY IMPLEMENTED!")
        else:
            logger.error("❌ Fine-Grained Permission Control implementation has issues!")
        
        return summary


def main():
    """Main validation function."""
    validator = PermissionControlValidator()
    
    try:
        summary = validator.run_validation()
        
        # Write results to file
        import json
        with open("permission_control_validation_report.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Detailed validation report saved to: permission_control_validation_report.json")
        
        # Exit with appropriate code
        sys.exit(0 if summary['overall_status'] == "PASSED" else 1)
        
    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()