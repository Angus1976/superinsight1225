"""
End-to-end integration tests for the approval workflow API endpoints.

Tests cover:
1. GET /api/data-lifecycle/approvals - list approvals (admin vs regular user)
2. POST /api/data-lifecycle/approvals/{id}/approve - approve a request
3. POST /api/data-lifecycle/approvals/{id}/approve - reject a request
4. POST /api/data-lifecycle/approvals/{id}/approve - permission denied
5. GET /api/data-lifecycle/permissions/check - check user permissions
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.data_lifecycle_api import router
from src.api.auth_simple import SimpleUser, get_current_user
from src.database.connection import get_db_session
from src.services.permission_service import UserRole
from src.models.approval import ApprovalRequest, ApprovalStatus
from src.models.data_transfer import DataTransferRequest


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


def _make_approval(
    approval_id: str = "appr-1",
    requester_id: str = "user-2",
    status: ApprovalStatus = ApprovalStatus.PENDING,
    approver_id: str = None,
    approved_at: datetime = None,
    comment: str = None,
) -> ApprovalRequest:
    """Create a mock ApprovalRequest for testing."""
    return ApprovalRequest(
        id=approval_id,
        transfer_request=DataTransferRequest(
            source_type="structuring",
            source_id="src-123",
            target_state="in_sample_library",
            data_attributes={
                "category": "test",
                "tags": ["a"],
                "quality_score": 0.8,
                "description": "test desc",
            },
            records=[{"id": "r1", "content": {"k": "v"}, "metadata": {}}],
            request_approval=False,
        ),
        requester_id=requester_id,
        requester_role="user",
        status=status,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=7),
        approver_id=approver_id,
        approved_at=approved_at,
        comment=comment,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    db = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.flush = Mock()
    db.execute = Mock()
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
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db_session] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: regular_user
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client_regular(app_with_regular):
    return TestClient(app_with_regular)


# ---------------------------------------------------------------------------
# 1. GET /approvals — admin sees all approvals
# ---------------------------------------------------------------------------

class TestListApprovalsAdmin:
    """Admin can see all approval requests."""

    @patch("src.services.approval_service.ApprovalService.get_pending_approvals")
    def test_admin_lists_all_pending_approvals(
        self, mock_get_pending, client_admin
    ):
        mock_get_pending.return_value = [
            _make_approval(approval_id="appr-1", requester_id="user-2"),
            _make_approval(approval_id="appr-2", requester_id="user-3"),
        ]

        resp = client_admin.get("/api/data-lifecycle/approvals")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["approvals"]) == 2
        assert body["approvals"][0]["id"] == "appr-1"
        assert body["approvals"][1]["id"] == "appr-2"

    @patch("src.services.approval_service.ApprovalService.get_pending_approvals")
    def test_admin_lists_empty_approvals(
        self, mock_get_pending, client_admin
    ):
        mock_get_pending.return_value = []

        resp = client_admin.get("/api/data-lifecycle/approvals")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["approvals"]) == 0


# ---------------------------------------------------------------------------
# 2. GET /approvals — regular user sees only own approvals
# ---------------------------------------------------------------------------

class TestListApprovalsRegularUser:
    """Regular user can only see their own approval requests."""

    @patch("src.services.approval_service.ApprovalService.get_user_approval_requests")
    def test_regular_user_sees_own_approvals(
        self, mock_get_user, client_regular
    ):
        mock_get_user.return_value = [
            _make_approval(approval_id="appr-1", requester_id="user-2"),
        ]

        resp = client_regular.get("/api/data-lifecycle/approvals")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["approvals"]) == 1
        # Service was called with the current user's ID
        mock_get_user.assert_called_once()
        call_kwargs = mock_get_user.call_args
        assert call_kwargs.kwargs.get("user_id") == "user-2"

    def test_regular_user_cannot_view_other_users_approvals(
        self, client_regular
    ):
        """Regular user querying another user's approvals gets 403."""
        resp = client_regular.get(
            "/api/data-lifecycle/approvals",
            params={"user_id": "other-user-999"},
        )

        assert resp.status_code == 403
        body = resp.json()["detail"]
        assert body["error_code"] == "PERMISSION_DENIED"


# ---------------------------------------------------------------------------
# 3. POST /approvals/{id}/approve — approve a request (admin)
# ---------------------------------------------------------------------------

class TestApproveRequest:
    """Admin or data_manager can approve a pending request."""

    @patch("src.services.approval_service.ApprovalService.approve_request")
    def test_admin_approves_request(
        self, mock_approve, client_admin
    ):
        approved_approval = _make_approval(
            approval_id="appr-1",
            status=ApprovalStatus.APPROVED,
            approver_id="admin-1",
            approved_at=datetime.utcnow(),
            comment="Looks good",
        )
        mock_approve.return_value = approved_approval

        resp = client_admin.post(
            "/api/data-lifecycle/approvals/appr-1/approve",
            params={"approved": True, "comment": "Looks good"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["approval"]["id"] == "appr-1"
        assert body["approval"]["status"] == "approved"
        assert body["approval"]["comment"] == "Looks good"


# ---------------------------------------------------------------------------
# 4. POST /approvals/{id}/approve — reject a request
# ---------------------------------------------------------------------------

class TestRejectRequest:
    """Admin or data_manager can reject a pending request."""

    @patch("src.services.approval_service.ApprovalService.approve_request")
    def test_admin_rejects_request(
        self, mock_approve, client_admin
    ):
        rejected_approval = _make_approval(
            approval_id="appr-2",
            status=ApprovalStatus.REJECTED,
            approver_id="admin-1",
            approved_at=datetime.utcnow(),
            comment="Data quality insufficient",
        )
        mock_approve.return_value = rejected_approval

        resp = client_admin.post(
            "/api/data-lifecycle/approvals/appr-2/approve",
            params={"approved": False, "comment": "Data quality insufficient"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["approval"]["status"] == "rejected"
        assert body["approval"]["comment"] == "Data quality insufficient"

    @patch("src.services.approval_service.ApprovalService.approve_request")
    def test_approve_nonexistent_request_returns_404(
        self, mock_approve, client_admin
    ):
        mock_approve.side_effect = ValueError(
            "Approval request appr-999 not found"
        )

        resp = client_admin.post(
            "/api/data-lifecycle/approvals/appr-999/approve",
            params={"approved": True},
        )

        assert resp.status_code == 404
        body = resp.json()["detail"]
        assert body["error_code"] == "APPROVAL_NOT_FOUND"

    @patch("src.services.approval_service.ApprovalService.approve_request")
    def test_approve_expired_request_returns_400(
        self, mock_approve, client_admin
    ):
        mock_approve.side_effect = ValueError(
            "Approval request has expired"
        )

        resp = client_admin.post(
            "/api/data-lifecycle/approvals/appr-expired/approve",
            params={"approved": True},
        )

        assert resp.status_code == 400
        body = resp.json()["detail"]
        assert body["error_code"] == "APPROVAL_EXPIRED"


# ---------------------------------------------------------------------------
# 5. POST /approvals/{id}/approve — permission denied for regular user
# ---------------------------------------------------------------------------

class TestApprovePermissionDenied:
    """Regular users cannot approve or reject requests."""

    def test_regular_user_cannot_approve(self, client_regular):
        resp = client_regular.post(
            "/api/data-lifecycle/approvals/appr-1/approve",
            params={"approved": True},
        )

        assert resp.status_code == 403
        body = resp.json()["detail"]
        assert body["error_code"] == "PERMISSION_DENIED"
        assert "admin or data_manager" in body["details"].lower()

    def test_regular_user_cannot_reject(self, client_regular):
        resp = client_regular.post(
            "/api/data-lifecycle/approvals/appr-1/approve",
            params={"approved": False, "comment": "nope"},
        )

        assert resp.status_code == 403
        body = resp.json()["detail"]
        assert body["error_code"] == "PERMISSION_DENIED"


# ---------------------------------------------------------------------------
# 6. GET /permissions/check — check user permissions
# ---------------------------------------------------------------------------

class TestCheckPermissions:
    """Permission check endpoint returns correct results per role."""

    def test_admin_has_full_permission(self, client_admin):
        resp = client_admin.get(
            "/api/data-lifecycle/permissions/check",
            params={
                "source_type": "structuring",
                "target_state": "in_sample_library",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["allowed"] is True
        assert body["requires_approval"] is False
        assert body["user_role"] == "admin"

    def test_regular_user_requires_approval_for_sample_library(
        self, client_regular
    ):
        resp = client_regular.get(
            "/api/data-lifecycle/permissions/check",
            params={
                "source_type": "augmentation",
                "target_state": "in_sample_library",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["allowed"] is True
        assert body["requires_approval"] is True
        assert body["user_role"] == "user"

    def test_regular_user_allowed_temp_stored_no_approval(
        self, client_regular
    ):
        resp = client_regular.get(
            "/api/data-lifecycle/permissions/check",
            params={
                "source_type": "sync",
                "target_state": "temp_stored",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["allowed"] is True
        assert body["requires_approval"] is False

    def test_regular_user_batch_transfer_not_allowed(self, client_regular):
        resp = client_regular.get(
            "/api/data-lifecycle/permissions/check",
            params={
                "source_type": "structuring",
                "target_state": "temp_stored",
                "operation": "batch_transfer",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["allowed"] is False

    def test_invalid_source_type_returns_400(self, client_admin):
        resp = client_admin.get(
            "/api/data-lifecycle/permissions/check",
            params={
                "source_type": "invalid_type",
                "target_state": "temp_stored",
            },
        )

        assert resp.status_code == 400
        body = resp.json()["detail"]
        assert body["error_code"] == "INVALID_SOURCE_TYPE"

    def test_invalid_target_state_returns_400(self, client_admin):
        resp = client_admin.get(
            "/api/data-lifecycle/permissions/check",
            params={
                "source_type": "structuring",
                "target_state": "nonexistent_state",
            },
        )

        assert resp.status_code == 400
        body = resp.json()["detail"]
        assert body["error_code"] == "INVALID_TARGET_STATE"

    def test_admin_annotation_pending_permission(self, client_admin):
        resp = client_admin.get(
            "/api/data-lifecycle/permissions/check",
            params={
                "source_type": "annotation",
                "target_state": "annotation_pending",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["allowed"] is True
        assert body["requires_approval"] is False
