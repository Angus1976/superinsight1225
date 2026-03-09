"""
Property-Based Tests for Enhancement Failure Safety

Tests Property 13: Enhancement Failure Safety

**Validates: Requirements 6.4**

When an enhancement fails, the original data must be preserved unchanged.
"""

import copy
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import patch
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

# Strategy for generating arbitrary content dictionaries
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

# Strategy for enhancement types
enhancement_type_strategy = st.sampled_from([
    EnhancementType.DATA_AUGMENTATION,
    EnhancementType.QUALITY_IMPROVEMENT,
    EnhancementType.NOISE_REDUCTION,
    EnhancementType.FEATURE_EXTRACTION,
    EnhancementType.NORMALIZATION,
])


# ============================================================================
# Property 13: Enhancement Failure Safety
# **Validates: Requirements 6.4**
# ============================================================================

@pytest.mark.property
class TestEnhancementFailureSafety:
    """
    Property 13: Enhancement Failure Safety

    For any enhancement job that fails, the original data must remain
    unchanged and accessible, the job status must be FAILED, and no
    enhanced data records should be persisted in the database.
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
    def test_original_data_preserved_on_failure(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: When enhancement fails, original content is preserved
        unchanged and accessible via get_original_content.

        **Validates: Requirements 6.4**
        """
        service = EnhancementService(db_session)
        content_snapshot = copy.deepcopy(content)

        config = EnhancementConfig(
            data_id=str(uuid4()),
            enhancement_type=enhancement_type,
        )
        job = service.create_enhancement_job(config, created_by=str(uuid4()))

        # Monkey-patch the enhancement algorithm to raise an exception
        with patch.object(
            service,
            "_run_enhancement",
            side_effect=RuntimeError("Simulated enhancement failure"),
        ):
            with pytest.raises(RuntimeError, match="Simulated enhancement"):
                service.apply_enhancement(job.id, content)

        # Original content must be preserved and match input exactly
        original = service.get_original_content(job.id)
        assert original == content_snapshot, (
            f"Original content was modified after failure. "
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
    def test_job_status_is_failed(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: When enhancement fails, job status must be FAILED.

        **Validates: Requirements 6.4**
        """
        service = EnhancementService(db_session)

        config = EnhancementConfig(
            data_id=str(uuid4()),
            enhancement_type=enhancement_type,
        )
        job = service.create_enhancement_job(config, created_by=str(uuid4()))

        with patch.object(
            service,
            "_run_enhancement",
            side_effect=RuntimeError("Simulated failure"),
        ):
            with pytest.raises(RuntimeError):
                service.apply_enhancement(job.id, content)

        status = service.get_job_status(job.id)
        assert status == JobStatus.FAILED, (
            f"Job status should be FAILED after failure, got {status.value}"
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
    def test_no_enhanced_data_persisted_on_failure(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: When enhancement fails, no enhanced data records
        should be persisted in the database.

        **Validates: Requirements 6.4**
        """
        service = EnhancementService(db_session)

        config = EnhancementConfig(
            data_id=str(uuid4()),
            enhancement_type=enhancement_type,
        )
        job = service.create_enhancement_job(config, created_by=str(uuid4()))

        count_before = db_session.query(EnhancedDataModel).count()

        with patch.object(
            service,
            "_run_enhancement",
            side_effect=RuntimeError("Simulated failure"),
        ):
            with pytest.raises(RuntimeError):
                service.apply_enhancement(job.id, content)

        count_after = db_session.query(EnhancedDataModel).count()
        assert count_after == count_before, (
            f"Enhanced data records changed after failure: "
            f"before={count_before}, after={count_after}"
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
    def test_original_content_matches_input_exactly(
        self,
        db_session: Session,
        content: dict,
        enhancement_type: EnhancementType,
    ):
        """
        Property: The original content stored before enhancement must
        exactly match the input content, even after failure.

        **Validates: Requirements 6.4**
        """
        service = EnhancementService(db_session)
        # Deep copy to ensure we have an independent reference
        expected = copy.deepcopy(content)

        config = EnhancementConfig(
            data_id=str(uuid4()),
            enhancement_type=enhancement_type,
        )
        job = service.create_enhancement_job(config, created_by=str(uuid4()))

        with patch.object(
            service,
            "_run_enhancement",
            side_effect=ValueError("Enhancement algorithm error"),
        ):
            with pytest.raises(ValueError):
                service.apply_enhancement(job.id, content)

        original = service.get_original_content(job.id)

        # Verify key-by-key equality
        assert set(original.keys()) == set(expected.keys()), (
            f"Keys differ: original={set(original.keys())}, "
            f"expected={set(expected.keys())}"
        )
        for key in expected:
            assert original[key] == expected[key], (
                f"Value mismatch for key '{key}': "
                f"original={original[key]}, expected={expected[key]}"
            )
