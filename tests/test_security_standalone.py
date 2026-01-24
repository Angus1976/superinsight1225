"""Standalone tests for AI Annotation Security Features.

This module provides quick verification tests for security services
without complex dependency chains.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import asyncio
from uuid import uuid4


async def test_audit_service():
    """Test audit logging service."""
    print("\n===Testing Audit Logging Service ===")

    from src.ai.annotation_audit_service import (
        AnnotationAuditService,
        AnnotationOperationType,
        AnnotationObjectType,
        AnnotationAuditFilter,
        reset_annotation_audit_service,
    )

    # Reset service
    await reset_annotation_audit_service()
    service = AnnotationAuditService()

    tenant_id = uuid4()
    user_id = uuid4()

    # Test logging operations
    print("1. Logging 5 operations...")
    for i in range(5):
        entry = await service.log_operation(
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type=AnnotationOperationType.CREATE,
            object_type=AnnotationObjectType.ANNOTATION,
            object_id=uuid4(),
            operation_description=f"Test operation {i}"
        )
        assert entry.log_id is not None, "Log entry should have ID"
        assert entry.hmac_signature is not None, "Log entry should have HMAC signature"

    # Test retrieving logs
    print("2. Retrieving logs...")
    filter = AnnotationAuditFilter(tenant_id=tenant_id, limit=100)
    logs = await service.get_logs(filter)
    assert len(logs) == 5, f"Expected 5 logs, got {len(logs)}"

    # Test integrity verification
    print("3. Verifying integrity...")
    for log in logs:
        is_valid = await service.verify_integrity(log.log_id)
        assert is_valid, f"Log {log.log_id} failed integrity check"

    # Test version tracking
    print("4. Testing version tracking...")
    annotation_id = uuid4()
    for version_num in range(3):
        await service.log_operation(
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type=AnnotationOperationType.UPDATE,
            object_type=AnnotationObjectType.ANNOTATION,
            object_id=annotation_id,
            after_state={"version": version_num},
            operation_description=f"Version {version_num}"
        )

    versions = await service.get_annotation_versions(annotation_id)
    assert len(versions) == 3, f"Expected 3 versions, got {len(versions)}"

    # Test tenant isolation
    print("5. Testing tenant isolation...")
    other_tenant_id = uuid4()
    other_filter = AnnotationAuditFilter(tenant_id=other_tenant_id, limit=100)
    other_logs = await service.get_logs(other_filter)
    assert len(other_logs) == 0, "Should not retrieve logs from different tenant"

    print("[OK] Audit Service: ALL TESTS PASSED")
    return True


async def test_rbac_service():
    """Test RBAC service."""
    print("\n=== Testing RBAC Service ===")

    from src.ai.annotation_rbac_service import (
        AnnotationRBACService,
        AnnotationRole,
        AnnotationPermission,
        reset_annotation_rbac_service,
    )

    # Reset service
    await reset_annotation_rbac_service()
    service = AnnotationRBACService()

    tenant_id = uuid4()
    user_id = uuid4()

    # Test role assignment
    print("1. Assigning role to user...")
    await service.assign_role(
        tenant_id=tenant_id,
        user_id=user_id,
        role=AnnotationRole.PROJECT_ANNOTATOR,
        scope="tenant"
    )

    # Test role retrieval
    print("2. Retrieving user roles...")
    roles = await service.get_user_roles(tenant_id=tenant_id, user_id=user_id)
    assert AnnotationRole.PROJECT_ANNOTATOR in [r.role for r in roles], \
        "User should have PROJECT_ANNOTATOR role"

    # Test permission check - annotators can create
    print("3. Testing annotator permissions...")
    check = await service.check_permission(
        tenant_id=tenant_id,
        user_id=user_id,
        permission=AnnotationPermission.ANNOTATION_CREATE,
        scope="tenant"
    )
    assert check.allowed, "Annotators should be able to create annotations"

    # Test permission denial - annotators cannot delete
    check = await service.check_permission(
        tenant_id=tenant_id,
        user_id=user_id,
        permission=AnnotationPermission.ANNOTATION_DELETE,
        scope="tenant"
    )
    assert not check.allowed, "Annotators should not be able to delete annotations"

    # Test admin role - has all permissions
    print("4. Testing admin permissions...")
    admin_user = uuid4()
    await service.assign_role(
        tenant_id=tenant_id,
        user_id=admin_user,
        role=AnnotationRole.TENANT_ADMIN,
        scope="tenant"
    )

    check = await service.check_permission(
        tenant_id=tenant_id,
        user_id=admin_user,
        permission=AnnotationPermission.ANNOTATION_DELETE,
        scope="tenant"
    )
    assert check.allowed, "Admins should have delete permission"

    # Test tenant isolation
    print("5. Testing tenant isolation...")
    other_tenant = uuid4()
    check = await service.check_permission(
        tenant_id=other_tenant,
        user_id=user_id,
        permission=AnnotationPermission.ANNOTATION_CREATE,
        scope="tenant"
    )
    assert not check.allowed, "User from different tenant should not have permissions"

    print("[OK] RBAC Service: ALL TESTS PASSED")
    return True


async def test_pii_service():
    """Test PII detection and desensitization service."""
    print("\n=== Testing PII Service ===")

    from src.ai.annotation_pii_service import (
        AnnotationPIIService,
        DesensitizationStrategy,
        PIIType,
        reset_annotation_pii_service,
    )

    # Reset service
    await reset_annotation_pii_service()
    service = AnnotationPIIService()

    # Test email detection
    print("1. Testing email detection...")
    text_with_email = "Contact me at user@example.com for details"
    detections = await service.detect_pii(text_with_email)
    email_detections = [d for d in detections if d.pii_type == PIIType.EMAIL]
    assert len(email_detections) > 0, "Should detect email address"
    assert "user@example.com" in email_detections[0].text, "Should detect correct email"

    # Test phone detection
    print("2. Testing phone detection...")
    text_with_phone = "Call me at 13812345678"
    detections = await service.detect_pii(text_with_phone)
    phone_detections = [d for d in detections if d.pii_type == PIIType.PHONE_CN]
    assert len(phone_detections) > 0, "Should detect Chinese phone number"

    # Test masking strategy
    print("3. Testing masking desensitization...")
    result = await service.desensitize(
        text_with_email,
        strategy=DesensitizationStrategy.MASK
    )
    assert "user@example.com" not in result.desensitized_text, \
        "Original email should be masked"
    assert "*" in result.desensitized_text or "MASKED" in result.desensitized_text, \
        "Masked text should contain masking indicator"

    # Test multiple PII items
    print("4. Testing multiple PII detection...")
    complex_text = "Email: user@example.com, Phone: 13812345678, Another email: admin@test.org"
    detections = await service.detect_pii(complex_text)
    assert len(detections) >= 2, f"Should detect at least 2 PII items, got {len(detections)}"

    # Test desensitization result mapping
    print("5. Testing desensitization mapping...")
    result = await service.desensitize(
        text_with_email,
        strategy=DesensitizationStrategy.PARTIAL_MASK
    )
    assert len(result.mapping) > 0, "Should have desensitization mapping"
    assert "user@example.com" in result.mapping, "Mapping should contain original PII"

    print("[OK] PII Service: ALL TESTS PASSED")
    return True


async def test_tenant_isolation_service():
    """Test multi-tenant isolation service."""
    print("\n=== Testing Tenant Isolation Service ===")

    from src.ai.annotation_tenant_isolation import (
        AnnotationTenantIsolationService,
        reset_annotation_tenant_isolation_service,
    )

    # Reset service
    await reset_annotation_tenant_isolation_service()
    service = AnnotationTenantIsolationService()

    # Register tenants
    print("1. Registering tenants...")
    tenant1 = uuid4()
    tenant2 = uuid4()

    await service.register_tenant(tenant1, "Tenant 1")
    await service.register_tenant(tenant2, "Tenant 2")

    # Create contexts
    print("2. Creating tenant contexts...")
    context1 = await service.create_context(
        tenant_id=tenant1,
        user_id=uuid4()
    )
    assert context1.tenant_id == tenant1, "Context should have correct tenant ID"

    # Test cross-tenant access prevention
    print("3. Testing cross-tenant access prevention...")
    try:
        await service.validate_tenant_access(
            context=context1,
            resource_tenant_id=tenant2,
            resource_type="annotation",
            resource_id=uuid4()
        )
        assert False, "Should have raised PermissionError for cross-tenant access"
    except PermissionError:
        pass  # Expected

    # Test tenant filter enforcement
    print("4. Testing tenant filter enforcement...")
    filter = await service.enforce_tenant_filter(
        tenant_id=tenant1,
        filters={"project_id": uuid4()}
    )
    assert filter.tenant_id == tenant1, "Filter should have correct tenant ID"
    filter_dict = filter.to_dict()
    assert "tenant_id" in filter_dict, "Filter dict should contain tenant_id"

    # Test same-tenant access allowed
    print("5. Testing same-tenant access...")
    try:
        await service.validate_tenant_access(
            context=context1,
            resource_tenant_id=tenant1,
            resource_type="annotation",
            resource_id=uuid4()
        )
        # Should succeed
    except PermissionError:
        assert False, "Same-tenant access should be allowed"

    print("[OK] Tenant Isolation Service: ALL TESTS PASSED")
    return True


async def run_all_tests():
    """Run all security tests."""
    print("\n" + "="*70)
    print("AI Annotation Security Features - Comprehensive Test Suite")
    print("="*70)

    results = {
        "Audit Service": False,
        "RBAC Service": False,
        "PII Service": False,
        "Tenant Isolation Service": False,
    }

    try:
        results["Audit Service"] = await test_audit_service()
    except Exception as e:
        print(f"[X] Audit Service FAILED: {e}")

    try:
        results["RBAC Service"] = await test_rbac_service()
    except Exception as e:
        print(f"[X] RBAC Service FAILED: {e}")

    try:
        results["PII Service"] = await test_pii_service()
    except Exception as e:
        print(f"[X] PII Service FAILED: {e}")

    try:
        results["Tenant Isolation Service"] = await test_tenant_isolation_service()
    except Exception as e:
        print(f"[X] Tenant Isolation Service FAILED: {e}")

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for service, passed_test in results.items():
        status = "[OK] PASS" if passed_test else "[X] FAIL"
        print(f"{service:30s} {status}")

    print(f"\nTotal: {passed}/{total} services passed")
    print("="*70)

    if passed == total:
        print("\n>>> ALL SECURITY FEATURES VERIFIED SUCCESSFULLY! <<<")
        return True
    else:
        print(f"\n[!] {total - passed} service(s) failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
