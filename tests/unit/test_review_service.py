"""
Unit tests for Review Service

Tests the review workflow including submission, assignment, approval,
rejection, and integration with State Manager and Audit Logger.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.connection import Base
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
from src.services.review_service import ReviewService


# Test database setup
@pytest.fixture(scope='function')
def db_session():
    """Create a test database session"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def review_service(db_session):
    """Create a ReviewService instance"""
    return ReviewService(db_session)


@pytest.fixture
def temp_data(db_session):
    """Create a temporary data item for testing"""
    data = TempDataModel(
        id=uuid4(),
        source_document_id='doc-123',
        content={'title': 'Test Document', 'sections': []},
        state=DataState.TEMP_STORED,
        uploaded_by='user-1',
        uploaded_at=datetime.utcnow(),
        review_status=None,
        reviewed_by=None,
        reviewed_at=None,
        rejection_reason=None,
        metadata_={'category': 'test', 'tags': ['test']},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(data)
    db_session.commit()
    db_session.refresh(data)
    return data


# ============================================================================
# Test: Submit for Review
# ============================================================================

def test_submit_for_review_success(review_service, temp_data, db_session):
    """Test successful submission for review"""
    # Submit for review
    result = review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1'
    )
    
    # Verify result
    assert result.data_id == str(temp_data.id)
    assert result.submitter_id == 'user-1'
    assert result.status == ReviewStatus.PENDING
    assert result.reviewer_id is None
    
    # Verify database state
    db_session.refresh(temp_data)
    assert temp_data.state == DataState.UNDER_REVIEW
    assert temp_data.review_status == ReviewStatus.PENDING


def test_submit_for_review_with_reviewer(review_service, temp_data, db_session):
    """Test submission for review with immediate reviewer assignment"""
    # Submit for review with reviewer
    result = review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    
    # Verify result
    assert result.reviewer_id == 'reviewer-1'
    assert result.status == ReviewStatus.IN_PROGRESS
    
    # Verify database state
    db_session.refresh(temp_data)
    assert temp_data.state == DataState.UNDER_REVIEW
    assert temp_data.review_status == ReviewStatus.IN_PROGRESS
    assert temp_data.reviewed_by == 'reviewer-1'


def test_submit_for_review_invalid_state(review_service, temp_data, db_session):
    """Test submission fails when data is not in TEMP_STORED state"""
    # Change state to UNDER_REVIEW
    temp_data.state = DataState.UNDER_REVIEW
    db_session.commit()
    
    # Attempt to submit for review
    with pytest.raises(ValueError, match="Data must be in TEMP_STORED state"):
        review_service.submit_for_review(
            data_id=str(temp_data.id),
            submitted_by='user-1'
        )


def test_submit_for_review_not_found(review_service):
    """Test submission fails when data not found"""
    with pytest.raises(ValueError, match="not found"):
        review_service.submit_for_review(
            data_id=str(uuid4()),
            submitted_by='user-1'
        )


# ============================================================================
# Test: Assign Reviewer
# ============================================================================

def test_assign_reviewer_success(review_service, temp_data, db_session):
    """Test successful reviewer assignment"""
    # Submit for review first
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1'
    )
    
    # Assign reviewer
    review_service.assign_reviewer(
        review_id=str(temp_data.id),
        reviewer_id='reviewer-1',
        assigned_by='admin-1'
    )
    
    # Verify database state
    db_session.refresh(temp_data)
    assert temp_data.reviewed_by == 'reviewer-1'
    assert temp_data.review_status == ReviewStatus.IN_PROGRESS


def test_assign_reviewer_invalid_state(review_service, temp_data, db_session):
    """Test reviewer assignment fails when not in UNDER_REVIEW state"""
    # Data is in TEMP_STORED state
    with pytest.raises(ValueError, match="Data must be in UNDER_REVIEW state"):
        review_service.assign_reviewer(
            review_id=str(temp_data.id),
            reviewer_id='reviewer-1',
            assigned_by='admin-1'
        )


def test_assign_reviewer_not_found(review_service):
    """Test reviewer assignment fails when review not found"""
    with pytest.raises(ValueError, match="not found"):
        review_service.assign_reviewer(
            review_id=str(uuid4()),
            reviewer_id='reviewer-1',
            assigned_by='admin-1'
        )


# ============================================================================
# Test: Approve Data
# ============================================================================

def test_approve_data_success(review_service, temp_data, db_session):
    """Test successful data approval and transfer to sample library"""
    # Submit for review with reviewer
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    
    # Approve data
    result = review_service.approve_data(
        review_id=str(temp_data.id),
        reviewer_id='reviewer-1',
        comments='Looks good'
    )
    
    # Verify result
    assert result.review_id == temp_data.id
    assert result.approved_by == 'reviewer-1'
    assert result.transferred_to_sample_library is True
    assert result.sample_id is not None
    
    # Verify database state
    db_session.refresh(temp_data)
    assert temp_data.state == DataState.IN_SAMPLE_LIBRARY
    assert temp_data.review_status == ReviewStatus.APPROVED
    assert temp_data.reviewed_by == 'reviewer-1'
    assert temp_data.reviewed_at is not None
    
    # Verify sample was created
    sample = db_session.query(SampleModel).filter(
        SampleModel.id == result.sample_id
    ).first()
    assert sample is not None
    assert sample.data_id == str(temp_data.id)
    assert sample.content == temp_data.content
    assert sample.metadata_['reviewed_by'] == 'reviewer-1'
    assert sample.metadata_['approval_comments'] == 'Looks good'


def test_approve_data_without_comments(review_service, temp_data, db_session):
    """Test data approval without comments"""
    # Submit for review
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    
    # Approve without comments
    result = review_service.approve_data(
        review_id=str(temp_data.id),
        reviewer_id='reviewer-1'
    )
    
    # Verify approval succeeded
    assert result.transferred_to_sample_library is True
    db_session.refresh(temp_data)
    assert temp_data.review_status == ReviewStatus.APPROVED


def test_approve_data_invalid_state(review_service, temp_data):
    """Test approval fails when not in UNDER_REVIEW state"""
    # Data is in TEMP_STORED state
    with pytest.raises(ValueError, match="Data must be in UNDER_REVIEW state"):
        review_service.approve_data(
            review_id=str(temp_data.id),
            reviewer_id='reviewer-1'
        )


def test_approve_data_wrong_reviewer(review_service, temp_data, db_session):
    """Test approval fails when wrong reviewer attempts to approve"""
    # Submit for review with specific reviewer
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    
    # Attempt to approve with different reviewer
    with pytest.raises(ValueError, match="Only assigned reviewer"):
        review_service.approve_data(
            review_id=str(temp_data.id),
            reviewer_id='reviewer-2'
        )


def test_approve_data_not_found(review_service):
    """Test approval fails when review not found"""
    with pytest.raises(ValueError, match="not found"):
        review_service.approve_data(
            review_id=str(uuid4()),
            reviewer_id='reviewer-1'
        )


# ============================================================================
# Test: Reject Data
# ============================================================================

def test_reject_data_success(review_service, temp_data, db_session):
    """Test successful data rejection"""
    # Submit for review
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    
    # Reject data
    result = review_service.reject_data(
        review_id=str(temp_data.id),
        reviewer_id='reviewer-1',
        reason='Quality issues found'
    )
    
    # Verify result
    assert result.review_id == temp_data.id
    assert result.rejected_by == 'reviewer-1'
    assert result.reason == 'Quality issues found'
    
    # Verify database state
    db_session.refresh(temp_data)
    assert temp_data.state == DataState.REJECTED
    assert temp_data.review_status == ReviewStatus.REJECTED
    assert temp_data.reviewed_by == 'reviewer-1'
    assert temp_data.reviewed_at is not None
    assert temp_data.rejection_reason == 'Quality issues found'


def test_reject_data_empty_reason(review_service, temp_data, db_session):
    """Test rejection fails when reason is empty"""
    # Submit for review
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    
    # Attempt to reject with empty reason
    with pytest.raises(ValueError, match="Rejection reason is required"):
        review_service.reject_data(
            review_id=str(temp_data.id),
            reviewer_id='reviewer-1',
            reason=''
        )
    
    # Attempt to reject with whitespace-only reason
    with pytest.raises(ValueError, match="Rejection reason is required"):
        review_service.reject_data(
            review_id=str(temp_data.id),
            reviewer_id='reviewer-1',
            reason='   '
        )


def test_reject_data_invalid_state(review_service, temp_data):
    """Test rejection fails when not in UNDER_REVIEW state"""
    # Data is in TEMP_STORED state
    with pytest.raises(ValueError, match="Data must be in UNDER_REVIEW state"):
        review_service.reject_data(
            review_id=str(temp_data.id),
            reviewer_id='reviewer-1',
            reason='Bad quality'
        )


def test_reject_data_wrong_reviewer(review_service, temp_data, db_session):
    """Test rejection fails when wrong reviewer attempts to reject"""
    # Submit for review with specific reviewer
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    
    # Attempt to reject with different reviewer
    with pytest.raises(ValueError, match="Only assigned reviewer"):
        review_service.reject_data(
            review_id=str(temp_data.id),
            reviewer_id='reviewer-2',
            reason='Bad quality'
        )


def test_reject_data_not_found(review_service):
    """Test rejection fails when review not found"""
    with pytest.raises(ValueError, match="not found"):
        review_service.reject_data(
            review_id=str(uuid4()),
            reviewer_id='reviewer-1',
            reason='Bad quality'
        )


# ============================================================================
# Test: Get Review Status
# ============================================================================

def test_get_review_status_pending(review_service, temp_data, db_session):
    """Test getting status of pending review"""
    # Submit for review
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1'
    )
    
    # Get status
    status = review_service.get_review_status(str(temp_data.id))
    
    # Verify status
    assert status['review_id'] == str(temp_data.id)
    assert status['state'] == DataState.UNDER_REVIEW.value
    assert status['review_status'] == ReviewStatus.PENDING.value
    assert status['reviewer_id'] is None
    assert status['reviewed_at'] is None
    assert status['rejection_reason'] is None
    assert status['uploaded_by'] == 'user-1'


def test_get_review_status_approved(review_service, temp_data, db_session):
    """Test getting status of approved review"""
    # Submit and approve
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    review_service.approve_data(
        review_id=str(temp_data.id),
        reviewer_id='reviewer-1',
        comments='Good'
    )
    
    # Get status
    status = review_service.get_review_status(str(temp_data.id))
    
    # Verify status
    assert status['state'] == DataState.IN_SAMPLE_LIBRARY.value
    assert status['review_status'] == ReviewStatus.APPROVED.value
    assert status['reviewer_id'] == 'reviewer-1'
    assert status['reviewed_at'] is not None


def test_get_review_status_rejected(review_service, temp_data, db_session):
    """Test getting status of rejected review"""
    # Submit and reject
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    review_service.reject_data(
        review_id=str(temp_data.id),
        reviewer_id='reviewer-1',
        reason='Quality issues'
    )
    
    # Get status
    status = review_service.get_review_status(str(temp_data.id))
    
    # Verify status
    assert status['state'] == DataState.REJECTED.value
    assert status['review_status'] == ReviewStatus.REJECTED.value
    assert status['reviewer_id'] == 'reviewer-1'
    assert status['reviewed_at'] is not None
    assert status['rejection_reason'] == 'Quality issues'


def test_get_review_status_not_found(review_service):
    """Test getting status fails when review not found"""
    with pytest.raises(ValueError, match="not found"):
        review_service.get_review_status(str(uuid4()))


# ============================================================================
# Test: Audit Logging Integration
# ============================================================================

def test_audit_logging_on_submit(review_service, temp_data, db_session):
    """Test that audit logs are created on review submission"""
    from src.models.data_lifecycle import AuditLogModel
    
    # Submit for review
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    
    # Check audit logs
    logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.resource_id == str(temp_data.id),
        AuditLogModel.action == Action.REVIEW
    ).all()
    
    # Should have logs for: submit_for_review and state transition
    assert len(logs) >= 1
    submit_log = next((log for log in logs if log.details.get('action') == 'submit_for_review'), None)
    assert submit_log is not None
    assert submit_log.user_id == 'user-1'
    assert submit_log.operation_type == OperationType.CREATE


def test_audit_logging_on_approve(review_service, temp_data, db_session):
    """Test that audit logs are created on approval"""
    from src.models.data_lifecycle import AuditLogModel
    
    # Submit and approve
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    review_service.approve_data(
        review_id=str(temp_data.id),
        reviewer_id='reviewer-1',
        comments='Good'
    )
    
    # Check audit logs
    logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.resource_id == str(temp_data.id),
        AuditLogModel.action == Action.REVIEW
    ).all()
    
    # Should have logs for: submit, approve, and state transitions
    approve_log = next((log for log in logs if log.details.get('action') == 'approve_data'), None)
    assert approve_log is not None
    assert approve_log.user_id == 'reviewer-1'
    assert approve_log.details['comments'] == 'Good'


def test_audit_logging_on_reject(review_service, temp_data, db_session):
    """Test that audit logs are created on rejection"""
    from src.models.data_lifecycle import AuditLogModel
    
    # Submit and reject
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    review_service.reject_data(
        review_id=str(temp_data.id),
        reviewer_id='reviewer-1',
        reason='Quality issues'
    )
    
    # Check audit logs
    logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.resource_id == str(temp_data.id),
        AuditLogModel.action == Action.REVIEW
    ).all()
    
    # Should have logs for: submit, reject, and state transitions
    reject_log = next((log for log in logs if log.details.get('action') == 'reject_data'), None)
    assert reject_log is not None
    assert reject_log.user_id == 'reviewer-1'
    assert reject_log.details['reason'] == 'Quality issues'


# ============================================================================
# Test: State Transition Integration
# ============================================================================

def test_state_transitions_on_workflow(review_service, temp_data, db_session):
    """Test that state transitions occur correctly throughout workflow"""
    # Initial state
    assert temp_data.state == DataState.TEMP_STORED
    
    # Submit for review
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    db_session.refresh(temp_data)
    assert temp_data.state == DataState.UNDER_REVIEW
    
    # Approve
    review_service.approve_data(
        review_id=str(temp_data.id),
        reviewer_id='reviewer-1'
    )
    db_session.refresh(temp_data)
    assert temp_data.state == DataState.IN_SAMPLE_LIBRARY


def test_state_history_recorded(review_service, temp_data, db_session):
    """Test that state history is recorded in audit logs"""
    from src.models.data_lifecycle import AuditLogModel
    
    # Submit and approve
    review_service.submit_for_review(
        data_id=str(temp_data.id),
        submitted_by='user-1',
        reviewer_id='reviewer-1'
    )
    review_service.approve_data(
        review_id=str(temp_data.id),
        reviewer_id='reviewer-1'
    )
    
    # Get state history from audit logs
    state_logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.resource_id == str(temp_data.id),
        AuditLogModel.operation_type == OperationType.STATE_CHANGE
    ).order_by(AuditLogModel.timestamp.asc()).all()
    
    # Should have state transitions: TEMP_STORED -> UNDER_REVIEW -> APPROVED -> IN_SAMPLE_LIBRARY
    assert len(state_logs) >= 3
    
    # Verify state progression
    states = [log.details.get('new_state') for log in state_logs]
    assert DataState.UNDER_REVIEW.value in states
    assert DataState.APPROVED.value in states
    assert DataState.IN_SAMPLE_LIBRARY.value in states
