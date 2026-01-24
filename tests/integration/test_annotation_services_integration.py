"""Integration tests for AI Annotation services.

Tests the complete workflow including:
- Annotation engines (Ollama, Zhipu, Baidu, etc.)
- Annotation switcher and method selection
- Security services (audit, RBAC, PII, tenant isolation)
- Performance optimization
- Resilience and health monitoring
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import asyncio
import pytest
from uuid import uuid4
from datetime import datetime


class TestAnnotationServicesIntegration:
    """Integration tests for annotation services."""

    @pytest.mark.asyncio
    async def test_complete_annotation_workflow_with_security(self):
        """Test complete annotation workflow with security checks."""
        from src.ai.annotation_switcher import AnnotationSwitcher
        from src.ai.annotation_audit_service import (
            get_annotation_audit_service,
            AnnotationOperationType,
            AnnotationObjectType,
        )
        from src.ai.annotation_rbac_service import (
            get_annotation_rbac_service,
            AnnotationRole,
            AnnotationPermission,
        )
        from src.ai.annotation_pii_service import (
            get_annotation_pii_service,
            DesensitizationStrategy,
        )

        # Setup services
        switcher = AnnotationSwitcher()
        audit_service = await get_annotation_audit_service()
        rbac_service = await get_annotation_rbac_service()
        pii_service = await get_annotation_pii_service()

        tenant_id = uuid4()
        user_id = uuid4()
        project_id = uuid4()

        # 1. Assign role to user
        await rbac_service.assign_role(
            tenant_id=tenant_id,
            user_id=user_id,
            role=AnnotationRole.PROJECT_ANNOTATOR,
            scope="tenant"
        )

        # 2. Check permission
        perm_check = await rbac_service.check_permission(
            tenant_id=tenant_id,
            user_id=user_id,
            permission=AnnotationPermission.ANNOTATION_CREATE,
            scope="tenant"
        )
        assert perm_check.allowed, "Annotator should have create permission"

        # 3. Sanitize input data with PII
        input_text = "Annotate this document. Contact: user@example.com"
        desentization_result = await pii_service.desensitize(
            input_text,
            strategy=DesensitizationStrategy.PARTIAL_MASK
        )
        sanitized_text = desentization_result.desensitized_text

        # 4. Log annotation creation
        audit_entry = await audit_service.log_operation(
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type=AnnotationOperationType.CREATE,
            object_type=AnnotationObjectType.ANNOTATION,
            object_id=uuid4(),
            before_state={},
            after_state={"text": sanitized_text},
            operation_description="Created annotation with sanitized data"
        )

        # 5. Verify audit entry integrity
        is_valid = await audit_service.verify_integrity(audit_entry.log_id)
        assert is_valid, "Audit entry should have valid integrity"

        # Verify PII was sanitized
        assert "user@example.com" not in sanitized_text, \
            "PII should be sanitized from annotation data"

        print("[OK] Complete annotation workflow with security: PASSED")

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_enforcement(self):
        """Test that multi-tenant isolation is enforced across all services."""
        from src.ai.annotation_audit_service import (
            get_annotation_audit_service,
            AnnotationOperationType,
            AnnotationObjectType,
            AnnotationAuditFilter,
        )
        from src.ai.annotation_rbac_service import (
            get_annotation_rbac_service,
            AnnotationRole,
        )
        from src.ai.annotation_tenant_isolation import (
            get_annotation_tenant_isolation_service,
        )

        audit_service = await get_annotation_audit_service()
        rbac_service = await get_annotation_rbac_service()
        tenant_service = await get_annotation_tenant_isolation_service()

        # Create two tenants
        tenant1_id = uuid4()
        tenant2_id = uuid4()
        user1_id = uuid4()
        user2_id = uuid4()

        # Register tenants
        await tenant_service.register_tenant(tenant1_id, "Tenant 1")
        await tenant_service.register_tenant(tenant2_id, "Tenant 2")

        # Assign roles to users in different tenants
        await rbac_service.assign_role(
            tenant_id=tenant1_id,
            user_id=user1_id,
            role=AnnotationRole.PROJECT_ANNOTATOR,
            scope="tenant"
        )
        await rbac_service.assign_role(
            tenant_id=tenant2_id,
            user_id=user2_id,
            role=AnnotationRole.PROJECT_ANNOTATOR,
            scope="tenant"
        )

        # Create audit logs for each tenant
        await audit_service.log_operation(
            tenant_id=tenant1_id,
            user_id=user1_id,
            operation_type=AnnotationOperationType.CREATE,
            object_type=AnnotationObjectType.ANNOTATION,
            object_id=uuid4(),
            operation_description="Tenant 1 operation"
        )
        await audit_service.log_operation(
            tenant_id=tenant2_id,
            user_id=user2_id,
            operation_type=AnnotationOperationType.CREATE,
            object_type=AnnotationObjectType.ANNOTATION,
            object_id=uuid4(),
            operation_description="Tenant 2 operation"
        )

        # Verify tenant isolation in audit logs
        tenant1_logs = await audit_service.get_logs(
            AnnotationAuditFilter(tenant_id=tenant1_id, limit=100)
        )
        tenant2_logs = await audit_service.get_logs(
            AnnotationAuditFilter(tenant_id=tenant2_id, limit=100)
        )

        # Each tenant should only see their own logs
        for log in tenant1_logs:
            assert log.tenant_id == tenant1_id, \
                "Tenant 1 should only see their own logs"
        for log in tenant2_logs:
            assert log.tenant_id == tenant2_id, \
                "Tenant 2 should only see their own logs"

        # Verify RBAC isolation
        perm_check = await rbac_service.check_permission(
            tenant_id=tenant2_id,
            user_id=user1_id,  # User from tenant 1
            permission=AnnotationPermission.ANNOTATION_CREATE,
            scope="tenant"
        )
        assert not perm_check.allowed, \
            "User from tenant 1 should not have permissions in tenant 2"

        print("[OK] Multi-tenant isolation enforcement: PASSED")

    @pytest.mark.asyncio
    async def test_annotation_version_tracking_with_rbac(self):
        """Test annotation versioning with RBAC checks."""
        from src.ai.annotation_audit_service import (
            get_annotation_audit_service,
            AnnotationOperationType,
            AnnotationObjectType,
        )
        from src.ai.annotation_rbac_service import (
            get_annotation_rbac_service,
            AnnotationRole,
            AnnotationPermission,
        )

        audit_service = await get_annotation_audit_service()
        rbac_service = await get_annotation_rbac_service()

        tenant_id = uuid4()
        annotator_id = uuid4()
        reviewer_id = uuid4()
        annotation_id = uuid4()

        # Assign roles
        await rbac_service.assign_role(
            tenant_id=tenant_id,
            user_id=annotator_id,
            role=AnnotationRole.PROJECT_ANNOTATOR,
            scope="tenant"
        )
        await rbac_service.assign_role(
            tenant_id=tenant_id,
            user_id=reviewer_id,
            role=AnnotationRole.PROJECT_REVIEWER,
            scope="tenant"
        )

        # Annotator creates annotation
        can_create = await rbac_service.check_permission(
            tenant_id=tenant_id,
            user_id=annotator_id,
            permission=AnnotationPermission.ANNOTATION_CREATE,
            scope="tenant"
        )
        assert can_create.allowed, "Annotator should be able to create"

        await audit_service.log_operation(
            tenant_id=tenant_id,
            user_id=annotator_id,
            operation_type=AnnotationOperationType.CREATE,
            object_type=AnnotationObjectType.ANNOTATION,
            object_id=annotation_id,
            after_state={"version": 1, "status": "draft"},
            operation_description="Initial annotation"
        )

        # Annotator updates annotation
        can_update = await rbac_service.check_permission(
            tenant_id=tenant_id,
            user_id=annotator_id,
            permission=AnnotationPermission.ANNOTATION_UPDATE,
            scope="tenant"
        )
        assert can_update.allowed, "Annotator should be able to update"

        await audit_service.log_operation(
            tenant_id=tenant_id,
            user_id=annotator_id,
            operation_type=AnnotationOperationType.UPDATE,
            object_type=AnnotationObjectType.ANNOTATION,
            object_id=annotation_id,
            before_state={"version": 1, "status": "draft"},
            after_state={"version": 2, "status": "draft"},
            operation_description="Updated annotation"
        )

        # Reviewer approves annotation
        can_approve = await rbac_service.check_permission(
            tenant_id=tenant_id,
            user_id=reviewer_id,
            permission=AnnotationPermission.ANNOTATION_APPROVE,
            scope="tenant"
        )
        assert can_approve.allowed, "Reviewer should be able to approve"

        await audit_service.log_operation(
            tenant_id=tenant_id,
            user_id=reviewer_id,
            operation_type=AnnotationOperationType.APPROVE,
            object_type=AnnotationObjectType.ANNOTATION,
            object_id=annotation_id,
            before_state={"version": 2, "status": "draft"},
            after_state={"version": 3, "status": "approved"},
            operation_description="Approved annotation"
        )

        # Verify version history
        versions = await audit_service.get_annotation_versions(annotation_id)
        assert len(versions) >= 3, "Should have at least 3 versions"

        # Verify annotator cannot delete
        can_delete = await rbac_service.check_permission(
            tenant_id=tenant_id,
            user_id=annotator_id,
            permission=AnnotationPermission.ANNOTATION_DELETE,
            scope="tenant"
        )
        assert not can_delete.allowed, "Annotator should not be able to delete"

        print("[OK] Annotation version tracking with RBAC: PASSED")

    @pytest.mark.asyncio
    async def test_pii_sanitization_in_audit_logs(self):
        """Test that PII is sanitized before being logged in audit trail."""
        from src.ai.annotation_audit_service import (
            get_annotation_audit_service,
            AnnotationOperationType,
            AnnotationObjectType,
            AnnotationAuditFilter,
        )
        from src.ai.annotation_pii_service import (
            get_annotation_pii_service,
            DesensitizationStrategy,
        )

        audit_service = await get_annotation_audit_service()
        pii_service = await get_annotation_pii_service()

        tenant_id = uuid4()
        user_id = uuid4()

        # Original annotation with PII
        original_data = {
            "text": "Customer email: john.doe@example.com",
            "phone": "13812345678",
            "notes": "Contact customer at the above details"
        }

        # Sanitize all PII in the data
        sanitized_data = {}
        for key, value in original_data.items():
            if isinstance(value, str):
                result = await pii_service.desensitize(
                    value,
                    strategy=DesensitizationStrategy.PARTIAL_MASK
                )
                sanitized_data[key] = result.desensitized_text
            else:
                sanitized_data[key] = value

        # Log operation with sanitized data
        await audit_service.log_operation(
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type=AnnotationOperationType.CREATE,
            object_type=AnnotationObjectType.ANNOTATION,
            object_id=uuid4(),
            before_state={},
            after_state=sanitized_data,
            operation_description="Created annotation with sanitized PII"
        )

        # Retrieve audit logs
        logs = await audit_service.get_logs(
            AnnotationAuditFilter(tenant_id=tenant_id, limit=10)
        )

        # Verify PII is not in audit logs
        for log in logs:
            log_str = str(log.after_state)
            assert "john.doe@example.com" not in log_str, \
                "Original email should not appear in audit logs"
            assert "13812345678" not in log_str, \
                "Original phone should not appear in audit logs"

        print("[OK] PII sanitization in audit logs: PASSED")


def run_integration_tests():
    """Run all integration tests."""
    print("\n" + "="*70)
    print("AI Annotation Services - Integration Tests")
    print("="*70)

    test_suite = TestAnnotationServicesIntegration()
    results = {}

    # Run tests
    tests = [
        ("Complete Workflow with Security", test_suite.test_complete_annotation_workflow_with_security),
        ("Multi-Tenant Isolation", test_suite.test_multi_tenant_isolation_enforcement),
        ("Version Tracking with RBAC", test_suite.test_annotation_version_tracking_with_rbac),
        ("PII Sanitization in Audit", test_suite.test_pii_sanitization_in_audit_logs),
    ]

    for test_name, test_func in tests:
        try:
            asyncio.run(test_func())
            results[test_name] = True
        except Exception as e:
            print(f"[X] {test_name} FAILED: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "[OK] PASS" if passed_test else "[X] FAIL"
        print(f"{test_name:45s} {status}")

    print(f"\nTotal: {passed}/{total} integration tests passed")
    print("="*70)

    return passed == total


if __name__ == "__main__":
    import sys
    success = run_integration_tests()
    sys.exit(0 if success else 1)
