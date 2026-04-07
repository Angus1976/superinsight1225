"""
Property-Based Tests for Review Workflow Integrity

Tests Property 5: Review Workflow Integrity

For any temporary data submitted for review, approving it should transfer it
to the sample library and update its state, while rejecting it should mark
it as rejected with the reason recorded.

**Validates: Requirements 3.1, 3.2, 3.3**
"""

import pytest
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4, UUID
from sqlalchemy.orm import Session
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from tests.property.sqlite_uuid_compat import uuid_pk_eq

from src.services.review_service import (
    ReviewService,
    ReviewRequest,
    ApprovalResult,
    RejectionResult
)
from src.models.data_lifecycle import (
    TempDataModel,
    SampleModel,
    DataState,
    ReviewStatus,
    ResourceType,
    OperationType,
    OperationResult,
    Action
)


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating user IDs
user_id_strategy = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        min_codepoint=ord('a'),
        max_codepoint=ord('z')
    )
)

# Strategy for generating document IDs
document_id_strategy = st.text(
    min_size=1,
    max_size=100,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        min_codepoint=ord('a'),
        max_codepoint=ord('z')
    )
)

# Strategy for generating content
content_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=50),
    values=st.one_of(
        st.text(min_size=0, max_size=200),
        st.lists(st.text(min_size=0, max_size=50)),
        st.integers(min_value=0, max_value=1000),
        st.floats(min_value=0.0, max_value=1.0)
    ),
    max_size=20
)

# Strategy for generating metadata
metadata_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=30),
    values=st.one_of(
        st.text(min_size=0, max_size=100),
        st.lists(st.text(min_size=1, max_size=20)),
        st.integers(min_value=0, max_value=100)
    ),
    max_size=10
)

# Strategy for generating rejection reasons
rejection_reason_strategy = st.text(
    min_size=10,
    max_size=500,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Po'),
        min_codepoint=ord('a'),
        max_codepoint=ord('z')
    )
).filter(lambda x: x.strip())

# Strategy for generating approval comments
approval_comment_strategy = st.one_of(
    st.none(),
    st.text(
        min_size=0,
        max_size=300,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Po'),
            min_codepoint=ord('a'),
            max_codepoint=ord('z')
        )
    )
)

# Strategy for generating categories
category_strategy = st.sampled_from([
    'general', 'text', 'image', 'audio', 'video',
    'document', 'dataset', 'model', 'annotation'
])


# ============================================================================
# Helper Functions
# ============================================================================

def create_temp_data(
    db: Session,
    data_id: UUID,
    document_id: str,
    content: Dict[str, Any],
    metadata: Dict[str, Any],
    uploaded_by: str
) -> TempDataModel:
    """
    Create a temp data record in the database.
    
    Args:
        db: Database session
        data_id: UUID for the temp data
        document_id: Source document ID
        content: Content dictionary
        metadata: Metadata dictionary
        uploaded_by: User who uploaded the data
    
    Returns:
        Created TempDataModel instance
    """
    temp_data = TempDataModel(
        id=data_id,
        source_document_id=document_id,
        content=content,
        state=DataState.TEMP_STORED,
        uploaded_by=uploaded_by,
        uploaded_at=datetime.utcnow(),
        review_status=None,
        reviewed_by=None,
        reviewed_at=None,
        rejection_reason=None,
        metadata_=metadata,
        lock_version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(temp_data)
    db.commit()
    db.refresh(temp_data)
    return temp_data


def count_samples_by_data_id(db: Session, data_id: str) -> int:
    """
    Count samples in the sample library for a given data ID.
    
    Args:
        db: Database session
        data_id: Original data ID
    
    Returns:
        Number of samples found
    """
    return db.query(SampleModel).filter(SampleModel.data_id == str(data_id)).count()


def get_temp_data_state(db: Session, data_id: UUID) -> DataState:
    """
    Get the current state of temp data.
    
    Args:
        db: Database session
        data_id: Temp data ID
    
    Returns:
        Current DataState
    """
    temp_data = db.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, data_id)).first()
    return temp_data.state if temp_data else None


def get_temp_data_review_status(db: Session, data_id: UUID) -> Optional[ReviewStatus]:
    """
    Get the current review status of temp data.
    
    Args:
        db: Database session
        data_id: Temp data ID
    
    Returns:
        Current ReviewStatus or None
    """
    temp_data = db.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, data_id)).first()
    return temp_data.review_status if temp_data else None


def get_temp_data_rejection_reason(db: Session, data_id: UUID) -> Optional[str]:
    """
    Get the rejection reason for temp data.
    
    Args:
        db: Database session
        data_id: Temp data ID
    
    Returns:
        Rejection reason or None
    """
    temp_data = db.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, data_id)).first()
    return temp_data.rejection_reason if temp_data else None


# ============================================================================
# Property 5: Review Workflow Integrity
# **Validates: Requirements 3.1, 3.2, 3.3**
# ============================================================================

@pytest.mark.property
class TestReviewWorkflowIntegrity:
    """
    Property 5: Review Workflow Integrity
    
    For any temporary data submitted for review, approving it should transfer
    it to the sample library and update its state, while rejecting it should
    mark it as rejected with the reason recorded.
    """
    
    @given(
        content=content_strategy,
        metadata=metadata_strategy,
        uploaded_by=user_id_strategy,
        document_id=document_id_strategy,
        reviewer_id=user_id_strategy,
        comments=approval_comment_strategy
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_approve_data_transfers_to_sample_library(
        self,
        db_session: Session,
        content: Dict[str, Any],
        metadata: Dict[str, Any],
        uploaded_by: str,
        document_id: str,
        reviewer_id: str,
        comments: Optional[str]
    ):
        """
        Property: Approving data transfers it to sample library and updates state.
        
        For any temporary data in TEMP_STORED state:
        1. Submit it for review
        2. Approve the data
        3. The data should be transferred to sample library
        4. The state should be updated to IN_SAMPLE_LIBRARY
        5. The review status should be APPROVED
        """
        # Create temp data
        data_id = uuid4()
        temp_data = create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id=document_id,
            content=content,
            metadata=metadata,
            uploaded_by=uploaded_by
        )
        
        # Verify initial state
        assert temp_data.state == DataState.TEMP_STORED
        assert temp_data.review_status is None
        
        # Submit for review
        review_service = ReviewService(db_session)
        review_request = review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by=uploaded_by,
            reviewer_id=reviewer_id
        )
        
        # Verify review request created
        assert review_request is not None
        assert review_request.id == data_id
        assert review_request.data_id == str(data_id)
        assert review_request.submitter_id == uploaded_by
        assert review_request.status in [ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS]
        
        # Verify state changed to UNDER_REVIEW
        temp_data = db_session.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, data_id)).first()
        assert temp_data.state == DataState.UNDER_REVIEW
        
        # Approve the data
        approval_result = review_service.approve_data(
            review_id=str(data_id),
            reviewer_id=reviewer_id,
            comments=comments
        )
        
        # Verify approval result
        assert approval_result is not None
        assert approval_result.review_id == data_id
        assert approval_result.approved_by == reviewer_id
        assert approval_result.transferred_to_sample_library is True
        assert approval_result.sample_id is not None
        
        # Verify state updated to IN_SAMPLE_LIBRARY
        temp_data = db_session.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, data_id)).first()
        assert temp_data.state == DataState.IN_SAMPLE_LIBRARY
        
        # Verify review status is APPROVED
        assert temp_data.review_status == ReviewStatus.APPROVED
        
        # Verify sample was created in sample library
        sample_count = count_samples_by_data_id(db_session, str(data_id))
        assert sample_count >= 1, "At least one sample should be created in sample library"
        
        # Verify sample has correct properties
        sample = db_session.query(SampleModel).filter(
            SampleModel.data_id == str(data_id)
        ).order_by(SampleModel.created_at.desc()).first()
        
        assert sample is not None
        assert sample.content == content
        assert sample.version == 1
        assert sample.metadata_.get('reviewed_by') == reviewer_id
    
    @given(
        content=content_strategy,
        metadata=metadata_strategy,
        uploaded_by=user_id_strategy,
        document_id=document_id_strategy,
        reviewer_id=user_id_strategy,
        reason=rejection_reason_strategy
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_reject_data_marks_as_rejected_with_reason(
        self,
        db_session: Session,
        content: Dict[str, Any],
        metadata: Dict[str, Any],
        uploaded_by: str,
        document_id: str,
        reviewer_id: str,
        reason: str
    ):
        """
        Property: Rejecting data marks it as rejected with reason recorded.
        
        For any temporary data in TEMP_STORED state:
        1. Submit it for review
        2. Reject the data with a reason
        3. The data should be marked as REJECTED
        4. The rejection reason should be recorded
        5. No sample should be created in sample library
        """
        # Create temp data
        data_id = uuid4()
        temp_data = create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id=document_id,
            content=content,
            metadata=metadata,
            uploaded_by=uploaded_by
        )
        
        # Verify initial state
        assert temp_data.state == DataState.TEMP_STORED
        assert temp_data.review_status is None
        
        # Submit for review
        review_service = ReviewService(db_session)
        review_request = review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by=uploaded_by,
            reviewer_id=reviewer_id
        )
        
        # Verify review request created
        assert review_request is not None
        assert review_request.status in [ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS]
        
        # Verify state changed to UNDER_REVIEW
        temp_data = db_session.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, data_id)).first()
        assert temp_data.state == DataState.UNDER_REVIEW
        
        # Reject the data
        rejection_result = review_service.reject_data(
            review_id=str(data_id),
            reviewer_id=reviewer_id,
            reason=reason
        )
        
        # Verify rejection result
        assert rejection_result is not None
        assert rejection_result.review_id == data_id
        assert rejection_result.rejected_by == reviewer_id
        assert rejection_result.reason == reason
        
        # Verify state updated to REJECTED
        temp_data = db_session.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, data_id)).first()
        assert temp_data.state == DataState.REJECTED
        
        # Verify review status is REJECTED
        assert temp_data.review_status == ReviewStatus.REJECTED
        
        # Verify rejection reason is recorded
        assert temp_data.rejection_reason == reason
        
        # Verify reviewed_by is set
        assert temp_data.reviewed_by == reviewer_id
        
        # Verify reviewed_at is set
        assert temp_data.reviewed_at is not None
        
        # Verify no sample was created in sample library
        sample_count = count_samples_by_data_id(db_session, str(data_id))
        assert sample_count == 0, "No samples should be created when data is rejected"
    
    @given(
        content=content_strategy,
        metadata=metadata_strategy,
        uploaded_by=user_id_strategy,
        document_id=document_id_strategy,
        reviewer_id=user_id_strategy
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_submit_for_review_creates_review_request(
        self,
        db_session: Session,
        content: Dict[str, Any],
        metadata: Dict[str, Any],
        uploaded_by: str,
        document_id: str,
        reviewer_id: str
    ):
        """
        Property: Submitting data for review creates a review request.
        
        For any temporary data in TEMP_STORED state:
        1. Submit it for review
        2. A review request should be created
        3. The state should change to UNDER_REVIEW
        """
        # Create temp data
        data_id = uuid4()
        temp_data = create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id=document_id,
            content=content,
            metadata=metadata,
            uploaded_by=uploaded_by
        )
        
        # Submit for review
        review_service = ReviewService(db_session)
        review_request = review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by=uploaded_by,
            reviewer_id=reviewer_id
        )
        
        # Verify review request properties
        assert review_request.id == data_id
        assert review_request.data_id == str(data_id)
        assert review_request.submitter_id == uploaded_by
        assert review_request.reviewer_id == reviewer_id
        assert review_request.status in [ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS]
        assert review_request.submitted_at is not None
        
        # Verify state transition
        temp_data = db_session.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, data_id)).first()
        assert temp_data.state == DataState.UNDER_REVIEW
        assert temp_data.review_status == review_request.status
        assert temp_data.reviewed_by == reviewer_id
    
    @given(
        content=content_strategy,
        metadata=metadata_strategy,
        uploaded_by=user_id_strategy,
        document_id=document_id_strategy,
        reviewer_id=user_id_strategy,
        comments=approval_comment_strategy
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_approval_preserves_content_in_sample(
        self,
        db_session: Session,
        content: Dict[str, Any],
        metadata: Dict[str, Any],
        uploaded_by: str,
        document_id: str,
        reviewer_id: str,
        comments: Optional[str]
    ):
        """
        Property: Content is preserved when transferring to sample library.
        
        When data is approved and transferred to sample library:
        1. The content should be preserved exactly
        2. The metadata should be preserved
        """
        # Create temp data
        data_id = uuid4()
        create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id=document_id,
            content=content,
            metadata=metadata,
            uploaded_by=uploaded_by
        )
        
        # Submit and approve
        review_service = ReviewService(db_session)
        review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by=uploaded_by,
            reviewer_id=reviewer_id
        )
        review_service.approve_data(
            review_id=str(data_id),
            reviewer_id=reviewer_id,
            comments=comments
        )
        
        # Verify content preserved in sample
        sample = db_session.query(SampleModel).filter(
            SampleModel.data_id == str(data_id)
        ).first()
        
        assert sample is not None
        assert sample.content == content
        assert sample.metadata_.get('source') == 'temp_data'
        assert sample.metadata_.get('original_metadata') == metadata
    
    @given(
        content=content_strategy,
        metadata=metadata_strategy,
        uploaded_by=user_id_strategy,
        document_id=document_id_strategy,
        reviewer_id=user_id_strategy,
        reason=rejection_reason_strategy
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rejection_preserves_data_for_resubmit(
        self,
        db_session: Session,
        content: Dict[str, Any],
        metadata: Dict[str, Any],
        uploaded_by: str,
        document_id: str,
        reviewer_id: str,
        reason: str
    ):
        """
        Property: Rejected data is preserved for potential resubmission.
        
        When data is rejected:
        1. The content should be preserved
        2. The rejection reason should be recorded
        3. The data should remain accessible
        """
        # Create temp data
        data_id = uuid4()
        create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id=document_id,
            content=content,
            metadata=metadata,
            uploaded_by=uploaded_by
        )
        
        # Submit and reject
        review_service = ReviewService(db_session)
        review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by=uploaded_by,
            reviewer_id=reviewer_id
        )
        review_service.reject_data(
            review_id=str(data_id),
            reviewer_id=reviewer_id,
            reason=reason
        )
        
        # Verify data preserved
        temp_data = db_session.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, data_id)).first()
        
        assert temp_data is not None
        assert temp_data.content == content
        assert temp_data.metadata_ == metadata
        assert temp_data.rejection_reason == reason
        assert temp_data.state == DataState.REJECTED


# ============================================================================
# Edge Cases Tests
# ============================================================================

@pytest.mark.property
class TestReviewWorkflowEdgeCases:
    """Edge cases for review workflow integrity."""
    
    def test_approve_without_reviewer_assignment(self, db_session: Session):
        """
        Test approval when no reviewer was pre-assigned.
        
        When data is submitted without a specific reviewer,
        any reviewer should be able to approve it.
        """
        data_id = uuid4()
        content = {'sections': [{'title': 'Test', 'content': 'Content'}]}
        
        create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id='doc-123',
            content=content,
            metadata={},
            uploaded_by='user1'
        )
        
        review_service = ReviewService(db_session)
        
        # Submit without pre-assigned reviewer
        review_request = review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by='user1',
            reviewer_id=None
        )
        
        assert review_request.status == ReviewStatus.PENDING
        
        # Approve with a different reviewer
        approval_result = review_service.approve_data(
            review_id=str(data_id),
            reviewer_id='reviewer1',
            comments=None
        )
        
        assert approval_result.transferred_to_sample_library is True
    
    def test_reject_requires_non_empty_reason(self, db_session: Session):
        """
        Test that rejection requires a non-empty reason.
        
        Attempting to reject with an empty reason should fail.
        """
        data_id = uuid4()
        content = {'sections': [{'title': 'Test', 'content': 'Content'}]}
        
        create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id='doc-123',
            content=content,
            metadata={},
            uploaded_by='user1'
        )
        
        review_service = ReviewService(db_session)
        review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by='user1',
            reviewer_id='reviewer1'
        )
        
        # Attempt to reject with empty reason
        with pytest.raises(ValueError, match="Rejection reason is required"):
            review_service.reject_data(
                review_id=str(data_id),
                reviewer_id='reviewer1',
                reason=""
            )
        
        # Verify data is still in UNDER_REVIEW state
        temp_data = db_session.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, data_id)).first()
        assert temp_data.state == DataState.UNDER_REVIEW
    
    def test_cannot_approve_already_rejected_data(self, db_session: Session):
        """
        Test that already rejected data cannot be approved.
        
        Once data is rejected, attempting to approve it should fail.
        """
        data_id = uuid4()
        content = {'sections': [{'title': 'Test', 'content': 'Content'}]}
        
        create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id='doc-123',
            content=content,
            metadata={},
            uploaded_by='user1'
        )
        
        review_service = ReviewService(db_session)
        review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by='user1',
            reviewer_id='reviewer1'
        )
        
        # Reject the data
        review_service.reject_data(
            review_id=str(data_id),
            reviewer_id='reviewer1',
            reason="Data quality issues"
        )
        
        # Attempt to approve rejected data
        with pytest.raises(ValueError, match="UNDER_REVIEW state"):
            review_service.approve_data(
                review_id=str(data_id),
                reviewer_id='reviewer1',
                comments=None
            )
    
    def test_cannot_reject_already_approved_data(self, db_session: Session):
        """
        Test that already approved data cannot be rejected.
        
        Once data is approved and transferred to sample library,
        attempting to reject it should fail.
        """
        data_id = uuid4()
        content = {'sections': [{'title': 'Test', 'content': 'Content'}]}
        
        create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id='doc-123',
            content=content,
            metadata={},
            uploaded_by='user1'
        )
        
        review_service = ReviewService(db_session)
        review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by='user1',
            reviewer_id='reviewer1'
        )
        
        # Approve the data
        review_service.approve_data(
            review_id=str(data_id),
            reviewer_id='reviewer1',
            comments=None
        )
        
        # Attempt to reject approved data
        with pytest.raises(ValueError, match="UNDER_REVIEW state"):
            review_service.reject_data(
                review_id=str(data_id),
                reviewer_id='reviewer1',
                reason="Changed my mind"
            )
    
    def test_get_review_status_returns_complete_info(self, db_session: Session):
        """
        Test that get_review_status returns complete information.
        
        The review status should include all relevant information.
        """
        data_id = uuid4()
        content = {'sections': [{'title': 'Test', 'content': 'Content'}]}
        
        create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id='doc-123',
            content=content,
            metadata={'category': 'test'},
            uploaded_by='user1'
        )
        
        review_service = ReviewService(db_session)
        review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by='user1',
            reviewer_id='reviewer1'
        )
        
        # Get review status
        status = review_service.get_review_status(str(data_id))
        
        assert status['review_id'] == str(data_id)
        assert status['data_id'] == str(data_id)
        assert status['state'] == DataState.UNDER_REVIEW.value
        assert status['reviewer_id'] == 'reviewer1'
        assert status['uploaded_by'] == 'user1'
        assert 'uploaded_at' in status
        assert 'updated_at' in status
    
    def test_approval_with_unicode_content(self, db_session: Session):
        """
        Test approval preserves Unicode content.
        
        Data with Unicode characters should be preserved correctly.
        """
        data_id = uuid4()
        content = {
            'sections': [
                {'title': '测试文档', 'content': '包含中文内容'},
                {'title': 'Emoji Test', 'content': '😀 🎉 ✨'}
            ]
        }
        
        create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id='doc-unicode',
            content=content,
            metadata={'title': '测试标题'},
            uploaded_by='user1'
        )
        
        review_service = ReviewService(db_session)
        review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by='user1',
            reviewer_id='reviewer1'
        )
        review_service.approve_data(
            review_id=str(data_id),
            reviewer_id='reviewer1',
            comments='批准 with Chinese comments 中文评论'
        )
        
        # Verify Unicode content preserved
        sample = db_session.query(SampleModel).filter(
            SampleModel.data_id == str(data_id)
        ).first()
        
        assert sample is not None
        assert sample.content == content
        assert '测试文档' in str(sample.content)
        assert '😀' in str(sample.content)
    
    def test_rejection_with_unicode_reason(self, db_session: Session):
        """
        Test rejection with Unicode reason.
        
        Rejection reasons with Unicode characters should be preserved.
        """
        data_id = uuid4()
        content = {'sections': [{'title': 'Test', 'content': 'Content'}]}
        
        create_temp_data(
            db=db_session,
            data_id=data_id,
            document_id='doc-123',
            content=content,
            metadata={},
            uploaded_by='user1'
        )
        
        review_service = ReviewService(db_session)
        review_service.submit_for_review(
            data_id=str(data_id),
            submitted_by='user1',
            reviewer_id='reviewer1'
        )
        
        unicode_reason = "数据质量问题 - 包含错误的内容"
        review_service.reject_data(
            review_id=str(data_id),
            reviewer_id='reviewer1',
            reason=unicode_reason
        )
        
        # Verify Unicode reason preserved
        temp_data = db_session.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, data_id)).first()
        assert temp_data.rejection_reason == unicode_reason
        assert '数据质量问题' in temp_data.rejection_reason