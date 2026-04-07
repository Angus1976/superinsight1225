"""
Review Service for Data Lifecycle Management

Handles data review and approval workflow, integrating with State Manager
for state transitions and Audit Logger for review action logging.
"""

from datetime import datetime
from typing import Optional, Dict, Any, Union
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, cast, String, or_

from src.models.data_lifecycle import (
    TempDataModel,
    SampleModel,
    ReviewStatus,
    DataState,
    ResourceType,
    OperationType,
    OperationResult,
    Action
)
from src.services.data_lifecycle_state_manager import (
    DataStateManager,
    StateTransitionContext
)
from src.services.audit_logger import AuditLogger


def _as_uuid(value: Union[str, UUID]) -> UUID:
    """Coerce string IDs to UUID for ORM binds (Postgres + SQLite unit tests)."""
    return value if isinstance(value, UUID) else UUID(str(value))


def _temp_data_id_eq(data_id: Union[str, UUID]):
    """Primary-key filter for TempDataModel.id (plain SQLite + SQLiteUUID property tests)."""
    u = _as_uuid(data_id)
    return or_(
        TempDataModel.id == u,
        cast(TempDataModel.id, String) == str(u),
    )


class ReviewRequest:
    """Review request model"""
    def __init__(
        self,
        id: UUID,
        data_id: str,
        submitter_id: str,
        reviewer_id: Optional[str] = None,
        status: ReviewStatus = ReviewStatus.PENDING,
        submitted_at: datetime = None
    ):
        self.id = id
        self.data_id = data_id
        self.submitter_id = submitter_id
        self.reviewer_id = reviewer_id
        self.status = status
        self.submitted_at = submitted_at or datetime.utcnow()


class ApprovalResult:
    """Approval result model"""
    def __init__(
        self,
        review_id: UUID,
        approved_at: datetime,
        approved_by: str,
        transferred_to_sample_library: bool,
        sample_id: Optional[UUID] = None
    ):
        self.review_id = review_id
        self.approved_at = approved_at
        self.approved_by = approved_by
        self.transferred_to_sample_library = transferred_to_sample_library
        self.sample_id = sample_id


class RejectionResult:
    """Rejection result model"""
    def __init__(
        self,
        review_id: UUID,
        rejected_at: datetime,
        rejected_by: str,
        reason: str
    ):
        self.review_id = review_id
        self.rejected_at = rejected_at
        self.rejected_by = rejected_by
        self.reason = reason


class ReviewService:
    """
    Review Service for managing data review and approval workflow.
    
    Responsibilities:
    - Manage review workflow
    - Assign reviewers
    - Process approval/rejection decisions
    - Transfer approved data to sample library
    - Integrate with State Manager for state transitions
    - Integrate with Audit Logger for review action logging
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
    """
    
    def __init__(self, db: Session):
        """
        Initialize the Review Service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.state_manager = DataStateManager(db)
        self.audit_logger = AuditLogger(db)
    
    def submit_for_review(
        self,
        data_id: str,
        submitted_by: str,
        reviewer_id: Optional[str] = None
    ) -> ReviewRequest:
        """
        Submit temporary data for review.
        
        Args:
            data_id: ID of the temporary data to review
            submitted_by: User ID who is submitting for review
            reviewer_id: Optional reviewer ID to assign immediately
        
        Returns:
            ReviewRequest object
        
        Raises:
            ValueError: If data not found or not in valid state
        
        Validates: Requirements 3.1
        """
        # Get temp data
        temp_data = self.db.query(TempDataModel).filter(
            _temp_data_id_eq(data_id)
        ).first()
        
        if not temp_data:
            raise ValueError(f"Temporary data {data_id} not found")
        
        # Validate current state
        if temp_data.state != DataState.TEMP_STORED:
            raise ValueError(
                f"Data must be in TEMP_STORED state to submit for review. "
                f"Current state: {temp_data.state.value}"
            )
        
        # Transition to UNDER_REVIEW state
        context = StateTransitionContext(
            user_id=submitted_by,
            reason="Submitted for review",
            metadata={'reviewer_id': reviewer_id} if reviewer_id else {}
        )
        
        result = self.state_manager.transition_state(
            data_id=data_id,
            resource_type=ResourceType.TEMP_DATA,
            target_state=DataState.UNDER_REVIEW,
            context=context
        )
        
        if not result.success:
            raise ValueError(f"Failed to transition state: {result.error}")
        
        # Update review status
        temp_data.review_status = ReviewStatus.PENDING if not reviewer_id else ReviewStatus.IN_PROGRESS
        temp_data.reviewed_by = reviewer_id
        temp_data.updated_at = datetime.utcnow()
        
        # Log review submission
        self.audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id=submitted_by,
            resource_type=ResourceType.TEMP_DATA,
            resource_id=data_id,
            action=Action.REVIEW,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'submit_for_review',
                'reviewer_id': reviewer_id,
                'status': temp_data.review_status.value
            }
        )
        
        self.db.commit()
        
        return ReviewRequest(
            id=temp_data.id,
            data_id=data_id,
            submitter_id=submitted_by,
            reviewer_id=reviewer_id,
            status=temp_data.review_status,
            submitted_at=datetime.utcnow()
        )
    
    def assign_reviewer(
        self,
        review_id: str,
        reviewer_id: str,
        assigned_by: str
    ) -> None:
        """
        Assign a reviewer to a review request.
        
        Args:
            review_id: ID of the review (same as data_id)
            reviewer_id: User ID of the reviewer to assign
            assigned_by: User ID who is assigning the reviewer
        
        Raises:
            ValueError: If review not found or not in valid state
        
        Validates: Requirements 3.4
        """
        # Get temp data
        temp_data = self.db.query(TempDataModel).filter(
            _temp_data_id_eq(review_id)
        ).first()
        
        if not temp_data:
            raise ValueError(f"Review {review_id} not found")
        
        # Validate state
        if temp_data.state != DataState.UNDER_REVIEW:
            raise ValueError(
                f"Data must be in UNDER_REVIEW state to assign reviewer. "
                f"Current state: {temp_data.state.value}"
            )
        
        # Update reviewer assignment
        temp_data.reviewed_by = reviewer_id
        temp_data.review_status = ReviewStatus.IN_PROGRESS
        temp_data.updated_at = datetime.utcnow()
        
        # Log reviewer assignment
        self.audit_logger.log_operation(
            operation_type=OperationType.UPDATE,
            user_id=assigned_by,
            resource_type=ResourceType.TEMP_DATA,
            resource_id=review_id,
            action=Action.REVIEW,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'assign_reviewer',
                'reviewer_id': reviewer_id,
                'assigned_by': assigned_by
            }
        )
        
        self.db.commit()
    
    def approve_data(
        self,
        review_id: str,
        reviewer_id: str,
        comments: Optional[str] = None
    ) -> ApprovalResult:
        """
        Approve data and transfer to sample library.
        
        Args:
            review_id: ID of the review (same as data_id)
            reviewer_id: User ID of the reviewer approving
            comments: Optional approval comments
        
        Returns:
            ApprovalResult object
        
        Raises:
            ValueError: If review not found or not in valid state
        
        Validates: Requirements 3.2, 3.5, 3.6
        """
        # Get temp data
        temp_data = self.db.query(TempDataModel).filter(
            _temp_data_id_eq(review_id)
        ).first()
        
        if not temp_data:
            raise ValueError(f"Review {review_id} not found")
        
        # Validate state
        if temp_data.state != DataState.UNDER_REVIEW:
            raise ValueError(
                f"Data must be in UNDER_REVIEW state to approve. "
                f"Current state: {temp_data.state.value}"
            )
        
        # Validate reviewer
        if temp_data.reviewed_by and temp_data.reviewed_by != reviewer_id:
            raise ValueError(
                f"Only assigned reviewer {temp_data.reviewed_by} can approve this data"
            )
        
        approved_at = datetime.utcnow()
        
        # Transition to APPROVED state
        context = StateTransitionContext(
            user_id=reviewer_id,
            reason=f"Approved by reviewer. Comments: {comments}" if comments else "Approved by reviewer",
            metadata={'comments': comments} if comments else {}
        )
        
        result = self.state_manager.transition_state(
            data_id=review_id,
            resource_type=ResourceType.TEMP_DATA,
            target_state=DataState.APPROVED,
            context=context
        )
        
        if not result.success:
            raise ValueError(f"Failed to transition to APPROVED state: {result.error}")
        
        # Update review status
        temp_data.review_status = ReviewStatus.APPROVED
        temp_data.reviewed_by = reviewer_id
        temp_data.reviewed_at = approved_at
        temp_data.updated_at = approved_at
        
        # Transfer to sample library
        sample_id = self._transfer_to_sample_library(
            temp_data=temp_data,
            reviewer_id=reviewer_id,
            comments=comments
        )
        
        # Log approval
        self.audit_logger.log_operation(
            operation_type=OperationType.UPDATE,
            user_id=reviewer_id,
            resource_type=ResourceType.TEMP_DATA,
            resource_id=review_id,
            action=Action.REVIEW,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'approve_data',
                'comments': comments,
                'sample_id': str(sample_id),
                'transferred_to_sample_library': True
            }
        )
        
        self.db.commit()
        
        return ApprovalResult(
            review_id=temp_data.id,
            approved_at=approved_at,
            approved_by=reviewer_id,
            transferred_to_sample_library=True,
            sample_id=sample_id
        )
    
    def reject_data(
        self,
        review_id: str,
        reviewer_id: str,
        reason: str
    ) -> RejectionResult:
        """
        Reject data with reason.
        
        Args:
            review_id: ID of the review (same as data_id)
            reviewer_id: User ID of the reviewer rejecting
            reason: Rejection reason (required)
        
        Returns:
            RejectionResult object
        
        Raises:
            ValueError: If review not found, not in valid state, or reason is empty
        
        Validates: Requirements 3.3, 3.6
        """
        # Validate reason is provided
        if not reason or not reason.strip():
            raise ValueError("Rejection reason is required and cannot be empty")
        
        # Get temp data
        temp_data = self.db.query(TempDataModel).filter(
            _temp_data_id_eq(review_id)
        ).first()
        
        if not temp_data:
            raise ValueError(f"Review {review_id} not found")
        
        # Validate state
        if temp_data.state != DataState.UNDER_REVIEW:
            raise ValueError(
                f"Data must be in UNDER_REVIEW state to reject. "
                f"Current state: {temp_data.state.value}"
            )
        
        # Validate reviewer
        if temp_data.reviewed_by and temp_data.reviewed_by != reviewer_id:
            raise ValueError(
                f"Only assigned reviewer {temp_data.reviewed_by} can reject this data"
            )
        
        rejected_at = datetime.utcnow()
        
        # Transition to REJECTED state
        context = StateTransitionContext(
            user_id=reviewer_id,
            reason=f"Rejected: {reason}",
            metadata={'rejection_reason': reason}
        )
        
        result = self.state_manager.transition_state(
            data_id=review_id,
            resource_type=ResourceType.TEMP_DATA,
            target_state=DataState.REJECTED,
            context=context
        )
        
        if not result.success:
            raise ValueError(f"Failed to transition to REJECTED state: {result.error}")
        
        # Update review status and rejection reason
        temp_data.review_status = ReviewStatus.REJECTED
        temp_data.reviewed_by = reviewer_id
        temp_data.reviewed_at = rejected_at
        temp_data.rejection_reason = reason
        temp_data.updated_at = rejected_at
        
        # Log rejection
        self.audit_logger.log_operation(
            operation_type=OperationType.UPDATE,
            user_id=reviewer_id,
            resource_type=ResourceType.TEMP_DATA,
            resource_id=review_id,
            action=Action.REVIEW,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'reject_data',
                'reason': reason
            }
        )
        
        self.db.commit()
        
        return RejectionResult(
            review_id=temp_data.id,
            rejected_at=rejected_at,
            rejected_by=reviewer_id,
            reason=reason
        )
    
    def get_review_status(self, review_id: str) -> Dict[str, Any]:
        """
        Get the current status of a review.
        
        Args:
            review_id: ID of the review (same as data_id)
        
        Returns:
            Dictionary with review status information
        
        Raises:
            ValueError: If review not found
        """
        # Get temp data
        temp_data = self.db.query(TempDataModel).filter(
            _temp_data_id_eq(review_id)
        ).first()
        
        if not temp_data:
            raise ValueError(f"Review {review_id} not found")
        
        return {
            'review_id': str(temp_data.id),
            'data_id': str(temp_data.id),
            'state': temp_data.state.value,
            'review_status': temp_data.review_status.value if temp_data.review_status else None,
            'reviewer_id': temp_data.reviewed_by,
            'reviewed_at': temp_data.reviewed_at.isoformat() if temp_data.reviewed_at else None,
            'rejection_reason': temp_data.rejection_reason,
            'uploaded_by': temp_data.uploaded_by,
            'uploaded_at': temp_data.uploaded_at.isoformat(),
            'updated_at': temp_data.updated_at.isoformat()
        }
    
    def _transfer_to_sample_library(
        self,
        temp_data: TempDataModel,
        reviewer_id: str,
        comments: Optional[str] = None
    ) -> UUID:
        """
        Transfer approved data to sample library.
        
        Args:
            temp_data: TempDataModel instance
            reviewer_id: User ID of the reviewer
            comments: Optional approval comments
        
        Returns:
            UUID of the created sample
        """
        # Extract metadata for sample
        metadata = temp_data.metadata_ or {}
        content = temp_data.content or {}
        
        # Create sample with default quality scores
        # In a real implementation, these would be calculated based on content
        sample = SampleModel(
            id=uuid4(),
            data_id=str(temp_data.id),
            content=content,
            category=metadata.get('category', 'general'),
            quality_overall=0.8,  # Default quality score
            quality_completeness=0.8,
            quality_accuracy=0.8,
            quality_consistency=0.8,
            version=1,
            tags=metadata.get('tags', []),
            usage_count=0,
            last_used_at=None,
            metadata_={
                'source': 'temp_data',
                'source_id': str(temp_data.id),
                'uploaded_by': temp_data.uploaded_by,
                'reviewed_by': reviewer_id,
                'approval_comments': comments,
                'original_metadata': metadata
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(sample)
        
        # Transition temp data to IN_SAMPLE_LIBRARY state
        context = StateTransitionContext(
            user_id=reviewer_id,
            reason="Transferred to sample library",
            metadata={'sample_id': str(sample.id)}
        )
        
        result = self.state_manager.transition_state(
            data_id=str(temp_data.id),
            resource_type=ResourceType.TEMP_DATA,
            target_state=DataState.IN_SAMPLE_LIBRARY,
            context=context
        )
        
        if not result.success:
            raise ValueError(f"Failed to transition to IN_SAMPLE_LIBRARY state: {result.error}")
        
        # Log transfer
        self.audit_logger.log_operation(
            operation_type=OperationType.TRANSFER,
            user_id=reviewer_id,
            resource_type=ResourceType.TEMP_DATA,
            resource_id=str(temp_data.id),
            action=Action.TRANSFER,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'transfer_to_sample_library',
                'sample_id': str(sample.id),
                'source_data_id': str(temp_data.id)
            }
        )
        
        return sample.id
