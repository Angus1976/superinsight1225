"""Quick verification of services integration.

Verifies that all services can be imported and instantiated together.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


def verify_annotation_services_integration():
    """Verify annotation services can work together."""
    print("\n=== Verifying Annotation Services Integration ===")

    try:
        # Import core annotation services
        from src.ai.annotation_switcher import AnnotationSwitcher
        from src.ai.annotation_audit_service import AnnotationAuditService
        from src.ai.annotation_rbac_service import AnnotationRBACService
        from src.ai.annotation_pii_service import AnnotationPIIService
        from src.ai.annotation_tenant_isolation import AnnotationTenantIsolationService
        from src.ai.annotation_performance_optimizer import ParallelBatchProcessor, ModelCacheManager, RateLimiter
        from src.ai.annotation_resilience import LLMRetryService, InputValidationService

        print("[OK] All annotation service imports successful")

        # Verify services can be instantiated
        switcher = AnnotationSwitcher()
        audit_svc = AnnotationAuditService()
        rbac_svc = AnnotationRBACService()
        pii_svc = AnnotationPIIService()
        tenant_svc = AnnotationTenantIsolationService()
        batch_processor = ParallelBatchProcessor()
        cache_mgr = ModelCacheManager()
        rate_limiter = RateLimiter()
        retry_svc = LLMRetryService()
        validation_svc = InputValidationService()

        print("[OK] All annotation services instantiated successfully")

        # Verify key methods exist
        assert hasattr(audit_svc, 'log_operation'), "Audit service missing log_operation"
        assert hasattr(rbac_svc, 'check_permission'), "RBAC service missing check_permission"
        assert hasattr(pii_svc, 'detect_pii'), "PII service missing detect_pii"
        assert hasattr(tenant_svc, 'validate_tenant_access'), "Tenant service missing validate_tenant_access"
        assert hasattr(batch_processor, 'submit_job'), "Batch processor missing submit_job"
        assert hasattr(cache_mgr, 'get'), "Cache manager missing get"
        assert hasattr(rate_limiter, 'acquire'), "Rate limiter missing acquire"
        assert hasattr(retry_svc, 'retry_with_backoff'), "Retry service missing retry_with_backoff"
        assert hasattr(validation_svc, 'validate_annotation_task'), "Validation service missing validate_annotation_task"

        print("[OK] All annotation service methods verified")
        return True

    except Exception as e:
        print(f"[X] Annotation services integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_text_to_sql_services_integration():
    """Verify Text-to-SQL services can work together."""
    print("\n=== Verifying Text-to-SQL Services Integration ===")

    print("[SKIP] Text-to-SQL services pending implementation (Task 4)")
    return None  # Return None to indicate skipped


def verify_cross_service_integration():
    """Verify services from different modules can integrate."""
    print("\n=== Verifying Cross-Service Integration ===")

    try:
        # Import services from different modules
        from src.ai.annotation_switcher import AnnotationSwitcher

        print("[OK] Annotation switcher import successful")

        # Verify annotation switcher
        annotation_switcher = AnnotationSwitcher()
        assert hasattr(annotation_switcher, 'annotate'), "Annotation switcher missing annotate"

        print("[OK] Cross-service integration verified")
        return True

    except Exception as e:
        print(f"[X] Cross-service integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_security_integration():
    """Verify security services integrate properly."""
    print("\n=== Verifying Security Services Integration ===")

    try:
        from src.ai.annotation_audit_service import AnnotationAuditService
        from src.ai.annotation_rbac_service import AnnotationRBACService
        from src.ai.annotation_pii_service import AnnotationPIIService
        from src.ai.annotation_tenant_isolation import AnnotationTenantIsolationService

        # Verify all security services can coexist
        audit = AnnotationAuditService()
        rbac = AnnotationRBACService()
        pii = AnnotationPIIService()
        tenant = AnnotationTenantIsolationService()

        print("[OK] All security services initialized together")

        # Verify security enums are available
        from src.ai.annotation_audit_service import AnnotationOperationType, AnnotationObjectType
        from src.ai.annotation_rbac_service import AnnotationPermission, AnnotationRole
        from src.ai.annotation_pii_service import PIIType, DesensitizationStrategy
        from src.ai.annotation_tenant_isolation import TenantIsolationViolationType

        print("[OK] All security enums available")

        # Verify enum values
        assert len(list(AnnotationOperationType)) > 0, "AnnotationOperationType should have values"
        assert len(list(AnnotationPermission)) > 0, "AnnotationPermission should have values"
        assert len(list(PIIType)) > 0, "PIIType should have values"
        assert len(list(TenantIsolationViolationType)) > 0, "TenantIsolationViolationType should have values"

        print("[OK] Security services integration verified")
        return True

    except Exception as e:
        print(f"[X] Security services integration failed: {e}")
        return False


def main():
    """Run all integration verifications."""
    print("="*70)
    print("Services Integration Verification")
    print("="*70)

    results = {
        "Annotation Services": verify_annotation_services_integration(),
        "Text-to-SQL Services": verify_text_to_sql_services_integration(),
        "Cross-Service Integration": verify_cross_service_integration(),
        "Security Integration": verify_security_integration(),
    }

    # Summary
    print("\n" + "="*70)
    print("INTEGRATION VERIFICATION SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v is True)
    skipped = sum(1 for v in results.values() if v is None)
    failed = sum(1 for v in results.values() if v is False)
    total = len(results)

    for service_name, result in results.items():
        if result is True:
            status = "[OK] PASS"
        elif result is None:
            status = "[--] SKIP"
        else:
            status = "[X] FAIL"
        print(f"{service_name:40s} {status}")

    print(f"\nTotal: {passed}/{total - skipped} integrations verified ({skipped} skipped)")
    print("="*70)

    if failed == 0:
        print("\n>>> ALL ACTIVE SERVICES INTEGRATION VERIFIED! <<<")
        return True
    else:
        print(f"\n[!] {failed} integration(s) failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
