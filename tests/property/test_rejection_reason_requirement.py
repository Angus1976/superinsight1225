"""
Property-Based Tests for Rejection Reason Requirement

Tests Property 27: Rejection Reason Requirement

**Validates: Requirements 12.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from src.models.data_lifecycle import (
    DataState,
    ResourceType,
    TempDataModel,
    ReviewStatus
)
from src.services.review_service import ReviewService
from tests.property.sqlite_uuid_compat import uuid_pk_eq


def _temp_data_by_id(db: Session, row_id):
    """SQLite + PGUUID: primary-key lookup by string id."""
    return db.query(TempDataModel).filter(uuid_pk_eq(TempDataModel.id, row_id)).first()


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating user IDs
user_id_strategy = st.text(min_size=1, max_size=50, alphabet=st.characters(
    whitelist_categories=('Lu', 'Ll', 'Nd'),
    min_codepoint=ord('a'),
    max_codepoint=ord('z')
))

# Strategy for generating valid rejection reasons (non-empty, non-whitespace)
valid_rejection_reason_strategy = st.text(
    min_size=1, 
    max_size=200,
    alphabet=st.characters(
        blacklist_characters='\x00',
        blacklist_categories=('Cc', 'Cs')
    )
).filter(lambda x: x.strip())  # Ensure not whitespace-only

# Strategy for generating invalid rejection reasons (empty or whitespace-only)
invalid_rejection_reason_strategy = st.one_of(
    st.just(""),  # Empty string
    st.text(min_size=1, max_size=20, alphabet=st.just(" ")),  # Whitespace-only
    st.text(min_size=1, max_size=20, alphabet=st.just("\t")),  # Tab-only
    st.text(min_size=1, max_size=20, alphabet=st.just("\n")),  # Newline-only
    st.text(min_size=1, max_size=20).filter(lambda x: not x.strip())  # Mixed whitespace
)


# ============================================================================
# Helper Functions
# ============================================================================

def create_temp_data_under_review(db: Session, uploaded_by: str, reviewer_id: str) -> str:
    """Create a temporary data item in UNDER_REVIEW state ready for rejection"""
    temp_data = TempDataModel(
        id=uuid4(),
        source_document_id=str(uuid4()),
        content={"test": "data", "sections": [{"title": "Test", "content": "Content"}]},
        state=DataState.UNDER_REVIEW,
        uploaded_by=uploaded_by,
        uploaded_at=datetime.utcnow(),
        reviewed_by=reviewer_id,
        metadata_={"category": "test", "tags": ["test"]}
    )
    db.add(temp_data)
    db.commit()
    return str(temp_data.id)


# ============================================================================
# Property 27: Rejection Reason Requirement
# **Validates: Requirements 12.5**
# ============================================================================

@pytest.mark.property
class TestRejectionReasonRequirement:
    """
    Property 27: Rejection Reason Requirement
    
    For all rejection operations, a non-empty rejection reason must be provided.
    Empty strings, whitespace-only strings, or null values must be rejected.
    The rejection reason must be stored and retrievable.
    """
    
    @given(
        submitter_id=user_id_strategy,
        reviewer_id=user_id_strategy,
        invalid_reason=invalid_rejection_reason_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rejection_requires_non_empty_reason(
        self,
        db_session: Session,
        submitter_id: str,
        reviewer_id: str,
        invalid_reason: str
    ):
        """
        Property: Rejection operations must fail with empty or whitespace-only reasons.
        
        For any rejection attempt with an invalid reason (empty, whitespace-only),
        the operation must fail with a descriptive ValueError.
        """
        # Create temp data in UNDER_REVIEW state
        data_id = create_temp_data_under_review(db_session, submitter_id, reviewer_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Get initial state
        temp_data = _temp_data_by_id(db_session, data_id)
        
        initial_state = temp_data.state
        initial_review_status = temp_data.review_status
        initial_rejection_reason = temp_data.rejection_reason
        
        # Attempt rejection with invalid reason
        with pytest.raises(ValueError) as exc_info:
            review_service.reject_data(
                review_id=data_id,
                reviewer_id=reviewer_id,
                reason=invalid_reason
            )
        
        # Assert: Error message is descriptive
        error_message = str(exc_info.value)
        assert "Rejection reason is required" in error_message or \
               "cannot be empty" in error_message, (
            f"Error message should mention rejection reason requirement, "
            f"but got: {error_message}"
        )
        
        # Refresh temp data
        db_session.refresh(temp_data)
        
        # Assert: Data state remains unchanged
        assert temp_data.state == initial_state, (
            f"After failed rejection, state should remain {initial_state.value}, "
            f"but is {temp_data.state.value}"
        )
        
        # Assert: Review status remains unchanged
        assert temp_data.review_status == initial_review_status, (
            f"After failed rejection, review_status should remain unchanged"
        )
        
        # Assert: Rejection reason remains unchanged (should be None)
        assert temp_data.rejection_reason == initial_rejection_reason, (
            f"After failed rejection, rejection_reason should remain unchanged"
        )
    
    @given(
        submitter_id=user_id_strategy,
        reviewer_id=user_id_strategy,
        valid_reason=valid_rejection_reason_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rejection_succeeds_with_valid_reason(
        self,
        db_session: Session,
        submitter_id: str,
        reviewer_id: str,
        valid_reason: str
    ):
        """
        Property: Rejection operations succeed with valid non-empty reasons.
        
        For any rejection with a valid reason (non-empty, non-whitespace),
        the operation must succeed and the reason must be stored correctly.
        """
        # Ensure reason is valid (not just whitespace)
        assume(valid_reason.strip())
        
        # Create temp data in UNDER_REVIEW state
        data_id = create_temp_data_under_review(db_session, submitter_id, reviewer_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Reject data with valid reason
        rejection_result = review_service.reject_data(
            review_id=data_id,
            reviewer_id=reviewer_id,
            reason=valid_reason
        )
        
        # Assert: Rejection result is correct
        assert str(rejection_result.review_id) == str(data_id), (
            f"Rejection result review_id should be {data_id}, "
            f"but is {rejection_result.review_id}"
        )
        assert rejection_result.rejected_by == reviewer_id, (
            f"Rejection result rejected_by should be {reviewer_id}, "
            f"but is {rejection_result.rejected_by}"
        )
        assert rejection_result.reason == valid_reason, (
            f"Rejection result reason should be '{valid_reason}', "
            f"but is '{rejection_result.reason}'"
        )
        assert rejection_result.rejected_at is not None, (
            "Rejection result rejected_at should be set"
        )
        
        # Get temp data after rejection
        temp_data = _temp_data_by_id(db_session, data_id)
        
        # Assert: Data is in REJECTED state
        assert temp_data.state == DataState.REJECTED, (
            f"After rejection, state should be REJECTED, "
            f"but is {temp_data.state.value}"
        )
        
        # Assert: Review status is REJECTED
        assert temp_data.review_status == ReviewStatus.REJECTED, (
            f"After rejection, review_status should be REJECTED, "
            f"but is {temp_data.review_status.value if temp_data.review_status else None}"
        )
        
        # Assert: Rejection reason is stored correctly
        assert temp_data.rejection_reason is not None, (
            "After rejection, rejection_reason should be set"
        )
        assert temp_data.rejection_reason == valid_reason, (
            f"Stored rejection reason should be '{valid_reason}', "
            f"but is '{temp_data.rejection_reason}'"
        )
        assert temp_data.rejection_reason.strip(), (
            "Stored rejection reason should not be empty or whitespace-only"
        )
        
        # Assert: Reviewer information is recorded
        assert temp_data.reviewed_by == reviewer_id, (
            f"After rejection, reviewed_by should be {reviewer_id}, "
            f"but is {temp_data.reviewed_by}"
        )
        assert temp_data.reviewed_at is not None, (
            "After rejection, reviewed_at should be set"
        )
    
    @given(
        submitter_id=user_id_strategy,
        reviewer_id=user_id_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rejection_with_none_reason_fails(
        self,
        db_session: Session,
        submitter_id: str,
        reviewer_id: str
    ):
        """
        Property: Rejection operations must fail with None as reason.
        
        For any rejection attempt with None as the reason, the operation
        must fail with a descriptive error.
        """
        # Create temp data in UNDER_REVIEW state
        data_id = create_temp_data_under_review(db_session, submitter_id, reviewer_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Attempt rejection with None reason
        with pytest.raises((ValueError, TypeError)) as exc_info:
            review_service.reject_data(
                review_id=data_id,
                reviewer_id=reviewer_id,
                reason=None
            )
        
        # Assert: Error is raised
        assert exc_info.value is not None, (
            "Rejection with None reason should raise an error"
        )
        
        # Get temp data
        temp_data = _temp_data_by_id(db_session, data_id)
        
        # Assert: Data remains in UNDER_REVIEW state
        assert temp_data.state == DataState.UNDER_REVIEW, (
            f"After failed rejection, state should remain UNDER_REVIEW, "
            f"but is {temp_data.state.value}"
        )
        
        # Assert: Rejection reason is not set
        assert temp_data.rejection_reason is None, (
            "After failed rejection, rejection_reason should remain None"
        )
    
    @given(
        submitter_id=user_id_strategy,
        reviewer_id=user_id_strategy,
        reason1=valid_rejection_reason_strategy,
        reason2=valid_rejection_reason_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rejection_reason_is_retrievable(
        self,
        db_session: Session,
        submitter_id: str,
        reviewer_id: str,
        reason1: str,
        reason2: str
    ):
        """
        Property: Rejection reasons are stored and retrievable.
        
        For any rejected data, the rejection reason must be retrievable
        from the database and match the originally provided reason.
        """
        # Ensure reasons are valid
        assume(reason1.strip())
        assume(reason2.strip())
        
        # Create two temp data items
        data_id1 = create_temp_data_under_review(db_session, submitter_id, reviewer_id)
        data_id2 = create_temp_data_under_review(db_session, submitter_id, reviewer_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Reject both with different reasons
        review_service.reject_data(
            review_id=data_id1,
            reviewer_id=reviewer_id,
            reason=reason1
        )
        
        review_service.reject_data(
            review_id=data_id2,
            reviewer_id=reviewer_id,
            reason=reason2
        )
        
        # Retrieve data from database
        temp_data1 = _temp_data_by_id(db_session, data_id1)
        temp_data2 = _temp_data_by_id(db_session, data_id2)
        
        # Assert: Both rejection reasons are stored correctly
        assert temp_data1.rejection_reason == reason1, (
            f"Data 1 rejection reason should be '{reason1}', "
            f"but is '{temp_data1.rejection_reason}'"
        )
        
        assert temp_data2.rejection_reason == reason2, (
            f"Data 2 rejection reason should be '{reason2}', "
            f"but is '{temp_data2.rejection_reason}'"
        )
        
        # Assert: Rejection reasons are independent
        if reason1 != reason2:
            assert temp_data1.rejection_reason != temp_data2.rejection_reason, (
                "Different rejection reasons should be stored independently"
            )
    
    @given(
        submitter_id=user_id_strategy,
        reviewer_id=user_id_strategy,
        valid_reason=valid_rejection_reason_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rejection_reason_preserves_content(
        self,
        db_session: Session,
        submitter_id: str,
        reviewer_id: str,
        valid_reason: str
    ):
        """
        Property: Rejection reasons preserve exact content including special characters.
        
        For any rejection reason containing special characters, punctuation,
        or unicode, the stored reason must exactly match the input.
        """
        # Ensure reason is valid
        assume(valid_reason.strip())
        
        # Create temp data in UNDER_REVIEW state
        data_id = create_temp_data_under_review(db_session, submitter_id, reviewer_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Reject data
        review_service.reject_data(
            review_id=data_id,
            reviewer_id=reviewer_id,
            reason=valid_reason
        )
        
        # Retrieve data
        temp_data = _temp_data_by_id(db_session, data_id)
        
        # Assert: Rejection reason exactly matches input
        assert temp_data.rejection_reason == valid_reason, (
            f"Stored rejection reason should exactly match input.\n"
            f"Expected: '{valid_reason}'\n"
            f"Got: '{temp_data.rejection_reason}'"
        )
        
        # Assert: Length is preserved
        assert len(temp_data.rejection_reason) == len(valid_reason), (
            f"Rejection reason length should be preserved: "
            f"expected {len(valid_reason)}, got {len(temp_data.rejection_reason)}"
        )
    
    @given(
        submitter_id=user_id_strategy,
        reviewer_id=user_id_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multiple_rejection_attempts_with_invalid_reasons(
        self,
        db_session: Session,
        submitter_id: str,
        reviewer_id: str
    ):
        """
        Property: Multiple rejection attempts with invalid reasons all fail.
        
        For any data item, multiple consecutive rejection attempts with
        invalid reasons should all fail, and the data should remain in
        UNDER_REVIEW state.
        """
        # Create temp data in UNDER_REVIEW state
        data_id = create_temp_data_under_review(db_session, submitter_id, reviewer_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # List of invalid reasons to test
        invalid_reasons = [
            "",
            "   ",
            "\t",
            "\n",
            "  \t  \n  ",
            None
        ]
        
        for invalid_reason in invalid_reasons:
            # Attempt rejection with invalid reason
            with pytest.raises((ValueError, TypeError)):
                review_service.reject_data(
                    review_id=data_id,
                    reviewer_id=reviewer_id,
                    reason=invalid_reason
                )
            
            # Verify data remains in UNDER_REVIEW state
            temp_data = _temp_data_by_id(db_session, data_id)
            
            assert temp_data.state == DataState.UNDER_REVIEW, (
                f"After failed rejection with reason '{repr(invalid_reason)}', "
                f"state should remain UNDER_REVIEW, but is {temp_data.state.value}"
            )
            
            assert temp_data.rejection_reason is None, (
                f"After failed rejection with reason '{repr(invalid_reason)}', "
                f"rejection_reason should remain None"
            )
    
    @given(
        submitter_id=user_id_strategy,
        reviewer_id=user_id_strategy,
        valid_reason=valid_rejection_reason_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_rejection_reason_in_audit_log(
        self,
        db_session: Session,
        submitter_id: str,
        reviewer_id: str,
        valid_reason: str
    ):
        """
        Property: Rejection reasons are recorded in audit logs.
        
        For any rejection operation, the rejection reason should be
        included in the audit log details for traceability.
        """
        # Ensure reason is valid
        assume(valid_reason.strip())
        
        # Create temp data in UNDER_REVIEW state
        data_id = create_temp_data_under_review(db_session, submitter_id, reviewer_id)
        
        # Create review service
        review_service = ReviewService(db_session)
        
        # Reject data
        review_service.reject_data(
            review_id=data_id,
            reviewer_id=reviewer_id,
            reason=valid_reason
        )
        
        # Query audit logs for this operation
        from src.models.data_lifecycle import AuditLogModel, Action
        
        audit_logs = db_session.query(AuditLogModel).filter(
            AuditLogModel.resource_id == data_id,
            AuditLogModel.action == Action.REVIEW
        ).all()
        
        # Assert: At least one audit log exists
        assert len(audit_logs) > 0, (
            "Rejection operation should create audit log entries"
        )
        
        # Find the rejection audit log
        rejection_log = None
        for log in audit_logs:
            if log.details and log.details.get('action') == 'reject_data':
                rejection_log = log
                break
        
        # Assert: Rejection audit log exists
        assert rejection_log is not None, (
            "Audit log for rejection operation should exist"
        )
        
        # Assert: Rejection reason is in audit log details
        assert rejection_log.details is not None, (
            "Rejection audit log should have details"
        )
        assert 'reason' in rejection_log.details, (
            "Rejection audit log details should include 'reason' field"
        )
        assert rejection_log.details['reason'] == valid_reason, (
            f"Audit log reason should be '{valid_reason}', "
            f"but is '{rejection_log.details['reason']}'"
        )
