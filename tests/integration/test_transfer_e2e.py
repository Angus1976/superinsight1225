"""
End-to-end integration tests for the complete data transfer flow.

Tests the full API endpoints using FastAPI TestClient with mocked
database sessions and auth dependencies.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.data_lifecycle_api import router
from src.api.auth_simple import SimpleUser, get_current_user
from src.database.connection import get_db_session
from src.services.permission_service import UserRole, PermissionResult
from src.models.approval import ApprovalRequest, ApprovalStatus
from src.security.data_transfer_security import SecurityException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(is_superuser: bool = True, user_id: str = "user-1") -> SimpleUser:
    return SimpleUser(
        user_id=user_id,
        email="test@example.com",
        username="tester",
        name="Test User",
        is_active=True,
        is_superuser=is_superuser,
    )


def _transfer_payload(
    source_type="structuring",
    target_state="temp_stored",
    source_id="src-123",
    records=None,
):
    if records is None:
        records = [{"id": "r1", "content": {"k": "v"}, "metadata": {}}]
    return {
        "source_type": source_type,
        "source_id": source_id,
        "target_state": target_state,
        "data_attributes": {
            "category": "test",
            "tags": ["a"],
            "quality_score": 0.8,
            "description": "test desc",
        },
        "records": records,
        "request_approval": False,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.flush = Mock()
    db.bulk_save_objects = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def admin_user():
    return _make_user(is_superuser=True, user_id="admin-1")


@pytest.fixture
def regular_user():
    return _make_user(is_superuser=False, user_id="user-2")


@pytest.fixture
def app_with_admin(mock_db, admin_user):
    """FastAPI app with admin auth override."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db_session] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: admin_user
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client_admin(app_with_admin):
    return TestClient(app_with_admin)


@pytest.fixture
def app_with_regular(mock_db, regular_user):
    """FastAPI app with regular (non-superuser) auth override."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db_session] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: regular_user
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client_regular(app_with_regular):
    return TestClient(app_with_regular)


@pytest.fixture
def app_no_auth(mock_db):
    """FastAPI app with no auth override (tests 401)."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db_session] = lambda: mock_db
    # Do NOT override get_current_user — it will require a real token
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth(app_no_auth):
    return TestClient(app_no_auth)


# ---------------------------------------------------------------------------
# 1. POST /transfer — successful transfer to temp_stored
# ---------------------------------------------------------------------------

class TestTransferToTempStored:
    """Admin transfers data to temp_stored — should succeed directly."""

    @patch("src.api.data_lifecycle_api.DataTransferSecurityMiddleware")
    @patch("src.api.data_lifecycle_api.DataTransferService")
    def test_transfer_to_temp_stored_success(
        self, MockService, MockSecurity, client_admin
    ):
        mock_svc = MockService.return_value
        mock_svc.transfer = AsyncMock(return_value={
            "success": True,
            "transferred_count": 1,
            "lifecycle_ids": ["id-1"],
            "target_state": "temp_stored",
            "message": "ok",
            "navigation_url": "/data-lifecycle/temp-data",
        })
        mock_sec = MockSecurity.return_value
        mock_sec.verify_no_privilege_escalation = AsyncMock()
        mock_sec.validate_request_integrity = AsyncMock()

        resp = client_admin.post(
            "/api/data-lifecycle/transfer",
            json=_transfer_payload(target_state="temp_stored"),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["transferred_count"] == 1
        assert "lifecycle_ids" in body


# ---------------------------------------------------------------------------
# 2. POST /transfer — successful transfer to in_sample_library
# ---------------------------------------------------------------------------

class TestTransferToSampleLibrary:
    """Admin transfers data to sample library — should succeed."""

    @patch("src.api.data_lifecycle_api.DataTransferSecurityMiddleware")
    @patch("src.api.data_lifecycle_api.DataTransferService")
    def test_transfer_to_sample_library_success(
        self, MockService, MockSecurity, client_admin
    ):
        mock_svc = MockService.return_value
        mock_svc.transfer = AsyncMock(return_value={
            "success": True,
            "transferred_count": 2,
            "lifecycle_ids": ["id-1", "id-2"],
            "target_state": "in_sample_library",
            "message": "ok",
            "navigation_url": "/data-lifecycle/sample-library",
        })
        mock_sec = MockSecurity.return_value
        mock_sec.verify_no_privilege_escalation = AsyncMock()
        mock_sec.validate_request_integrity = AsyncMock()

        payload = _transfer_payload(
            target_state="in_sample_library",
            records=[
                {"id": "r1", "content": {"a": 1}},
                {"id": "r2", "content": {"b": 2}},
            ],
        )
        resp = client_admin.post("/api/data-lifecycle/transfer", json=payload)

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["target_state"] == "in_sample_library"
        assert body["transferred_count"] == 2


# ---------------------------------------------------------------------------
# 3. POST /transfer — successful transfer to annotation_pending
# ---------------------------------------------------------------------------

class TestTransferToAnnotationPending:
    """Admin transfers data to annotation_pending — should succeed."""

    @patch("src.api.data_lifecycle_api.DataTransferSecurityMiddleware")
    @patch("src.api.data_lifecycle_api.DataTransferService")
    def test_transfer_to_annotation_pending_success(
        self, MockService, MockSecurity, client_admin
    ):
        mock_svc = MockService.return_value
        mock_svc.transfer = AsyncMock(return_value={
            "success": True,
            "transferred_count": 1,
            "lifecycle_ids": ["id-1"],
            "target_state": "annotation_pending",
            "message": "ok",
            "navigation_url": "/data-lifecycle/annotation-pending",
        })
        mock_sec = MockSecurity.return_value
        mock_sec.verify_no_privilege_escalation = AsyncMock()
        mock_sec.validate_request_integrity = AsyncMock()

        resp = client_admin.post(
            "/api/data-lifecycle/transfer",
            json=_transfer_payload(target_state="annotation_pending"),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["target_state"] == "annotation_pending"


# ---------------------------------------------------------------------------
# 4. POST /transfer — transfer requiring approval (non-admin to sample library)
# ---------------------------------------------------------------------------

class TestTransferRequiresApproval:
    """Regular user transferring to sample library triggers approval."""

    @patch("src.api.data_lifecycle_api.DataTransferSecurityMiddleware")
    @patch("src.api.data_lifecycle_api.DataTransferService")
    def test_transfer_requires_approval(
        self, MockService, MockSecurity, client_regular
    ):
        mock_svc = MockService.return_value
        mock_svc.transfer = AsyncMock(return_value={
            "success": True,
            "approval_required": True,
            "approval_id": "appr-1",
            "message": "pending",
            "estimated_approval_time": "2-3 business days",
        })
        mock_sec = MockSecurity.return_value
        mock_sec.verify_no_privilege_escalation = AsyncMock()
        mock_sec.validate_request_integrity = AsyncMock()

        resp = client_regular.post(
            "/api/data-lifecycle/transfer",
            json=_transfer_payload(target_state="in_sample_library"),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["approval_required"] is True
        assert body["approval_id"] == "appr-1"


# ---------------------------------------------------------------------------
# 5. POST /transfer — permission denied (403)
# ---------------------------------------------------------------------------

class TestTransferPermissionDenied:
    """Transfer raises PermissionError → 403."""

    @patch("src.api.data_lifecycle_api.DataTransferSecurityMiddleware")
    @patch("src.api.data_lifecycle_api.DataTransferService")
    def test_transfer_permission_denied(
        self, MockService, MockSecurity, client_regular
    ):
        mock_svc = MockService.return_value
        mock_svc.transfer = AsyncMock(
            side_effect=PermissionError("Not allowed")
        )
        mock_sec = MockSecurity.return_value
        mock_sec.verify_no_privilege_escalation = AsyncMock()
        mock_sec.validate_request_integrity = AsyncMock()

        resp = client_regular.post(
            "/api/data-lifecycle/transfer",
            json=_transfer_payload(target_state="in_sample_library"),
        )

        assert resp.status_code == 403
        body = resp.json()["detail"]
        assert body["error_code"] == "PERMISSION_DENIED"


# ---------------------------------------------------------------------------
# 6. POST /transfer — invalid request (400)
# ---------------------------------------------------------------------------

class TestTransferInvalidRequest:
    """Transfer raises ValueError → 400."""

    @patch("src.api.data_lifecycle_api.DataTransferSecurityMiddleware")
    @patch("src.api.data_lifecycle_api.DataTransferService")
    def test_transfer_invalid_source(
        self, MockService, MockSecurity, client_admin
    ):
        mock_svc = MockService.return_value
        mock_svc.transfer = AsyncMock(
            side_effect=ValueError("Source not found")
        )
        mock_sec = MockSecurity.return_value
        mock_sec.verify_no_privilege_escalation = AsyncMock()
        mock_sec.validate_request_integrity = AsyncMock()

        resp = client_admin.post(
            "/api/data-lifecycle/transfer",
            json=_transfer_payload(),
        )

        assert resp.status_code == 400
        body = resp.json()["detail"]
        assert body["error_code"] == "INVALID_SOURCE"

    def test_transfer_pydantic_validation_error(self, client_admin):
        """Missing required fields → 422 from Pydantic."""
        resp = client_admin.post(
            "/api/data-lifecycle/transfer",
            json={"source_type": "structuring"},  # incomplete
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 7. POST /batch-transfer — batch transfer success
# ---------------------------------------------------------------------------

class TestBatchTransferSuccess:
    """Admin batch transfer succeeds."""

    @patch("src.api.data_lifecycle_api.DataTransferSecurityMiddleware")
    @patch("src.api.data_lifecycle_api.DataTransferService")
    def test_batch_transfer_success(
        self, MockService, MockSecurity, client_admin
    ):
        mock_svc = MockService.return_value
        mock_svc.transfer = AsyncMock(return_value={
            "success": True,
            "transferred_count": 1,
            "lifecycle_ids": ["id-1"],
            "target_state": "temp_stored",
            "message": "ok",
            "navigation_url": "/data-lifecycle/temp-data",
        })
        mock_sec = MockSecurity.return_value
        mock_sec.verify_no_privilege_escalation = AsyncMock()
        mock_sec.validate_request_integrity = AsyncMock()

        batch = [
            _transfer_payload(source_id="s1"),
            _transfer_payload(source_id="s2"),
        ]
        resp = client_admin.post(
            "/api/data-lifecycle/batch-transfer", json=batch
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["total_transfers"] == 2
        assert body["successful_transfers"] == 2
        assert body["failed_transfers"] == 0
        assert len(body["results"]) == 2


# ---------------------------------------------------------------------------
# 8. POST /batch-transfer — permission denied for non-admin
# ---------------------------------------------------------------------------

class TestBatchTransferPermissionDenied:
    """Regular user cannot batch-transfer → 403."""

    def test_batch_transfer_forbidden_for_regular_user(self, client_regular):
        batch = [_transfer_payload()]
        resp = client_regular.post(
            "/api/data-lifecycle/batch-transfer", json=batch
        )

        assert resp.status_code == 403
        body = resp.json()["detail"]
        assert body["error_code"] == "PERMISSION_DENIED"


# ---------------------------------------------------------------------------
# 9. Accept-Language header for i18n response messages
# ---------------------------------------------------------------------------

class TestI18nResponseMessages:
    """Verify Accept-Language header affects response messages."""

    @patch("src.api.data_lifecycle_api.DataTransferSecurityMiddleware")
    @patch("src.api.data_lifecycle_api.DataTransferService")
    def test_chinese_message_with_zh_header(
        self, MockService, MockSecurity, client_admin
    ):
        mock_svc = MockService.return_value
        mock_svc.transfer = AsyncMock(return_value={
            "success": True,
            "transferred_count": 1,
            "lifecycle_ids": ["id-1"],
            "target_state": "temp_stored",
            "message": "placeholder",
            "navigation_url": "/data-lifecycle/temp-data",
        })
        mock_sec = MockSecurity.return_value
        mock_sec.verify_no_privilege_escalation = AsyncMock()
        mock_sec.validate_request_integrity = AsyncMock()

        resp = client_admin.post(
            "/api/data-lifecycle/transfer",
            json=_transfer_payload(),
            headers={"Accept-Language": "zh-CN"},
        )

        assert resp.status_code == 200
        body = resp.json()
        # Chinese message should contain Chinese characters
        assert "成功转存" in body["message"]

    @patch("src.api.data_lifecycle_api.DataTransferSecurityMiddleware")
    @patch("src.api.data_lifecycle_api.DataTransferService")
    def test_english_message_with_en_header(
        self, MockService, MockSecurity, client_admin
    ):
        mock_svc = MockService.return_value
        mock_svc.transfer = AsyncMock(return_value={
            "success": True,
            "transferred_count": 1,
            "lifecycle_ids": ["id-1"],
            "target_state": "temp_stored",
            "message": "placeholder",
            "navigation_url": "/data-lifecycle/temp-data",
        })
        mock_sec = MockSecurity.return_value
        mock_sec.verify_no_privilege_escalation = AsyncMock()
        mock_sec.validate_request_integrity = AsyncMock()

        resp = client_admin.post(
            "/api/data-lifecycle/transfer",
            json=_transfer_payload(),
            headers={"Accept-Language": "en-US"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "Successfully transferred" in body["message"]


# ---------------------------------------------------------------------------
# 10. Security middleware blocking privilege escalation attempts
# ---------------------------------------------------------------------------

class TestSecurityMiddleware:
    """Security middleware blocks privilege escalation."""

    @patch("src.api.data_lifecycle_api.DataTransferSecurityMiddleware")
    def test_privilege_escalation_blocked(
        self, MockSecurity, client_admin
    ):
        mock_sec = MockSecurity.return_value
        mock_sec.verify_no_privilege_escalation = AsyncMock(
            side_effect=SecurityException("Privilege escalation attempt detected")
        )

        resp = client_admin.post(
            "/api/data-lifecycle/transfer",
            json=_transfer_payload(),
        )

        assert resp.status_code == 403
        body = resp.json()["detail"]
        assert body["error_code"] == "SECURITY_VIOLATION"

    @patch("src.api.data_lifecycle_api.DataTransferSecurityMiddleware")
    def test_request_integrity_violation_blocked(
        self, MockSecurity, client_admin
    ):
        mock_sec = MockSecurity.return_value
        mock_sec.verify_no_privilege_escalation = AsyncMock()
        mock_sec.validate_request_integrity = AsyncMock(
            side_effect=SecurityException("Too many records")
        )

        resp = client_admin.post(
            "/api/data-lifecycle/transfer",
            json=_transfer_payload(),
        )

        assert resp.status_code == 403
        body = resp.json()["detail"]
        assert body["error_code"] == "SECURITY_VIOLATION"
