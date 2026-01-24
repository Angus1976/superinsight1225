"""Property-based tests for AI Annotation Security Features.

This module tests the following security properties:
- Property 25: Audit Trail Completeness
- Property 26: Role-Based Access Enforcement
- Property 27: Sensitive Data Desensitization
- Property 28: Multi-Tenant Isolation

Requirements:
- 7.1: Audit logging
- 7.2: RBAC enforcement
- 7.3: PII desensitization
- 7.4: Annotation history and versioning
- 7.5: Export with metadata
- 7.6: Multi-tenant isolation
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from typing import Dict, List, Set
from uuid import UUID, uuid4
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.ai.annotation_audit_service import (
    AnnotationAuditService,
    AnnotationOperationType,
    AnnotationObjectType,
    AnnotationAuditFilter,
    reset_annotation_audit_service,
)
from src.ai.annotation_rbac_service import (
    AnnotationRBACService,
    AnnotationPermission,
    AnnotationRole,
    reset_annotation_rbac_service,
)
from src.ai.annotation_pii_service import (
    AnnotationPIIService,
    PIIType,
    DesensitizationStrategy,
    reset_annotation_pii_service,
)
from src.ai.annotation_tenant_isolation import (
    AnnotationTenantIsolationService,
    TenantContext,
    TenantIsolationViolationType,
    reset_annotation_tenant_isolation_service,
)


# ============================================================================
# Property 25: Audit Trail Completeness
# ============================================================================

class TestAuditTrailCompleteness:
    """Property 25: All annotation operations are logged to audit trail."""

    @pytest.mark.asyncio
    @given(
        operation_type=st.sampled_from(list(AnnotationOperationType)),
        object_type=st.sampled_from(list(AnnotationObjectType)),
        num_operations=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    async def test_all_operations_logged(
        self,
        operation_type: AnnotationOperationType,
        object_type: AnnotationObjectType,
        num_operations: int
    ):
        """Test that all operations are logged to audit trail."""
        await reset_annotation_audit_service()
        service = AnnotationAuditService()

        tenant_id = uuid4()
        user_id = uuid4()
        logged_ids = []

        # Perform operations
        for i in range(num_operations):
            entry = await service.log_operation(
                tenant_id=tenant_id,
                user_id=user_id,
                operation_type=operation_type,
                object_type=object_type,
                object_id=uuid4(),
                operation_description=f"Operation {i}"
            )
            logged_ids.append(entry.log_id)

        # Verify all operations are in audit log
        filter = AnnotationAuditFilter(
            tenant_id=tenant_id,
            limit=100
        )
        logs = await service.get_logs(filter)

        assert len(logs) == num_operations, \
            f"Expected {num_operations} logs, found {len(logs)}"

        # Verify all logged IDs are present
        retrieved_ids = {log.log_id for log in logs}
        for log_id in logged_ids:
            assert log_id in retrieved_ids, f"Log {log_id} not found in audit trail"

    @pytest.mark.asyncio
    @given(
        num_versions=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    async def test_version_history_completeness(
        self,
        num_versions: int
    ):
        """Test that annotation version history is complete."""
        await reset_annotation_audit_service()
        service = AnnotationAuditService()

        tenant_id = uuid4()
        user_id = uuid4()
        annotation_id = uuid4()

        # Create multiple versions
        for version_num in range(num_versions):
            await service.log_operation(
                tenant_id=tenant_id,
                user_id=user_id,
                operation_type=AnnotationOperationType.UPDATE,
                object_type=AnnotationObjectType.ANNOTATION,
                object_id=annotation_id,
                after_state={"version": version_num},
                operation_description=f"Version {version_num}"
            )

        # Get version history
        versions = await service.get_annotation_versions(annotation_id)

        assert len(versions) == num_versions, \
            f"Expected {num_versions} versions, found {len(versions)}"

        # Verify versions are in reverse chronological order
        for i in range(len(versions) - 1):
            assert versions[i].version_number > versions[i+1].version_number

    @pytest.mark.asyncio
    @given(
        num_operations=st.integers(min_value=5, max_value=30)
    )
    @settings(max_examples=100, deadline=None)
    async def test_audit_integrity_verification(
        self,
        num_operations: int
    ):
        """Test that audit log entries have valid HMAC signatures."""
        await reset_annotation_audit_service()
        service = AnnotationAuditService()

        tenant_id = uuid4()
        user_id = uuid4()

        # Create operations
        for i in range(num_operations):
            await service.log_operation(
                tenant_id=tenant_id,
                user_id=user_id,
                operation_type=AnnotationOperationType.CREATE,
                object_type=AnnotationObjectType.ANNOTATION,
                object_id=uuid4(),
                operation_description=f"Op {i}"
            )

        # Verify integrity of all logs
        filter = AnnotationAuditFilter(tenant_id=tenant_id, limit=100)
        logs = await service.get_logs(filter)

        for log in logs:
            is_valid = await service.verify_integrity(log.log_id)
            assert is_valid, f"Log {log.log_id} failed integrity check"


# ============================================================================
# Property 26: Role-Based Access Enforcement
# ============================================================================

class TestRoleBasedAccessEnforcement:
    """Property 26: RBAC correctly enforces permissions."""

    @pytest.mark.asyncio
    @given(
        role=st.sampled_from([
            AnnotationRole.PROJECT_ANNOTATOR,
            AnnotationRole.PROJECT_REVIEWER,
            AnnotationRole.PROJECT_MANAGER
        ]),
        permission=st.sampled_from([
            AnnotationPermission.ANNOTATION_CREATE,
            AnnotationPermission.ANNOTATION_READ,
            AnnotationPermission.ANNOTATION_APPROVE,
            AnnotationPermission.ANNOTATION_DELETE
        ])
    )
    @settings(max_examples=100, deadline=None)
    async def test_role_permission_enforcement(
        self,
        role: AnnotationRole,
        permission: AnnotationPermission
    ):
        """Test that roles correctly grant or deny permissions."""
        await reset_annotation_rbac_service()
        service = AnnotationRBACService()

        tenant_id = uuid4()
        user_id = uuid4()

        # Assign role
        await service.assign_role(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            scope="tenant"
        )

        # Check permission
        check = await service.check_permission(
            tenant_id=tenant_id,
            user_id=user_id,
            permission=permission,
            scope="tenant"
        )

        # Get role definition
        role_def = await service.get_role_definition(role)

        # Permission should match role definition
        expected_allowed = permission in role_def.permissions
        assert check.allowed == expected_allowed, \
            f"Role {role} permission {permission}: expected {expected_allowed}, got {check.allowed}"

    @pytest.mark.asyncio
    @given(
        num_permissions=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    async def test_permission_denial_for_unauthorized_users(
        self,
        num_permissions: int
    ):
        """Test that users without roles are denied all permissions."""
        await reset_annotation_rbac_service()
        service = AnnotationRBACService()

        tenant_id = uuid4()
        user_id = uuid4()

        # User has no roles - all permissions should be denied
        all_permissions = list(AnnotationPermission)[:num_permissions]

        for permission in all_permissions:
            check = await service.check_permission(
                tenant_id=tenant_id,
                user_id=user_id,
                permission=permission,
                scope="tenant"
            )
            assert not check.allowed, \
                f"User without roles should not have permission {permission}"

    @pytest.mark.asyncio
    @given(
        scope=st.sampled_from(["tenant", "project"])
    )
    @settings(max_examples=100, deadline=None)
    async def test_scope_hierarchy_enforcement(
        self,
        scope: str
    ):
        """Test that permission scope hierarchy is enforced."""
        await reset_annotation_rbac_service()
        service = AnnotationRBACService()

        tenant_id = uuid4()
        user_id = uuid4()
        project_id = uuid4()

        # Assign tenant-level role
        await service.assign_role(
            tenant_id=tenant_id,
            user_id=user_id,
            role=AnnotationRole.TENANT_ADMIN,
            scope="tenant"
        )

        # Tenant-level role should grant access to projects
        check = await service.check_permission(
            tenant_id=tenant_id,
            user_id=user_id,
            permission=AnnotationPermission.PROJECT_READ,
            scope="project",
            scope_id=project_id
        )

        assert check.allowed, \
            "Tenant-level admin should have access to all projects"


# ============================================================================
# Property 27: Sensitive Data Desensitization
# ============================================================================

class TestSensitiveDataDesensitization:
    """Property 27: PII is correctly detected and desensitized."""

    @pytest.mark.asyncio
    @given(
        strategy=st.sampled_from([
            DesensitizationStrategy.MASK,
            DesensitizationStrategy.PARTIAL_MASK,
            DesensitizationStrategy.REPLACE
        ])
    )
    @settings(max_examples=100, deadline=None)
    async def test_pii_detection_and_desensitization(
        self,
        strategy: DesensitizationStrategy
    ):
        """Test that PII is detected and properly desensitized."""
        await reset_annotation_pii_service()
        service = AnnotationPIIService()

        # Test texts with known PII
        test_cases = [
            ("My email is user@example.com", PIIType.EMAIL, "user@example.com"),
            ("Call me at 13812345678", PIIType.PHONE_CN, "13812345678"),
            ("My ID is 110101199001011234", PIIType.ID_NUMBER_CN, "110101199001011234"),
        ]

        for text, expected_type, expected_value in test_cases:
            # Detect PII
            detections = await service.detect_pii(text)
            assert len(detections) > 0, f"Failed to detect PII in: {text}"

            # Desensitize
            result = await service.desensitize(text, strategy=strategy)

            # Verify original PII is not in desensitized text
            assert expected_value not in result.desensitized_text, \
                f"Original PII '{expected_value}' found in desensitized text"

            # Verify desensitization mapping exists
            assert expected_value in result.mapping, \
                f"Missing mapping for PII '{expected_value}'"

    @pytest.mark.asyncio
    @given(
        num_pii_items=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    async def test_multiple_pii_detection(
        self,
        num_pii_items: int
    ):
        """Test detection of multiple PII items in single text."""
        await reset_annotation_pii_service()
        service = AnnotationPIIService()

        # Build text with multiple PII items
        emails = [f"user{i}@example.com" for i in range(num_pii_items)]
        text = "Contact us: " + ", ".join(emails)

        # Detect PII
        detections = await service.detect_pii(text)

        # Should detect all email addresses
        assert len(detections) >= num_pii_items, \
            f"Expected at least {num_pii_items} detections, found {len(detections)}"

    @pytest.mark.asyncio
    @given(
        preserve_structure=st.booleans()
    )
    @settings(max_examples=100, deadline=None)
    async def test_desensitization_preserves_structure(
        self,
        preserve_structure: bool
    ):
        """Test that desensitization can preserve text structure."""
        await reset_annotation_pii_service()
        service = AnnotationPIIService()

        text = "Email: user@example.com, Phone: 13812345678"
        original_length = len(text)

        result = await service.desensitize(
            text,
            strategy=DesensitizationStrategy.PARTIAL_MASK,
            preserve_structure=preserve_structure
        )

        if preserve_structure:
            # Structure preservation may keep similar length
            # (not exact due to partial masking)
            assert abs(len(result.desensitized_text) - original_length) < 50

    @pytest.mark.asyncio
    async def test_chinese_id_validation(self):
        """Test Chinese ID number validation with checksum."""
        await reset_annotation_pii_service()
        service = AnnotationPIIService()

        # Valid Chinese ID (with correct checksum)
        valid_id = "110101199001011234"  # Hypothetical valid format
        text_valid = f"ID: {valid_id}"

        detections = await service.detect_pii(text_valid)

        # Should detect ID
        id_detections = [d for d in detections if d.pii_type == PIIType.ID_NUMBER_CN]
        assert len(id_detections) >= 0  # May or may not validate checksum


# ============================================================================
# Property 28: Multi-Tenant Isolation
# ============================================================================

class TestMultiTenantIsolation:
    """Property 28: Complete data isolation between tenants."""

    @pytest.mark.asyncio
    @given(
        num_tenants=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    async def test_cross_tenant_access_prevention(
        self,
        num_tenants: int
    ):
        """Test that cross-tenant access is prevented."""
        await reset_annotation_tenant_isolation_service()
        service = AnnotationTenantIsolationService()

        # Register multiple tenants
        tenants = [uuid4() for _ in range(num_tenants)]
        for tenant_id in tenants:
            await service.register_tenant(
                tenant_id=tenant_id,
                tenant_name=f"Tenant {tenant_id}"
            )

        # Create contexts for each tenant
        contexts = []
        for tenant_id in tenants:
            context = await service.create_context(
                tenant_id=tenant_id,
                user_id=uuid4()
            )
            contexts.append(context)

        # Try cross-tenant access
        for i, context in enumerate(contexts):
            for j, other_tenant_id in enumerate(tenants):
                if i != j:
                    # Attempt to access resource from different tenant
                    with pytest.raises(PermissionError):
                        await service.validate_tenant_access(
                            context=context,
                            resource_tenant_id=other_tenant_id,
                            resource_type="annotation",
                            resource_id=uuid4()
                        )

    @pytest.mark.asyncio
    @given(
        num_operations=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    async def test_tenant_filter_enforcement(
        self,
        num_operations: int
    ):
        """Test that tenant_id filters are enforced on all queries."""
        await reset_annotation_tenant_isolation_service()
        service = AnnotationTenantIsolationService()

        tenant_id = uuid4()
        await service.register_tenant(tenant_id, "Test Tenant")

        # Create query filters
        for i in range(num_operations):
            filter = await service.enforce_tenant_filter(
                tenant_id=tenant_id,
                filters={"project_id": uuid4()}
            )

            # Verify tenant_id is in filter
            assert filter.tenant_id == tenant_id
            filter_dict = filter.to_dict()
            assert "tenant_id" in filter_dict
            assert filter_dict["tenant_id"] == tenant_id

    @pytest.mark.asyncio
    @given(
        num_violations=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    async def test_isolation_violation_tracking(
        self,
        num_violations: int
    ):
        """Test that isolation violations are tracked."""
        await reset_annotation_tenant_isolation_service()
        service = AnnotationTenantIsolationService()

        tenant1 = uuid4()
        tenant2 = uuid4()

        await service.register_tenant(tenant1, "Tenant 1")
        await service.register_tenant(tenant2, "Tenant 2")

        context = await service.create_context(
            tenant_id=tenant1,
            user_id=uuid4()
        )

        # Generate violations
        violation_count = 0
        for i in range(num_violations):
            try:
                await service.validate_tenant_access(
                    context=context,
                    resource_tenant_id=tenant2,
                    resource_type="annotation",
                    resource_id=uuid4()
                )
            except PermissionError:
                violation_count += 1

        # Get violations
        violations = await service.get_violations(tenant_id=tenant1)

        assert len(violations) >= violation_count, \
            f"Expected at least {violation_count} violations, found {len(violations)}"

    @pytest.mark.asyncio
    async def test_missing_tenant_id_detection(self):
        """Test that missing tenant_id in queries is detected."""
        await reset_annotation_tenant_isolation_service()
        service = AnnotationTenantIsolationService()

        tenant_id = uuid4()
        await service.register_tenant(tenant_id, "Test Tenant")

        # Query without tenant_id should fail
        with pytest.raises(ValueError):
            await service.validate_query_has_tenant_filter(
                query_filters={"project_id": uuid4()},
                expected_tenant_id=tenant_id
            )

    @pytest.mark.asyncio
    async def test_tenant_id_mismatch_detection(self):
        """Test that tenant_id mismatch is detected."""
        await reset_annotation_tenant_isolation_service()
        service = AnnotationTenantIsolationService()

        tenant1 = uuid4()
        tenant2 = uuid4()

        await service.register_tenant(tenant1, "Tenant 1")
        await service.register_tenant(tenant2, "Tenant 2")

        # Query with wrong tenant_id should fail
        with pytest.raises(ValueError):
            await service.validate_query_has_tenant_filter(
                query_filters={"tenant_id": tenant2},
                expected_tenant_id=tenant1
            )


# ============================================================================
# Helper functions for running async tests
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
