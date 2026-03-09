"""
Property-Based Tests for Iterative Enhancement Traceability

Tests Property 30: Iterative Enhancement Traceability

**Validates: Requirements 21.2, 21.3, 21.4, 21.6**

For any enhanced data added back to the sample library, the new sample
must be linked to the original data, preserve version history, and
increment the iteration count.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID
from sqlalchemy import create_engine, String
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from src.models.data_lifecycle import (
    EnhancedDataModel,
    SampleModel,
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


PATCHED_MODELS = [EnhancedDataModel, SampleModel, VersionModel, AuditLogModel]


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Create an in-memory SQLite database with UUID patching."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

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

def _create_and_apply_enhancement(
    service: EnhancementService,
    content: dict,
    enhancement_type: EnhancementType,
    data_id: Optional[str] = None,
) -> str:
    """Create and apply a successful enhancement, returning the job ID."""
    config = EnhancementConfig(
        data_id=data_id or str(uuid4()),
        enhancement_type=enhancement_type,
    )
    user_id = str(uuid4())
    job = service.create_enhancement_job(config, created_by=user_id)
    service.apply_enhancement(job.id, content)
    return job.id


def _add_to_library(
    service: EnhancementService,
    job_id: str,
) -> dict:
    """Add enhanced data from a completed job to the sample library."""
    user_id = str(uuid4())
    return service.add_to_sample_library(job_id, user_id)


# ============================================================================
# Property 30: Iterative Enhancement Traceability
# **Validates: Requirements 21.2, 21.3, 21.4, 21.6**
# ============================================================================

@pytest.mark.property
class TestIterativeEnhancementTraceability:
    """
    Property 30: Iterative Enhancement Traceability

    For any enhanced data added back to the sample library:
    1. The new sample links back to the original data (original_data_id set)
    2. The iteration count is >= 1 and increments correctly
    3. The enhancement job ID is recorded in the result metadata
    4. Multiple iterations maintain the full chain of traceability
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
    def test_sample_links_to_original_data(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: Enhanced data added to sample library always contains
        a link to the original data via original_data_id in metadata.

        **Validates: Requirements 21.2**
        """
        service = EnhancementService(db_session)
        job_id = _create_and_apply_enhancement(
            service, content, enhancement_type
        )
        result = _add_to_library(service, job_id)

        # The metadata must contain original_data_id
        assert 'original_data_id' in result['metadata'], (
            "Sample metadata must contain 'original_data_id' for traceability"
        )
        # original_data_id must be a non-empty string
        original_id = result['metadata']['original_data_id']
        assert original_id and isinstance(original_id, str), (
            f"original_data_id must be a non-empty string, got: {original_id}"
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
    def test_iteration_count_at_least_one(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: The iteration count for any enhanced data added to the
        sample library is always >= 1.

        **Validates: Requirements 21.4**
        """
        service = EnhancementService(db_session)
        job_id = _create_and_apply_enhancement(
            service, content, enhancement_type
        )
        result = _add_to_library(service, job_id)

        iteration_count = result['metadata'].get('iteration_count')
        assert iteration_count is not None, (
            "Sample metadata must contain 'iteration_count'"
        )
        assert iteration_count >= 1, (
            f"Iteration count must be >= 1, got: {iteration_count}"
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
    def test_enhancement_job_id_recorded(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: The enhancement job ID is always recorded in the
        sample metadata when adding enhanced data to the library.

        **Validates: Requirements 21.6**
        """
        service = EnhancementService(db_session)
        job_id = _create_and_apply_enhancement(
            service, content, enhancement_type
        )
        result = _add_to_library(service, job_id)

        assert 'enhancement_job_id' in result['metadata'], (
            "Sample metadata must contain 'enhancement_job_id'"
        )
        recorded_job_id = result['metadata']['enhancement_job_id']
        assert recorded_job_id and isinstance(recorded_job_id, str), (
            f"enhancement_job_id must be a non-empty string, "
            f"got: {recorded_job_id}"
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
    def test_version_history_preserved(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: When enhanced data is added to the sample library,
        a version record is created to preserve version history.

        **Validates: Requirements 21.3**
        """
        service = EnhancementService(db_session)
        job_id = _create_and_apply_enhancement(
            service, content, enhancement_type
        )

        versions_before = db_session.query(VersionModel).count()

        result = _add_to_library(service, job_id)

        versions_after = db_session.query(VersionModel).count()
        assert versions_after > versions_before, (
            "A version record must be created when adding enhanced data "
            "to the sample library"
        )

        # Verify the version is linked to the new sample
        sample_id = result['id']
        version = db_session.query(VersionModel).filter(
            VersionModel.data_id == sample_id
        ).first()
        assert version is not None, (
            f"Version record must be linked to new sample {sample_id}"
        )

    @given(
        content=content_strategy,
        enhancement_type=enhancement_type_strategy,
    )
    @settings(
        max_examples=15,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_multiple_iterations_increment_count(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: Multiple enhancement iterations on the same original
        data produce increasing iteration counts, maintaining the full
        chain of traceability.

        **Validates: Requirements 21.4, 21.6**
        """
        service = EnhancementService(db_session)
        original_data_id = str(uuid4())

        # First iteration
        job_id_1 = _create_and_apply_enhancement(
            service, content, enhancement_type, data_id=original_data_id
        )
        result_1 = _add_to_library(service, job_id_1)
        count_1 = result_1['metadata']['iteration_count']

        # Second iteration on the same original data
        job_id_2 = _create_and_apply_enhancement(
            service, content, enhancement_type, data_id=original_data_id
        )
        result_2 = _add_to_library(service, job_id_2)
        count_2 = result_2['metadata']['iteration_count']

        assert count_2 > count_1, (
            f"Iteration count must increase across iterations. "
            f"First: {count_1}, Second: {count_2}"
        )

        # Both must link to the same original data
        assert (
            result_1['metadata']['original_data_id']
            == result_2['metadata']['original_data_id']
        ), (
            "Both iterations must link to the same original data ID"
        )
