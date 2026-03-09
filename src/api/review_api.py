"""
Review API Router for Data Lifecycle Management.

Provides REST API endpoints for managing data review workflow,
including submission, reviewer assignment, approval, rejection, and status tracking.

Validates: Requirements 3.1, 3.2, 3.3, 12.3, 12.4, 12.5
"""

from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, status
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from src.database.connection import get_db_session
from src.services.review_service import ReviewService
from src.models.data_lifecycle import ReviewStatus, DataState


router = APIRouter(prefix="/api/reviews", tags=["Review Workflow"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class SubmitReviewRequest(BaseModel):
    """Submit data for review request."""
    data_id: str = Field(..., description="Temporary data ID to review")
    submitted_by: str = Field(..., description="User ID who is submitting")
    reviewer_id: Optional[str] = Field(None, description="Optional reviewer ID to assign immediately")


class SubmitReviewResponse(BaseModel):
    """Submit data for review response."""
    review_id: UUID = Field(..., description="Review ID (same as data ID)")
    data_id: str = Field(..., description="Data ID being reviewed")
    submitter_id: str = Field(..., description="User ID who submitted")
    reviewer_id: Optional[str] = Field(None, description="Assigned reviewer ID")
    status: ReviewStatus = Field(..., description="Review status")
    submitted_at: datetime = Field(..., description="Submission timestamp")


class AssignReviewerRequest(BaseModel):
    """Assign reviewer request."""
    reviewer_id: str = Field(..., description="User ID of the reviewer to assign")
    assigned_by: str = Field(..., description="User ID who is assigning the reviewer")


class AssignReviewerResponse(BaseModel):
    """Assign reviewer response."""
    review_id: UUID = Field(..., description="Review ID")
    reviewer_id: str = Field(..., description="Assigned reviewer ID")
    assigned_by: str = Field(..., description="User ID who assigned the reviewer")
    status: ReviewStatus = Field(..., description="Updated review status")


class ApproveDataRequest(BaseModel):
    """Approve data request."""
    reviewer_id: str = Field(..., description="User ID of the reviewer approving")
    comments: Optional[str] = Field(None, description="Optional approval comments")


class ApproveDataResponse(BaseModel):
    """Approve data response."""
    review_id: UUID = Field(..., description="Review ID")
    approved_at: datetime = Field(..., description="Approval timestamp")
    approved_by: str = Field(..., description="User ID who approved")
    transferred_to_sample_library: bool = Field(..., description="Whether data was transferred to sample library")
    sample_id: Optional[UUID] = Field(None, description="Sample ID if transferred")


class RejectDataRequest(BaseModel):
    """Reject data request."""
    reviewer_id: str = Field(..., description="User ID of the reviewer rejecting")
    reason: str = Field(..., min_length=1, description="Rejection reason (required)")


class RejectDataResponse(BaseModel):
    """Reject data response."""
    review_id: UUID = Field(..., description="Review ID")
    rejected_at: datetime = Field(..., description="Rejection timestamp")
    rejected_by: str = Field(..., description="User ID who rejected")
    reason: str = Field(..., description="Rejection reason")


class ReviewStatusResponse(BaseModel):
    """Review status response."""
    review_id: UUID = Field(..., description="Review ID")
    data_id: UUID = Field(..., description="Data ID")
    state: DataState = Field(..., description="Current data state")
    review_status: Optional[ReviewStatus] = Field(None, description="Review status")
    reviewer_id: Optional[str] = Field(None, description="Assigned reviewer ID")
    reviewed_at: Optional[datetime] = Field(None, description="Review completion timestamp")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason if rejected")
    uploaded_by: str = Field(..., description="User ID who uploaded the data")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_review_service(db: DBSession = Depends(get_db_session)) -> ReviewService:
    """Get review service instance."""
    return ReviewService(db)


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("", response_model=SubmitReviewResponse, status_code=status.HTTP_201_CREATED)
async def submit_for_review(
    request: SubmitReviewRequest,
    review_service: ReviewService = Depends(get_review_service)
):
    """
    Submit temporary data for review.
    
    Creates a review request for temporary data and optionally assigns a reviewer.
    Transitions the data state from TEMP_STORED to UNDER_REVIEW.
    
    Validates: Requirements 3.1, 12.3
    
    Args:
        request: Submit review request with data ID, submitter, and optional reviewer
        review_service: Review service instance
    
    Returns:
        SubmitReviewResponse with review details
    
    Raises:
        HTTPException 400: If data not found or not in valid state
        HTTPException 500: If submission fails
    """
    try:
        review_request = review_service.submit_for_review(
            data_id=request.data_id,
            submitted_by=request.submitted_by,
            reviewer_id=request.reviewer_id
        )
        
        return SubmitReviewResponse(
            review_id=review_request.id,
            data_id=review_request.data_id,
            submitter_id=review_request.submitter_id,
            reviewer_id=review_request.reviewer_id,
            status=review_request.status,
            submitted_at=review_request.submitted_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit for review: {str(e)}"
        )


@router.put("/{review_id}/assign", response_model=AssignReviewerResponse)
async def assign_reviewer(
    review_id: UUID,
    request: AssignReviewerRequest,
    review_service: ReviewService = Depends(get_review_service)
):
    """
    Assign a reviewer to a review request.
    
    Updates the reviewer assignment for a review request that is in UNDER_REVIEW state.
    
    Validates: Requirements 3.4, 12.4
    
    Args:
        review_id: Review ID (same as data ID)
        request: Assign reviewer request with reviewer ID and assigner ID
        review_service: Review service instance
    
    Returns:
        AssignReviewerResponse with updated review details
    
    Raises:
        HTTPException 400: If review not found or not in valid state
        HTTPException 404: If review not found
        HTTPException 500: If assignment fails
    """
    try:
        review_service.assign_reviewer(
            review_id=str(review_id),
            reviewer_id=request.reviewer_id,
            assigned_by=request.assigned_by
        )
        
        # Get updated status
        status_dict = review_service.get_review_status(str(review_id))
        
        return AssignReviewerResponse(
            review_id=review_id,
            reviewer_id=request.reviewer_id,
            assigned_by=request.assigned_by,
            status=ReviewStatus(status_dict['review_status'])
        )
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign reviewer: {str(e)}"
        )


@router.post("/{review_id}/approve", response_model=ApproveDataResponse)
async def approve_data(
    review_id: UUID,
    request: ApproveDataRequest,
    review_service: ReviewService = Depends(get_review_service)
):
    """
    Approve data and transfer to sample library.
    
    Approves the data under review, transitions it to APPROVED state,
    and transfers it to the sample library.
    
    Validates: Requirements 3.2, 3.5, 3.6, 12.4
    
    Args:
        review_id: Review ID (same as data ID)
        request: Approve data request with reviewer ID and optional comments
        review_service: Review service instance
    
    Returns:
        ApproveDataResponse with approval details and sample ID
    
    Raises:
        HTTPException 400: If review not found or not in valid state
        HTTPException 403: If reviewer is not authorized
        HTTPException 404: If review not found
        HTTPException 500: If approval fails
    """
    try:
        approval_result = review_service.approve_data(
            review_id=str(review_id),
            reviewer_id=request.reviewer_id,
            comments=request.comments
        )
        
        return ApproveDataResponse(
            review_id=approval_result.review_id,
            approved_at=approval_result.approved_at,
            approved_by=approval_result.approved_by,
            transferred_to_sample_library=approval_result.transferred_to_sample_library,
            sample_id=approval_result.sample_id
        )
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        elif "only assigned reviewer" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve data: {str(e)}"
        )


@router.post("/{review_id}/reject", response_model=RejectDataResponse)
async def reject_data(
    review_id: UUID,
    request: RejectDataRequest,
    review_service: ReviewService = Depends(get_review_service)
):
    """
    Reject data with reason.
    
    Rejects the data under review, transitions it to REJECTED state,
    and records the rejection reason.
    
    Validates: Requirements 3.3, 3.6, 12.5
    
    Args:
        review_id: Review ID (same as data ID)
        request: Reject data request with reviewer ID and reason
        review_service: Review service instance
    
    Returns:
        RejectDataResponse with rejection details
    
    Raises:
        HTTPException 400: If review not found, not in valid state, or reason is empty
        HTTPException 403: If reviewer is not authorized
        HTTPException 404: If review not found
        HTTPException 500: If rejection fails
    """
    try:
        rejection_result = review_service.reject_data(
            review_id=str(review_id),
            reviewer_id=request.reviewer_id,
            reason=request.reason
        )
        
        return RejectDataResponse(
            review_id=rejection_result.review_id,
            rejected_at=rejection_result.rejected_at,
            rejected_by=rejection_result.rejected_by,
            reason=rejection_result.reason
        )
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        elif "only assigned reviewer" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject data: {str(e)}"
        )


@router.get("/{review_id}", response_model=ReviewStatusResponse)
async def get_review_status(
    review_id: UUID,
    review_service: ReviewService = Depends(get_review_service)
):
    """
    Get the current status of a review.
    
    Returns detailed information about a review including its current state,
    review status, reviewer assignment, and timestamps.
    
    Validates: Requirements 12.3
    
    Args:
        review_id: Review ID (same as data ID)
        review_service: Review service instance
    
    Returns:
        ReviewStatusResponse with review status details
    
    Raises:
        HTTPException 404: If review not found
        HTTPException 500: If status retrieval fails
    """
    try:
        status_dict = review_service.get_review_status(str(review_id))
        
        return ReviewStatusResponse(
            review_id=UUID(status_dict['review_id']),
            data_id=UUID(status_dict['data_id']),
            state=DataState(status_dict['state']),
            review_status=ReviewStatus(status_dict['review_status']) if status_dict['review_status'] else None,
            reviewer_id=status_dict['reviewer_id'],
            reviewed_at=datetime.fromisoformat(status_dict['reviewed_at']) if status_dict['reviewed_at'] else None,
            rejection_reason=status_dict['rejection_reason'],
            uploaded_by=status_dict['uploaded_by'],
            uploaded_at=datetime.fromisoformat(status_dict['uploaded_at']),
            updated_at=datetime.fromisoformat(status_dict['updated_at'])
        )
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review status: {str(e)}"
        )
