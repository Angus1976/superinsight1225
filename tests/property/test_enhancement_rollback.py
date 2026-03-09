"""
Property-Based Tests for Enhancement Rollback

Tests Property 14: Enhancement Rollback

**Validates: Requirements 6.5**

After rollback, enhanced data must be removed and original data must be
restorable.
"""

import copy
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from uuid import uuid4, UUID
from sqlalchemy import create_engine, String
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from src.models.data_lifecycle import (
    EnhancedDataModel,
    VersionModel,
    AuditLogModel,
    EnhancementType,
    JobStatus,
)
from src.services.enhancement_service import (
    EnhancementService,
    EnhancementConfig,
)


# ============================================================================
# SQLite UUID Compatibility
# ============================================================================

class SQLiteUUID(TypeDecorator):
    """UUID type that works with SQLite by storing as string."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return UUID(value) if not isinstance(value, UUID) else value
        return value


PATCHED_MODELS = [EnhancedDataModel, VersionModel, AuditLogModel]


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Create an in-memory SQLite database with UUID patching."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Patch UUID columns for SQLite
    for model in PATCHED_MODELS:
        for col in model.__table__.columns:
            if isinstance(col.type, PGUUID):
                col.type = SQLiteUUID()

    for model in PATCHED_MODELS:
        model.__table__.create(bind=engine, checkfirst=True)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    engine.dispose()

    # Restore original UUID types
    for model in PATCHED_MODELS:
        for col in model.__table__.columns:
            if isinstance(col.type, SQLiteUUID):
                col.type = PGUUID(as_uuid=True)


# ============================================================================
# Test Strategies
# ============================================================================

content_strategy = st.dictionaries(
    keys=st.sampled_from([
        "title", "text", "description", "category", "tags",
        "score", "metadata", "items", "notes", "status",
    ]),
    values=st.one_of(
        st.text(min_size=1, max_size=80),
        st.integers(min_value=-1000, max_value=1000),
        st.floats(
            min_value=-100.0, max_value=100.0,
            allow_nan=False, allow_infinity=False,
        ),
        st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5),
        st.booleans(),
    ),
    min_size=1,
    max_size=8,
)

enhancement_type_strategy = st.sampled_from([
    EnhancementType.DATA_AUGMENTATION,
    EnhancementType.QUALITY_IMPROVEMENT,
    EnhancementType.NOISE_REDUCTION,
    EnhancementType.FEATURE_EXTRACTION,
    EnhancementType.NORMALIZATION,
])


# ============================================================================
# Helpers
# ============================================================================

def _apply_successful_enhancement(
    service: EnhancementService,
    content: dict,
    enhancement_type: EnhancementType,
) -> str:
    """Create and apply a successful enhancement, returning the job ID."""
    config = EnhancementConfig(
        data_id=str(uuid4()),
        enhancement_type=enhancement_type,
    )
    job = service.create_enhancement_job(config, created_by=str(uuid4()))
    service.apply_enhancement(job.id, content)
    return job.id


# ============================================================================
# Property 14: Enhancement Rollback
# **Validates: Requirements 6.5**
# ============================================================================

@pytest.mark.property
class TestEnhancementRollback:
    """
    Property 14: Enhancement Rollback

    For any successful enhancement that is rolled back:
    1. The enhanced data record must be removed from the database
    2. The job status must be CANCELLED after rollback
    3. The original content must still be accessible and match the original
       input exactly
    4. No orphaned enhanced data records should remain
    5. Rollback of a non-completed job must raise an error
    """

    @given(
        content=content_strategy,
        enhancement_type=enhancement_type_strategy,
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_enhanced_data_removed_after_rollback(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: After rollback, the enhanced data record must be removed
        from the database.

        **Validates: Requirements 6.5**
        """
        service = EnhancementService(db_session)
        job_id = _apply_successful_enhancement(
            service, content, enhancement_type
        )

        # Verify enhanced data exists before rollback
        count_before = db_session.query(EnhancedDataModel).count()
        assert count_before >= 1, "Enhanced data should exist before rollback"

        service.rollback_enhancement(job_id)

        # The enhanced data record for this job must be gone
        job = service._jobs[job_id]
        remaining = db_session.query(EnhancedDataModel).filter(
            EnhancedDataModel.enhancement_job_id == UUID(job_id)
        ).count()
        assert remaining == 0, (
            f"Enhanced data record should be removed after rollback, "
            f"found {remaining}"
        )

    @given(
        content=content_strategy,
        enhancement_type=enhancement_type_strategy,
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_job_status_cancelled_after_rollback(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: After rollback, the job status must be CANCELLED.

        **Validates: Requirements 6.5**
        """
        service = EnhancementService(db_session)
        job_id = _apply_successful_enhancement(
            service, content, enhancement_type
        )

        # Confirm job is COMPLETED before rollback
        assert service.get_job_status(job_id) == JobStatus.COMPLETED

        service.rollback_enhancement(job_id)

        status = service.get_job_status(job_id)
        assert status == JobStatus.CANCELLED, (
            f"Job status should be CANCELLED after rollback, "
            f"got {status.value}"
        )

    @given(
        content=content_strategy,
        enhancement_type=enhancement_type_strategy,
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_original_content_accessible_after_rollback(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: After rollback, the original content must still be
        accessible and match the original input exactly.

        **Validates: Requirements 6.5**
        """
        service = EnhancementService(db_session)
        content_snapshot = copy.deepcopy(content)

        job_id = _apply_successful_enhancement(
            service, content, enhancement_type
        )

        service.rollback_enhancement(job_id)

        original = service.get_original_content(job_id)
        assert original == content_snapshot, (
            f"Original content should match input after rollback. "
            f"Expected {content_snapshot}, got {original}"
        )

    @given(
        content=content_strategy,
        enhancement_type=enhancement_type_strategy,
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_no_orphaned_enhanced_data_after_rollback(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: After rollback, no orphaned enhanced data records
        should remain for the rolled-back job.

        **Validates: Requirements 6.5**
        """
        service = EnhancementService(db_session)

        count_before = db_session.query(EnhancedDataModel).count()

        job_id = _apply_successful_enhancement(
            service, content, enhancement_type
        )

        # One new record should exist
        count_after_apply = db_session.query(EnhancedDataModel).count()
        assert count_after_apply == count_before + 1

        service.rollback_enhancement(job_id)

        count_after_rollback = db_session.query(EnhancedDataModel).count()
        assert count_after_rollback == count_before, (
            f"Enhanced data count should return to pre-enhancement level. "
            f"Before={count_before}, after rollback={count_after_rollback}"
        )

    @given(
        content=content_strategy,
        enhancement_type=enhancement_type_strategy,
        bad_status=st.sampled_from([
            JobStatus.QUEUED,
            JobStatus.RUNNING,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        ]),
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_rollback_non_completed_job_raises_error(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
        bad_status: JobStatus,
    ):
        """
        Property: Rollback of a non-completed job must raise an error.

        **Validates: Requirements 6.5**
        """
        service = EnhancementService(db_session)

        config = EnhancementConfig(
            data_id=str(uuid4()),
            enhancement_type=enhancement_type,
        )
        job = service.create_enhancement_job(config, created_by=str(uuid4()))

        # Force the job into the non-completed status
        job.status = bad_status

        with pytest.raises(ValueError, match="Cannot rollback"):
            service.rollback_enhancement(job.id)
