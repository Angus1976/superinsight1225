"""
Unit tests for Review API endpoints.

Tests all review workflow API endpoints including submission, assignment,
approval, rejection, and status retrieval.

Validates: Requirements 3.1, 3.2, 3.3, 12.3, 12.4, 12.5
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, MagicMock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.review_api import (
    router,
    SubmitReviewRequest,
    AssignReviewerRequest,
    ApproveDataRequest,
    RejectDataRequest
)
from src.services.review_service import (
    ReviewRequest,
    ApprovalResult,
    RejectionResult
)
from src.models.data_lifecycle import ReviewStatus, DataState


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_review_service():
    """Create a mock review service."""
    return Mock()


@pytest.fixture
def client(mock_review_service):
    """Create a test client with mocked dependencies."""
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    
    # Override dependency
    def override_get_review_service():
        return mock_review_service
    
    from src.api.review_api import get_review_service
    app.dependency_overrides[get_review_service] = override_get_review_service
    
    return TestClient(app)


@pytest.fixture
def sample_review_id():
    """Sample review ID."""
    return uuid4()


@pytest.fixture
def sample_data_id():
    """Sample data ID."""
    return str(uuid4())


# ============================================================================
# Test POST /api/reviews - Submit for Review
# ============================================================================

def test_submit_for_review_success(client, mock_review_service, sample_review_id, sample_data_id):
    """Test successful submission for review."""
    # Arrange
    submitted_at = datetime.utcnow()
    mock_review_request = ReviewRequest(
        id=sample_review_id,
        data_id=sample_data_id,
        submitter_id="user123",
        reviewer_id=None,
        status=ReviewStatus.PENDING,
        submitted_at=submitted_at
    )
    mock_review_service.submit_for_review.return_value = mock_review_request
    
    # Act
    response = client.post(
        "/api/reviews",
        json={
            "data_id": sample_data_id,
            "submitted_by": "user123"
        }
    )
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["review_id"] == str(sample_review_id)
    assert data["data_id"] == sample_data_id
    assert data["submitter_id"] == "user123"
    assert data["reviewer_id"] is None
    assert data["status"] == "pending"
    
    mock_review_service.submit_for_review.assert_called_once_with(
        data_id=sample_data_id,
        submitted_by="user123",
        reviewer_id=None
    )


def test_submit_for_review_with_reviewer(client, mock_review_service, sample_review_id, sample_data_id):
    """Test submission for review with immediate reviewer assignment."""
    # Arrange
    submitted_at = datetime.utcnow()
    mock_review_request = ReviewRequest(
        id=sample_review_id,
        data_id=sample_data_id,
        submitter_id="user123",
        reviewer_id="reviewer456",
        status=ReviewStatus.IN_PROGRESS,
        submitted_at=submitted_at
    )
    mock_review_service.submit_for_review.return_value = mock_review_request
    
    # Act
    response = client.post(
        "/api/reviews",
        json={
            "data_id": sample_data_id,
            "submitted_by": "user123",
            "reviewer_id": "reviewer456"
        }
    )
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["reviewer_id"] == "reviewer456"
    assert data["status"] == "in_progress"


def test_submit_for_review_data_not_found(client, mock_review_service, sample_data_id):
    """Test submission for review when data not found."""
    # Arrange
    mock_review_service.submit_for_review.side_effect = ValueError(
        f"Temporary data {sample_data_id} not found"
    )
    
    # Act
    response = client.post(
        "/api/reviews",
        json={
            "data_id": sample_data_id,
            "submitted_by": "user123"
        }
    )
    
    # Assert
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_submit_for_review_invalid_state(client, mock_review_service, sample_data_id):
    """Test submission for review when data not in valid state."""
    # Arrange
    mock_review_service.submit_for_review.side_effect = ValueError(
        "Data must be in TEMP_STORED state to submit for review"
    )
    
    # Act
    response = client.post(
        "/api/reviews",
        json={
            "data_id": sample_data_id,
            "submitted_by": "user123"
        }
    )
    
    # Assert
    assert response.status_code == 400
    assert "TEMP_STORED" in response.json()["detail"]


def test_submit_for_review_internal_error(client, mock_review_service, sample_data_id):
    """Test submission for review with internal error."""
    # Arrange
    mock_review_service.submit_for_review.side_effect = Exception("Database error")
    
    # Act
    response = client.post(
        "/api/reviews",
        json={
            "data_id": sample_data_id,
            "submitted_by": "user123"
        }
    )
    
    # Assert
    assert response.status_code == 500
    assert "Failed to submit for review" in response.json()["detail"]


# ============================================================================
# Test PUT /api/reviews/{id}/assign - Assign Reviewer
# ============================================================================

def test_assign_reviewer_success(client, mock_review_service, sample_review_id):
    """Test successful reviewer assignment."""
    # Arrange
    mock_review_service.assign_reviewer.return_value = None
    mock_review_service.get_review_status.return_value = {
        'review_id': str(sample_review_id),
        'data_id': str(sample_review_id),
        'state': 'under_review',
        'review_status': 'in_progress',
        'reviewer_id': 'reviewer456',
        'reviewed_at': None,
        'rejection_reason': None,
        'uploaded_by': 'user123',
        'uploaded_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    # Act
    response = client.put(
        f"/api/reviews/{sample_review_id}/assign",
        json={
            "reviewer_id": "reviewer456",
            "assigned_by": "admin789"
        }
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["review_id"] == str(sample_review_id)
    assert data["reviewer_id"] == "reviewer456"
    assert data["assigned_by"] == "admin789"
    assert data["status"] == "in_progress"
    
    mock_review_service.assign_reviewer.assert_called_once_with(
        review_id=str(sample_review_id),
        reviewer_id="reviewer456",
        assigned_by="admin789"
    )


def test_assign_reviewer_not_found(client, mock_review_service, sample_review_id):
    """Test reviewer assignment when review not found."""
    # Arrange
    mock_review_service.assign_reviewer.side_effect = ValueError(
        f"Review {sample_review_id} not found"
    )
    
    # Act
    response = client.put(
        f"/api/reviews/{sample_review_id}/assign",
        json={
            "reviewer_id": "reviewer456",
            "assigned_by": "admin789"
        }
    )
    
    # Assert
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_assign_reviewer_invalid_state(client, mock_review_service, sample_review_id):
    """Test reviewer assignment when review not in valid state."""
    # Arrange
    mock_review_service.assign_reviewer.side_effect = ValueError(
        "Data must be in UNDER_REVIEW state to assign reviewer"
    )
    
    # Act
    response = client.put(
        f"/api/reviews/{sample_review_id}/assign",
        json={
            "reviewer_id": "reviewer456",
            "assigned_by": "admin789"
        }
    )
    
    # Assert
    assert response.status_code == 400
    assert "UNDER_REVIEW" in response.json()["detail"]


# ============================================================================
# Test POST /api/reviews/{id}/approve - Approve Data
# ============================================================================

def test_approve_data_success(client, mock_review_service, sample_review_id):
    """Test successful data approval."""
    # Arrange
    sample_id = uuid4()
    approved_at = datetime.utcnow()
    mock_approval_result = ApprovalResult(
        review_id=sample_review_id,
        approved_at=approved_at,
        approved_by="reviewer456",
        transferred_to_sample_library=True,
        sample_id=sample_id
    )
    mock_review_service.approve_data.return_value = mock_approval_result
    
    # Act
    response = client.post(
        f"/api/reviews/{sample_review_id}/approve",
        json={
            "reviewer_id": "reviewer456",
            "comments": "Looks good"
        }
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["review_id"] == str(sample_review_id)
    assert data["approved_by"] == "reviewer456"
    assert data["transferred_to_sample_library"] is True
    assert data["sample_id"] == str(sample_id)
    
    mock_review_service.approve_data.assert_called_once_with(
        review_id=str(sample_review_id),
        reviewer_id="reviewer456",
        comments="Looks good"
    )


def test_approve_data_without_comments(client, mock_review_service, sample_review_id):
    """Test data approval without comments."""
    # Arrange
    approved_at = datetime.utcnow()
    mock_approval_result = ApprovalResult(
        review_id=sample_review_id,
        approved_at=approved_at,
        approved_by="reviewer456",
        transferred_to_sample_library=True,
        sample_id=uuid4()
    )
    mock_review_service.approve_data.return_value = mock_approval_result
    
    # Act
    response = client.post(
        f"/api/reviews/{sample_review_id}/approve",
        json={
            "reviewer_id": "reviewer456"
        }
    )
    
    # Assert
    assert response.status_code == 200
    mock_review_service.approve_data.assert_called_once_with(
        review_id=str(sample_review_id),
        reviewer_id="reviewer456",
        comments=None
    )


def test_approve_data_not_found(client, mock_review_service, sample_review_id):
    """Test data approval when review not found."""
    # Arrange
    mock_review_service.approve_data.side_effect = ValueError(
        f"Review {sample_review_id} not found"
    )
    
    # Act
    response = client.post(
        f"/api/reviews/{sample_review_id}/approve",
        json={
            "reviewer_id": "reviewer456"
        }
    )
    
    # Assert
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_approve_data_unauthorized_reviewer(client, mock_review_service, sample_review_id):
    """Test data approval by unauthorized reviewer."""
    # Arrange
    mock_review_service.approve_data.side_effect = ValueError(
        "Only assigned reviewer reviewer123 can approve this data"
    )
    
    # Act
    response = client.post(
        f"/api/reviews/{sample_review_id}/approve",
        json={
            "reviewer_id": "reviewer456"
        }
    )
    
    # Assert
    assert response.status_code == 403
    assert "only assigned reviewer" in response.json()["detail"].lower()


def test_approve_data_invalid_state(client, mock_review_service, sample_review_id):
    """Test data approval when not in valid state."""
    # Arrange
    mock_review_service.approve_data.side_effect = ValueError(
        "Data must be in UNDER_REVIEW state to approve"
    )
    
    # Act
    response = client.post(
        f"/api/reviews/{sample_review_id}/approve",
        json={
            "reviewer_id": "reviewer456"
        }
    )
    
    # Assert
    assert response.status_code == 400
    assert "UNDER_REVIEW" in response.json()["detail"]


# ============================================================================
# Test POST /api/reviews/{id}/reject - Reject Data
# ============================================================================

def test_reject_data_success(client, mock_review_service, sample_review_id):
    """Test successful data rejection."""
    # Arrange
    rejected_at = datetime.utcnow()
    mock_rejection_result = RejectionResult(
        review_id=sample_review_id,
        rejected_at=rejected_at,
        rejected_by="reviewer456",
        reason="Quality issues found"
    )
    mock_review_service.reject_data.return_value = mock_rejection_result
    
    # Act
    response = client.post(
        f"/api/reviews/{sample_review_id}/reject",
        json={
            "reviewer_id": "reviewer456",
            "reason": "Quality issues found"
        }
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["review_id"] == str(sample_review_id)
    assert data["rejected_by"] == "reviewer456"
    assert data["reason"] == "Quality issues found"
    
    mock_review_service.reject_data.assert_called_once_with(
        review_id=str(sample_review_id),
        reviewer_id="reviewer456",
        reason="Quality issues found"
    )


def test_reject_data_not_found(client, mock_review_service, sample_review_id):
    """Test data rejection when review not found."""
    # Arrange
    mock_review_service.reject_data.side_effect = ValueError(
        f"Review {sample_review_id} not found"
    )
    
    # Act
    response = client.post(
        f"/api/reviews/{sample_review_id}/reject",
        json={
            "reviewer_id": "reviewer456",
            "reason": "Quality issues"
        }
    )
    
    # Assert
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_reject_data_unauthorized_reviewer(client, mock_review_service, sample_review_id):
    """Test data rejection by unauthorized reviewer."""
    # Arrange
    mock_review_service.reject_data.side_effect = ValueError(
        "Only assigned reviewer reviewer123 can reject this data"
    )
    
    # Act
    response = client.post(
        f"/api/reviews/{sample_review_id}/reject",
        json={
            "reviewer_id": "reviewer456",
            "reason": "Quality issues"
        }
    )
    
    # Assert
    assert response.status_code == 403
    assert "only assigned reviewer" in response.json()["detail"].lower()


def test_reject_data_empty_reason(client, mock_review_service, sample_review_id):
    """Test data rejection with empty reason - Pydantic validation."""
    # Act
    response = client.post(
        f"/api/reviews/{sample_review_id}/reject",
        json={
            "reviewer_id": "reviewer456",
            "reason": ""
        }
    )
    
    # Assert - Pydantic returns 422 for validation errors
    assert response.status_code == 422


def test_reject_data_invalid_state(client, mock_review_service, sample_review_id):
    """Test data rejection when not in valid state."""
    # Arrange
    mock_review_service.reject_data.side_effect = ValueError(
        "Data must be in UNDER_REVIEW state to reject"
    )
    
    # Act
    response = client.post(
        f"/api/reviews/{sample_review_id}/reject",
        json={
            "reviewer_id": "reviewer456",
            "reason": "Quality issues"
        }
    )
    
    # Assert
    assert response.status_code == 400
    assert "UNDER_REVIEW" in response.json()["detail"]


# ============================================================================
# Test GET /api/reviews/{id} - Get Review Status
# ============================================================================

def test_get_review_status_pending(client, mock_review_service, sample_review_id):
    """Test getting review status for pending review."""
    # Arrange
    uploaded_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    mock_review_service.get_review_status.return_value = {
        'review_id': str(sample_review_id),
        'data_id': str(sample_review_id),
        'state': 'under_review',
        'review_status': 'pending',
        'reviewer_id': None,
        'reviewed_at': None,
        'rejection_reason': None,
        'uploaded_by': 'user123',
        'uploaded_at': uploaded_at.isoformat(),
        'updated_at': updated_at.isoformat()
    }
    
    # Act
    response = client.get(f"/api/reviews/{sample_review_id}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["review_id"] == str(sample_review_id)
    assert data["state"] == "under_review"
    assert data["review_status"] == "pending"
    assert data["reviewer_id"] is None
    assert data["reviewed_at"] is None
    assert data["rejection_reason"] is None
    
    mock_review_service.get_review_status.assert_called_once_with(str(sample_review_id))


def test_get_review_status_approved(client, mock_review_service, sample_review_id):
    """Test getting review status for approved review."""
    # Arrange
    uploaded_at = datetime.utcnow()
    reviewed_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    mock_review_service.get_review_status.return_value = {
        'review_id': str(sample_review_id),
        'data_id': str(sample_review_id),
        'state': 'approved',
        'review_status': 'approved',
        'reviewer_id': 'reviewer456',
        'reviewed_at': reviewed_at.isoformat(),
        'rejection_reason': None,
        'uploaded_by': 'user123',
        'uploaded_at': uploaded_at.isoformat(),
        'updated_at': updated_at.isoformat()
    }
    
    # Act
    response = client.get(f"/api/reviews/{sample_review_id}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "approved"
    assert data["review_status"] == "approved"
    assert data["reviewer_id"] == "reviewer456"
    assert data["reviewed_at"] is not None


def test_get_review_status_rejected(client, mock_review_service, sample_review_id):
    """Test getting review status for rejected review."""
    # Arrange
    uploaded_at = datetime.utcnow()
    reviewed_at = datetime.utcnow()
    updated_at = datetime.utcnow()
    mock_review_service.get_review_status.return_value = {
        'review_id': str(sample_review_id),
        'data_id': str(sample_review_id),
        'state': 'rejected',
        'review_status': 'rejected',
        'reviewer_id': 'reviewer456',
        'reviewed_at': reviewed_at.isoformat(),
        'rejection_reason': 'Quality issues found',
        'uploaded_by': 'user123',
        'uploaded_at': uploaded_at.isoformat(),
        'updated_at': updated_at.isoformat()
    }
    
    # Act
    response = client.get(f"/api/reviews/{sample_review_id}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "rejected"
    assert data["review_status"] == "rejected"
    assert data["rejection_reason"] == "Quality issues found"


def test_get_review_status_not_found(client, mock_review_service, sample_review_id):
    """Test getting review status when review not found."""
    # Arrange
    mock_review_service.get_review_status.side_effect = ValueError(
        f"Review {sample_review_id} not found"
    )
    
    # Act
    response = client.get(f"/api/reviews/{sample_review_id}")
    
    # Assert
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_review_status_internal_error(client, mock_review_service, sample_review_id):
    """Test getting review status with internal error."""
    # Arrange
    mock_review_service.get_review_status.side_effect = Exception("Database error")
    
    # Act
    response = client.get(f"/api/reviews/{sample_review_id}")
    
    # Assert
    assert response.status_code == 500
    assert "Failed to get review status" in response.json()["detail"]


# ============================================================================
# Test Request Validation
# ============================================================================

def test_submit_review_missing_data_id(client):
    """Test submit review with missing data_id."""
    # Act
    response = client.post(
        "/api/reviews",
        json={
            "submitted_by": "user123"
        }
    )
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_submit_review_missing_submitted_by(client):
    """Test submit review with missing submitted_by."""
    # Act
    response = client.post(
        "/api/reviews",
        json={
            "data_id": str(uuid4())
        }
    )
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_reject_data_reason_too_short(client, sample_review_id):
    """Test reject data with reason that's too short (empty string)."""
    # Act
    response = client.post(
        f"/api/reviews/{sample_review_id}/reject",
        json={
            "reviewer_id": "reviewer456",
            "reason": ""
        }
    )
    
    # Assert
    assert response.status_code == 422  # Validation error
