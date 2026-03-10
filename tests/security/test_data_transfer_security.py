"""
Tests for Data Transfer Security Middleware

Tests security checks to prevent privilege escalation attacks.
"""

import pytest
from src.security.data_transfer_security import (
    DataTransferSecurityMiddleware,
    SecurityException
)
from src.models.data_transfer import (
    DataTransferRequest,
    DataAttributes,
    TransferRecord
)
from src.services.permission_service import UserRole


def _make_request(**overrides):
    """Helper to create a transfer request with optional overrides."""
    defaults = dict(
        source_type="structuring",
        source_id="test-source-123",
        target_state="temp_stored",
        data_attributes=DataAttributes(
            category="test_category",
            tags=["test"],
            quality_score=0.8,
            description="Test transfer"
        ),
        records=[
            TransferRecord(
                id="record-1",
                content={"field1": "value1"},
                metadata={"source": "test"}
            )
        ]
    )
    defaults.update(overrides)
    return DataTransferRequest(**defaults)


@pytest.fixture
def security_middleware():
    """Create security middleware instance."""
    return DataTransferSecurityMiddleware()


@pytest.fixture
def valid_request():
    """Create a valid transfer request."""
    return _make_request()


class TestForbiddenFieldsDetection:
    """Test detection of forbidden fields that could bypass security.
    
    Pydantic models prevent adding fields that don't exist in the schema,
    providing the first line of defense. The middleware adds defense-in-depth.
    """

    @pytest.mark.parametrize("field_name", [
        "force_approve",
        "bypass_permission",
        "skip_approval",
        "override_role",
        "admin_override",
        "force_admin",
        "bypass_check",
        "skip_validation",
    ])
    def test_pydantic_prevents_forbidden_field(self, valid_request, field_name):
        """Pydantic should prevent adding any forbidden field to request."""
        with pytest.raises(ValueError) as exc_info:
            setattr(valid_request, field_name, True)
        assert "has no field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_valid_request_passes(self, security_middleware, valid_request):
        """Valid request without forbidden fields should pass."""
        await security_middleware.verify_no_privilege_escalation(
            request=valid_request,
            current_user_id="user-123",
            current_user_role=UserRole.USER
        )


class TestRoleTamperingDetection:
    """Test detection of role tampering attempts."""

    @pytest.mark.asyncio
    async def test_pydantic_prevents_role_tampering(self, valid_request):
        """Pydantic should prevent adding user_role field to request."""
        with pytest.raises(ValueError) as exc_info:
            valid_request.user_role = "admin"
        assert "has no field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pydantic_prevents_role_field_in_attributes(self, valid_request):
        """Pydantic should prevent adding role field to data_attributes."""
        with pytest.raises(ValueError) as exc_info:
            valid_request.data_attributes.role = "admin"
        assert "has no field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_valid_request_without_role_passes(self, security_middleware, valid_request):
        """Should pass when request doesn't contain role field."""
        await security_middleware.verify_no_privilege_escalation(
            request=valid_request,
            current_user_id="user-123",
            current_user_role=UserRole.USER
        )


class TestProtectedMetadataDetection:
    """Test detection of protected metadata manipulation."""

    @pytest.mark.parametrize("field_name,field_value", [
        ("approved_by", "admin-123"),
        ("approved_at", "2026-01-01T00:00:00Z"),
        ("system_approved", True),
        ("internal_transfer", True),
        ("bypass_audit", True),
        ("skip_log", True),
    ])
    @pytest.mark.asyncio
    async def test_detect_protected_metadata_field(
        self, security_middleware, valid_request, field_name, field_value
    ):
        """Should detect any protected metadata field in record metadata."""
        valid_request.records[0].metadata[field_name] = field_value

        with pytest.raises(SecurityException) as exc_info:
            await security_middleware.verify_no_privilege_escalation(
                request=valid_request,
                current_user_id="user-123",
                current_user_role=UserRole.USER
            )
        assert field_name in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_normal_metadata_passes(self, security_middleware, valid_request):
        """Normal metadata should pass security check."""
        valid_request.records[0].metadata["custom_field"] = "custom_value"
        valid_request.records[0].metadata["source"] = "test"

        await security_middleware.verify_no_privilege_escalation(
            request=valid_request,
            current_user_id="user-123",
            current_user_role=UserRole.USER
        )


class TestApprovalBypassDetection:
    """Test detection of approval bypass attempts."""

    @pytest.mark.parametrize("pattern", [
        "pre_approved",
        "auto_approved",
        "approved",
        "no_approval_needed",
        "approval_skipped",
    ])
    @pytest.mark.asyncio
    async def test_remove_suspicious_approval_metadata(
        self, security_middleware, valid_request, pattern
    ):
        """Should remove each suspicious approval-related metadata pattern."""
        valid_request.records[0].metadata[pattern] = True

        await security_middleware.verify_no_privilege_escalation(
            request=valid_request,
            current_user_id="user-123",
            current_user_role=UserRole.USER
        )
        assert pattern not in valid_request.records[0].metadata


class TestRequestIntegrityValidation:
    """Test request integrity validation."""

    @pytest.mark.asyncio
    async def test_invalid_source_type(self, security_middleware, valid_request):
        """Should reject invalid source_type."""
        valid_request.source_type = "invalid_source"

        with pytest.raises(SecurityException) as exc_info:
            await security_middleware.validate_request_integrity(valid_request)
        assert "invalid source_type" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_invalid_target_state(self, security_middleware, valid_request):
        """Should reject invalid target_state."""
        valid_request.target_state = "invalid_state"

        with pytest.raises(SecurityException) as exc_info:
            await security_middleware.validate_request_integrity(valid_request)
        assert "invalid target_state" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_empty_records(self, security_middleware, valid_request):
        """Should reject request with no records."""
        valid_request.records = []

        with pytest.raises(SecurityException) as exc_info:
            await security_middleware.validate_request_integrity(valid_request)
        assert "at least one record" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_too_many_records(self, security_middleware, valid_request):
        """Should reject request with too many records (>10000)."""
        valid_request.records = [
            TransferRecord(id=f"r-{i}", content={"f": "v"}, metadata={})
            for i in range(10001)
        ]

        with pytest.raises(SecurityException) as exc_info:
            await security_middleware.validate_request_integrity(valid_request)
        assert "too many records" in str(exc_info.value).lower()

    @pytest.mark.parametrize("source_type", [
        "structuring", "augmentation", "sync",
    ])
    @pytest.mark.asyncio
    async def test_valid_source_types_pass(self, security_middleware, source_type):
        """All model-allowed source_types should pass integrity check."""
        request = _make_request(source_type=source_type)
        await security_middleware.validate_request_integrity(request)

    @pytest.mark.parametrize("target_state", [
        "temp_stored", "in_sample_library", "annotation_pending",
    ])
    @pytest.mark.asyncio
    async def test_valid_target_states_pass(self, security_middleware, target_state):
        """All legitimate target_states should pass integrity check."""
        request = _make_request(target_state=target_state)
        await security_middleware.validate_request_integrity(request)

    @pytest.mark.asyncio
    async def test_valid_request_passes_integrity_check(self, security_middleware, valid_request):
        """Valid request should pass integrity check."""
        await security_middleware.validate_request_integrity(valid_request)


class TestAdminBypassAttempts:
    """Test that even admins cannot bypass security checks."""

    @pytest.mark.parametrize("field_name", [
        "force_approve", "bypass_permission", "skip_approval",
    ])
    def test_admin_cannot_use_forbidden_fields(self, valid_request, field_name):
        """Admin should also be blocked from using forbidden fields."""
        with pytest.raises(ValueError) as exc_info:
            setattr(valid_request, field_name, True)
        assert "has no field" in str(exc_info.value)

    @pytest.mark.parametrize("protected_field", [
        "approved_by", "system_approved", "bypass_audit", "skip_log",
    ])
    @pytest.mark.asyncio
    async def test_admin_cannot_set_protected_metadata(
        self, security_middleware, valid_request, protected_field
    ):
        """Admin should also be blocked from setting any protected metadata."""
        valid_request.records[0].metadata[protected_field] = True

        with pytest.raises(SecurityException):
            await security_middleware.verify_no_privilege_escalation(
                request=valid_request,
                current_user_id="admin-123",
                current_user_role=UserRole.ADMIN
            )

    @pytest.mark.asyncio
    async def test_admin_approval_bypass_metadata_removed(
        self, security_middleware, valid_request
    ):
        """Admin's suspicious approval metadata should also be removed."""
        valid_request.records[0].metadata["pre_approved"] = True

        await security_middleware.verify_no_privilege_escalation(
            request=valid_request,
            current_user_id="admin-123",
            current_user_role=UserRole.ADMIN
        )
        assert "pre_approved" not in valid_request.records[0].metadata


class TestMultipleRecordsMixedMetadata:
    """Test requests with multiple records where some are clean and some suspicious."""

    @pytest.mark.asyncio
    async def test_protected_field_in_second_record_detected(self, security_middleware):
        """Should detect protected metadata even if only in a later record."""
        request = _make_request(records=[
            TransferRecord(id="clean-1", content={"a": 1}, metadata={"source": "ok"}),
            TransferRecord(id="bad-2", content={"b": 2}, metadata={"system_approved": True}),
        ])

        with pytest.raises(SecurityException) as exc_info:
            await security_middleware.verify_no_privilege_escalation(
                request=request,
                current_user_id="user-1",
                current_user_role=UserRole.USER
            )
        assert "system_approved" in str(exc_info.value)
        assert "1" in str(exc_info.value)  # record index 1

    @pytest.mark.asyncio
    async def test_suspicious_metadata_removed_from_all_records(self, security_middleware):
        """Should remove suspicious approval metadata from every record."""
        request = _make_request(records=[
            TransferRecord(id="r-0", content={"a": 1}, metadata={"pre_approved": True}),
            TransferRecord(id="r-1", content={"b": 2}, metadata={"source": "clean"}),
            TransferRecord(id="r-2", content={"c": 3}, metadata={"auto_approved": True}),
        ])

        await security_middleware.verify_no_privilege_escalation(
            request=request,
            current_user_id="user-1",
            current_user_role=UserRole.USER
        )

        assert "pre_approved" not in request.records[0].metadata
        assert "auto_approved" not in request.records[2].metadata
        # Clean record untouched
        assert request.records[1].metadata == {"source": "clean"}

    @pytest.mark.asyncio
    async def test_all_clean_records_pass(self, security_middleware):
        """Multiple records with only normal metadata should pass."""
        request = _make_request(records=[
            TransferRecord(id=f"r-{i}", content={"v": i}, metadata={"source": "ok"})
            for i in range(5)
        ])

        await security_middleware.verify_no_privilege_escalation(
            request=request,
            current_user_id="user-1",
            current_user_role=UserRole.DATA_ANALYST
        )

    @pytest.mark.asyncio
    async def test_record_with_none_metadata_passes(self, security_middleware):
        """Records with None metadata should not cause errors."""
        request = _make_request(records=[
            TransferRecord(id="r-0", content={"a": 1}, metadata=None),
            TransferRecord(id="r-1", content={"b": 2}, metadata={"source": "ok"}),
        ])

        await security_middleware.verify_no_privilege_escalation(
            request=request,
            current_user_id="user-1",
            current_user_role=UserRole.USER
        )
