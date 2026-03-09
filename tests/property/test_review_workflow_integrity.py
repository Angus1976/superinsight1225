"""
Property-Based Tests for Review Workflow Integrity

Tests Property 5: Review Workflow Integrity

**Validates: Requirements 3.1, 3.2, 3.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from src.models.data_lifecycle import (
    DataState,
    ResourceType,
    TempDataModel,
    SampleModel,
    ReviewStatus
)
from src.services.review_service import ReviewService
from tests.conftest import db_session


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating user IDs
user_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(
    whitelist_categories=('Lu', 'Ll', 'Nd'),
    min_codepoint=ord('a'),
    max_codepoint=ord('z')
))

# Strategy for generating comments
comment_strategy = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=200)
)

# Strategy for generating non-empty rejection reasons
rejection_reason_strategy = st.text(min_size=1, max_size=200, alphabet=st.characters(
    blacklist_characters='\x00\n\r\t',
    blacklist_categories=('Cc', 'Cs')
))

# Strategy for generating reviewer IDs (optional)
optional_reviewer_strategy = st.one_of(
    st.none(),
    user_id_strategy
)


# ============================================================================
# Helper Functions
# ============================================================================

def create_temp_data_for_review(db: Session, uploaded_by: str) -> str:
    """Create a temporary data item ready for review"""
    temp_data = TempDataModel(
        id=uuid4(),
        source_document_id=str(uuid4()),
        content={"test": "data", "sections": [{"title": "Test", "content": "Content"}]},
        state=DataState.TEMP_STORED,
        uploaded_by=uploaded_by,
        uploaded_at=datetime.utcnow(),
        metadata_={"category": "test", "tags": ["test"]}
    )
    db.add(temp_data)
    db.commit()
    return str(temp_data.id)


def get_sample_by_data_id(db: Session, data_id: str) -> SampleModel:
    """Get sample by original data ID"""
    return db.query(SampleModel).filter(
        SampleModel.data_id == data_id
    ).first()


# ============================================================================
# Property 5: Review Workflow Integrity
# **Validates: Requirements 3.1, 3.2, 3.3**
# ============================================================================

@pytest.mark.property
class TestReviewWorkflowIntegrity:
    """
    Property 5: Review Workflow Integrity
    
    For all review workflows (submit → approve/reject), the final state must
    be consistent with the decision:
    - If approved, data must be in APPROVED state and transferred to sample library
    - If rejected, data must be in REJECTED state with non-empty rejection reason
    - State transitions must follow the defined state machine
    """
    
    @given(
        submitter_id=user_id_strategy,
        reviewer_id=user_id_strategy,
        comments=comment_strategy
    )
    @settings(max_examples=30, deadline=None)
    def test_approval_workflow_integrity(
        self,
        db_session: Session,
        submitter_id: str,
        reviewer_id: str,
        comments: str
    ):
        """
        Property: Approval workflow maintains integrity.
        
        For any approval workflow (submit → approve), the data must:
        1. Transition to APPROVED state
        2. Be transferred to sample library
        3. Have review status set to APPROVED
        4. Have reviewer information recorded
        """
        # Create temp data
        data_id = create_temp_data_for_review(db_session, submitter_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Submit for review
        review_request = review_service.submit_for_review(
            data_id=data_id,
            submitted_by=submitter_id,
            reviewer_id=reviewer_id
        )
        
        # Assert: Review request created
        assert review_request.data_id == data_id
        assert review_request.submitter_id == submitter_id
        assert review_request.reviewer_id == reviewer_id
        
        # Get temp data after submission
        temp_data = db_session.query(TempDataModel).filter(
            TempDataModel.id == data_id
        ).first()
        
        # Assert: Data is in UNDER_REVIEW state
        assert temp_data.state == DataState.UNDER_REVIEW, (
            f"After submission, data should be in UNDER_REVIEW state, "
            f"but is in {temp_data.state.value}"
        )
        
        # Approve data
        approval_result = review_service.approve_data(
            review_id=data_id,
            reviewer_id=reviewer_id,
            comments=comments
        )
        
        # Assert: Approval result is correct
        assert approval_result.review_id == temp_data.id
        assert approval_result.approved_by == reviewer_id
        assert approval_result.transferred_to_sample_library is True
        assert approval_result.sample_id is not None
        
        # Refresh temp data
        db_session.refresh(temp_data)
        
        # Assert: Data is in APPROVED state
        assert temp_data.state == DataState.APPROVED, (
            f"After approval, data should be in APPROVED state, "
            f"but is in {temp_data.state.value}"
        )
        
        # Assert: Review status is APPROVED
        assert temp_data.review_status == ReviewStatus.APPROVED, (
            f"After approval, review_status should be APPROVED, "
            f"but is {temp_data.review_status.value if temp_data.review_status else None}"
        )
        
        # Assert: Reviewer information is recorded
        assert temp_data.reviewed_by == reviewer_id, (
            f"After approval, reviewed_by should be {reviewer_id}, "
            f"but is {temp_data.reviewed_by}"
        )
        assert temp_data.reviewed_at is not None, (
            "After approval, reviewed_at should be set"
        )
        
        # Assert: Data is transferred to sample library
        sample = get_sample_by_data_id(db_session, data_id)
        assert sample is not None, (
            "After approval, data should be transferred to sample library"
        )
        assert sample.id == approval_result.sample_id, (
            f"Sample ID should match approval result: {approval_result.sample_id}"
        )
        
        # Assert: Data is in IN_SAMPLE_LIBRARY state
        db_session.refresh(temp_data)
        assert temp_data.state == DataState.IN_SAMPLE_LIBRARY, (
            f"After transfer, data should be in IN_SAMPLE_LIBRARY state, "
            f"but is in {temp_data.state.value}"
        )
    
    @given(
        submitter_id=user_id_strategy,
        reviewer_id=user_id_strategy,
        rejection_reason=rejection_reason_strategy
    )
    @settings(max_examples=30, deadline=None)
    def test_rejection_workflow_integrity(
        self,
        db_session: Session,
        submitter_id: str,
        reviewer_id: str,
        rejection_reason: str
    ):
        """
        Property: Rejection workflow maintains integrity.
        
        For any rejection workflow (submit → reject), the data must:
        1. Transition to REJECTED state
        2. Have review status set to REJECTED
        3. Have non-empty rejection reason recorded
        4. Have reviewer information recorded
        5. NOT be transferred to sample library
        """
        # Ensure rejection reason is not empty or whitespace-only
        assume(rejection_reason.strip())
        
        # Create temp data
        data_id = create_temp_data_for_review(db_session, submitter_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Submit for review
        review_request = review_service.submit_for_review(
            data_id=data_id,
            submitted_by=submitter_id,
            reviewer_id=reviewer_id
        )
        
        # Assert: Review request created
        assert review_request.data_id == data_id
        
        # Get temp data after submission
        temp_data = db_session.query(TempDataModel).filter(
            TempDataModel.id == data_id
        ).first()
        
        # Assert: Data is in UNDER_REVIEW state
        assert temp_data.state == DataState.UNDER_REVIEW
        
        # Reject data
        rejection_result = review_service.reject_data(
            review_id=data_id,
            reviewer_id=reviewer_id,
            reason=rejection_reason
        )
        
        # Assert: Rejection result is correct
        assert rejection_result.review_id == temp_data.id
        assert rejection_result.rejected_by == reviewer_id
        assert rejection_result.reason == rejection_reason
        
        # Refresh temp data
        db_session.refresh(temp_data)
        
        # Assert: Data is in REJECTED state
        assert temp_data.state == DataState.REJECTED, (
            f"After rejection, data should be in REJECTED state, "
            f"but is in {temp_data.state.value}"
        )
        
        # Assert: Review status is REJECTED
        assert temp_data.review_status == ReviewStatus.REJECTED, (
            f"After rejection, review_status should be REJECTED, "
            f"but is {temp_data.review_status.value if temp_data.review_status else None}"
        )
        
        # Assert: Rejection reason is recorded and non-empty
        assert temp_data.rejection_reason is not None, (
            "After rejection, rejection_reason should be set"
        )
        assert temp_data.rejection_reason.strip(), (
            "After rejection, rejection_reason should not be empty or whitespace-only"
        )
        assert temp_data.rejection_reason == rejection_reason, (
            f"Rejection reason should be {rejection_reason}, "
            f"but is {temp_data.rejection_reason}"
        )
        
        # Assert: Reviewer information is recorded
        assert temp_data.reviewed_by == reviewer_id, (
            f"After rejection, reviewed_by should be {reviewer_id}, "
            f"but is {temp_data.reviewed_by}"
        )
        assert temp_data.reviewed_at is not None, (
            "After rejection, reviewed_at should be set"
        )
        
        # Assert: Data is NOT transferred to sample library
        sample = get_sample_by_data_id(db_session, data_id)
        assert sample is None, (
            "After rejection, data should NOT be transferred to sample library"
        )
    
    @given(
        submitter_id=user_id_strategy,
        reviewer_id=user_id_strategy
    )
    @settings(max_examples=20, deadline=None)
    def test_rejection_requires_non_empty_reason(
        self,
        db_session: Session,
        submitter_id: str,
        reviewer_id: str
    ):
        """
        Property: Rejection requires non-empty reason.
        
        For any rejection attempt with empty or whitespace-only reason,
        the operation must fail with a descriptive error.
        """
        # Create temp data
        data_id = create_temp_data_for_review(db_session, submitter_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Submit for review
        review_service.submit_for_review(
            data_id=data_id,
            submitted_by=submitter_id,
            reviewer_id=reviewer_id
        )
        
        # Test empty reason
        with pytest.raises(ValueError) as exc_info:
            review_service.reject_data(
                review_id=data_id,
                reviewer_id=reviewer_id,
                reason=""
            )
        
        assert "Rejection reason is required" in str(exc_info.value), (
            "Empty rejection reason should raise ValueError with descriptive message"
        )
        
        # Test whitespace-only reason
        with pytest.raises(ValueError) as exc_info:
            review_service.reject_data(
                review_id=data_id,
                reviewer_id=reviewer_id,
                reason="   "
            )
        
        assert "Rejection reason is required" in str(exc_info.value), (
            "Whitespace-only rejection reason should raise ValueError with descriptive message"
        )
        
        # Assert: Data remains in UNDER_REVIEW state
        temp_data = db_session.query(TempDataModel).filter(
            TempDataModel.id == data_id
        ).first()
        assert temp_data.state == DataState.UNDER_REVIEW, (
            "After failed rejection, data should remain in UNDER_REVIEW state"
        )
    
    @given(
        submitter_id=user_id_strategy,
        initial_reviewer_id=user_id_strategy,
        actual_reviewer_id=user_id_strategy,
        comments=comment_strategy
    )
    @settings(max_examples=20, deadline=None)
    def test_reviewer_assignment_workflow(
        self,
        db_session: Session,
        submitter_id: str,
        initial_reviewer_id: str,
        actual_reviewer_id: str,
        comments: str
    ):
        """
        Property: Reviewer assignment workflow integrity.
        
        For any review workflow with reviewer assignment:
        1. Initial submission can optionally assign a reviewer
        2. Reviewer can be reassigned before decision
        3. Only assigned reviewer can approve/reject
        """
        # Ensure reviewers are different
        assume(initial_reviewer_id != actual_reviewer_id)
        
        # Create temp data
        data_id = create_temp_data_for_review(db_session, submitter_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Submit for review with initial reviewer
        review_service.submit_for_review(
            data_id=data_id,
            submitted_by=submitter_id,
            reviewer_id=initial_reviewer_id
        )
        
        # Get temp data
        temp_data = db_session.query(TempDataModel).filter(
            TempDataModel.id == data_id
        ).first()
        
        # Assert: Initial reviewer is assigned
        assert temp_data.reviewed_by == initial_reviewer_id
        
        # Reassign to different reviewer
        review_service.assign_reviewer(
            review_id=data_id,
            reviewer_id=actual_reviewer_id,
            assigned_by=submitter_id
        )
        
        # Refresh temp data
        db_session.refresh(temp_data)
        
        # Assert: Reviewer is updated
        assert temp_data.reviewed_by == actual_reviewer_id, (
            f"After reassignment, reviewed_by should be {actual_reviewer_id}, "
            f"but is {temp_data.reviewed_by}"
        )
        
        # Attempt approval by wrong reviewer (should fail)
        with pytest.raises(ValueError) as exc_info:
            review_service.approve_data(
                review_id=data_id,
                reviewer_id=initial_reviewer_id,
                comments=comments
            )
        
        assert "Only assigned reviewer" in str(exc_info.value), (
            "Approval by non-assigned reviewer should raise ValueError"
        )
        
        # Approve by correct reviewer (should succeed)
        approval_result = review_service.approve_data(
            review_id=data_id,
            reviewer_id=actual_reviewer_id,
            comments=comments
        )
        
        # Assert: Approval succeeds
        assert approval_result.approved_by == actual_reviewer_id
        assert approval_result.transferred_to_sample_library is True
    
    @given(
        submitter_id=user_id_strategy,
        reviewer_id=user_id_strategy,
        comments=comment_strategy
    )
    @settings(max_examples=20, deadline=None)
    def test_state_transition_sequence_integrity(
        self,
        db_session: Session,
        submitter_id: str,
        reviewer_id: str,
        comments: str
    ):
        """
        Property: State transition sequence follows state machine.
        
        For any review workflow, state transitions must follow the sequence:
        TEMP_STORED → UNDER_REVIEW → APPROVED → IN_SAMPLE_LIBRARY
        or
        TEMP_STORED → UNDER_REVIEW → REJECTED
        """
        # Create temp data
        data_id = create_temp_data_for_review(db_session, submitter_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Get initial state
        temp_data = db_session.query(TempDataModel).filter(
            TempDataModel.id == data_id
        ).first()
        
        # Assert: Initial state is TEMP_STORED
        assert temp_data.state == DataState.TEMP_STORED, (
            f"Initial state should be TEMP_STORED, but is {temp_data.state.value}"
        )
        
        # Submit for review
        review_service.submit_for_review(
            data_id=data_id,
            submitted_by=submitter_id,
            reviewer_id=reviewer_id
        )
        
        # Refresh and check state
        db_session.refresh(temp_data)
        assert temp_data.state == DataState.UNDER_REVIEW, (
            f"After submission, state should be UNDER_REVIEW, but is {temp_data.state.value}"
        )
        
        # Approve data
        review_service.approve_data(
            review_id=data_id,
            reviewer_id=reviewer_id,
            comments=comments
        )
        
        # Refresh and check state
        db_session.refresh(temp_data)
        assert temp_data.state == DataState.APPROVED, (
            f"After approval, state should be APPROVED, but is {temp_data.state.value}"
        )
        
        # After transfer, check final state
        db_session.refresh(temp_data)
        assert temp_data.state == DataState.IN_SAMPLE_LIBRARY, (
            f"After transfer, state should be IN_SAMPLE_LIBRARY, but is {temp_data.state.value}"
        )
    
    def test_cannot_review_non_temp_stored_data(self, db_session: Session):
        """
        Property: Only TEMP_STORED data can be submitted for review.
        
        For any data not in TEMP_STORED state, attempting to submit for
        review should fail with a descriptive error.
        """
        # Create temp data in wrong state
        temp_data = TempDataModel(
            id=uuid4(),
            source_document_id=str(uuid4()),
            content={"test": "data"},
            state=DataState.ANNOTATED,  # Wrong state
            uploaded_by="test_user",
            uploaded_at=datetime.utcnow(),
            metadata_={}
        )
        db_session.add(temp_data)
        db_session.commit()
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Attempt to submit for review
        with pytest.raises(ValueError) as exc_info:
            review_service.submit_for_review(
                data_id=str(temp_data.id),
                submitted_by="test_user",
                reviewer_id="reviewer"
            )
        
        assert "must be in TEMP_STORED state" in str(exc_info.value), (
            "Submitting non-TEMP_STORED data should raise ValueError with descriptive message"
        )
    
    def test_cannot_approve_or_reject_non_under_review_data(self, db_session: Session):
        """
        Property: Only UNDER_REVIEW data can be approved or rejected.
        
        For any data not in UNDER_REVIEW state, attempting to approve or
        reject should fail with a descriptive error.
        """
        # Create temp data in wrong state
        temp_data = TempDataModel(
            id=uuid4(),
            source_document_id=str(uuid4()),
            content={"test": "data"},
            state=DataState.TEMP_STORED,  # Wrong state
            uploaded_by="test_user",
            uploaded_at=datetime.utcnow(),
            metadata_={}
        )
        db_session.add(temp_data)
        db_session.commit()
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Attempt to approve
        with pytest.raises(ValueError) as exc_info:
            review_service.approve_data(
                review_id=str(temp_data.id),
                reviewer_id="reviewer",
                comments="Test"
            )
        
        assert "must be in UNDER_REVIEW state" in str(exc_info.value), (
            "Approving non-UNDER_REVIEW data should raise ValueError"
        )
        
        # Attempt to reject
        with pytest.raises(ValueError) as exc_info:
            review_service.reject_data(
                review_id=str(temp_data.id),
                reviewer_id="reviewer",
                reason="Test reason"
            )
        
        assert "must be in UNDER_REVIEW state" in str(exc_info.value), (
            "Rejecting non-UNDER_REVIEW data should raise ValueError"
        )
