"""
Property-Based Tests for Task Completion Validation

Tests Property 12: Task Completion Validation

For any annotation task, marking it as complete should only succeed
if all assigned samples have been annotated.

**Validates: Requirements 5.6**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from sqlalchemy import create_engine, event, String, TypeDecorator
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.data_lifecycle import (
    SampleModel,
    AnnotationTaskModel,
    AuditLogModel,
    TaskStatus,
    AnnotationType
)
from src.services.annotation_task_service import (
    AnnotationTaskService,
    TaskConfig,
    Annotation
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
            if isinstance(value, UUID):
                return str(value)
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return UUID(value) if not isinstance(value, UUID) else value
        return value


def patch_uuid_columns_for_sqlite(engine):
    """
    Patch PGUUID columns to use string storage for SQLite compatibility.
    This is applied at the column level when creating tables.
    """
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


# ============================================================================
# Custom Fixture for Data Lifecycle Tables Only
# ============================================================================

@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Provide a database session with only data lifecycle tables.
    Patches UUID columns for SQLite compatibility.
    """
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Patch UUID columns in the models to use String for SQLite
    for model in [SampleModel, AnnotationTaskModel, AuditLogModel]:
        for col in model.__table__.columns:
            if isinstance(col.type, PGUUID):
                col.type = SQLiteUUID()

    SampleModel.__table__.create(bind=engine, checkfirst=True)
    AnnotationTaskModel.__table__.create(bind=engine, checkfirst=True)
    AuditLogModel.__table__.create(bind=engine, checkfirst=True)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    engine.dispose()

    # Restore original UUID types for other tests
    from sqlalchemy.dialects.postgresql import UUID as PGUUID_Restore
    for model in [SampleModel, AnnotationTaskModel, AuditLogModel]:
        for col in model.__table__.columns:
            if isinstance(col.type, SQLiteUUID):
                col.type = PGUUID_Restore(as_uuid=True)


# ============================================================================
# Helper Functions
# ============================================================================

def create_samples(db: Session, count: int) -> list[SampleModel]:
    """Create sample models for testing"""
    samples = []
    for i in range(count):
        sample = SampleModel(
            id=uuid4(),
            data_id=str(uuid4()),
            content={'test': f'sample_{i}', 'value': i},
            category='test',
            quality_overall=0.8,
            quality_completeness=0.8,
            quality_accuracy=0.8,
            quality_consistency=0.8,
            version=1,
            tags=['test'],
            usage_count=0,
            last_used_at=None,
            metadata_={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(sample)
        samples.append(sample)

    db.commit()
    return samples


def create_task_with_samples(
    db: Session,
    service: AnnotationTaskService,
    sample_count: int,
) -> tuple[dict, list[SampleModel]]:
    """Create an annotation task with samples and return task dict + samples"""
    samples = create_samples(db, sample_count)
    sample_ids = [str(s.id) for s in samples]

    config = TaskConfig(
        name=f"Test Task {uuid4()}",
        description="Test task for property testing",
        sample_ids=sample_ids,
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions="Test instructions",
        deadline=datetime.utcnow() + timedelta(days=7),
        assigned_to=[]
    )

    task = service.create_task(config, created_by=str(uuid4()))
    return task, samples


def annotate_samples(
    service: AnnotationTaskService,
    task_id: str,
    samples: list[SampleModel],
    count: int,
    annotator_id: str
) -> None:
    """Submit annotations for the first `count` samples"""
    for i in range(count):
        annotation = Annotation(
            task_id=task_id,
            sample_id=str(samples[i].id),
            annotator_id=annotator_id,
            labels=[{'label': 'test', 'value': i}],
            confidence=0.9
        )
        service.submit_annotation(annotation)


# ============================================================================
# Property 12: Task Completion Validation
# **Validates: Requirements 5.6**
# ============================================================================

@pytest.mark.property
class TestTaskCompletionValidation:
    """
    Property 12: Task Completion Validation

    For any annotation task, marking it as complete should only succeed
    if all assigned samples have been annotated.

    **Validates: Requirements 5.6**
    """

    @given(
        sample_count=st.integers(min_value=2, max_value=30),
        annotations_to_submit=st.integers(min_value=0, max_value=30)
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_incomplete_task_cannot_be_completed(
        self,
        db_session: Session,
        sample_count: int,
        annotations_to_submit: int
    ):
        """
        Property: A task with fewer annotations than samples cannot be completed.

        For any task with N samples where K < N annotations have been submitted,
        calling complete_task must raise a ValueError.
        """
        annotations_to_submit = min(annotations_to_submit, sample_count - 1)
        assume(annotations_to_submit < sample_count)

        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(db_session, service, sample_count)

        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))

        annotate_samples(service, task['id'], samples, annotations_to_submit, annotator_id)

        with pytest.raises(ValueError, match="Cannot complete task"):
            service.complete_task(task['id'], completed_by=str(uuid4()))

    @given(sample_count=st.integers(min_value=1, max_value=30))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_fully_annotated_task_can_be_completed(
        self,
        db_session: Session,
        sample_count: int
    ):
        """
        Property: A task with all samples annotated can be completed successfully.

        For any task with N samples where all N annotations have been submitted,
        calling complete_task must succeed and set status to COMPLETED.
        """
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(db_session, service, sample_count)

        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))

        annotate_samples(service, task['id'], samples, sample_count, annotator_id)

        service.complete_task(task['id'], completed_by=str(uuid4()))

        completed_task = service.get_task(task['id'])
        assert completed_task['status'] == TaskStatus.COMPLETED.value
        assert completed_task['completed_at'] is not None

    @given(sample_count=st.integers(min_value=1, max_value=20))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_task_with_zero_annotations_cannot_be_completed(
        self,
        db_session: Session,
        sample_count: int
    ):
        """
        Property: A task with no annotations submitted cannot be completed.

        For any task with N > 0 samples and 0 annotations,
        calling complete_task must raise a ValueError.
        """
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(db_session, service, sample_count)

        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))

        with pytest.raises(ValueError, match="Cannot complete task"):
            service.complete_task(task['id'], completed_by=str(uuid4()))

    @given(sample_count=st.integers(min_value=1, max_value=20))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_completed_task_has_progress_equal_to_total(
        self,
        db_session: Session,
        sample_count: int
    ):
        """
        Property: After successful completion, progress_completed equals progress_total.

        For any task that is successfully completed, the progress must show
        completed == total.
        """
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(db_session, service, sample_count)

        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))

        annotate_samples(service, task['id'], samples, sample_count, annotator_id)

        service.complete_task(task['id'], completed_by=str(uuid4()))

        progress = service.get_task_progress(task['id'])
        assert progress.completed == progress.total, (
            f"Completed task should have completed ({progress.completed}) "
            f"== total ({progress.total})"
        )
        assert progress.percentage == 100.0
