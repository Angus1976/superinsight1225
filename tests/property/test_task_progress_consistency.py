"""
Property-Based Tests for Task Progress Consistency

Tests Property 11: Task Progress Consistency

**Validates: Requirements 5.4**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from sqlalchemy import create_engine
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
from tests.property.sqlite_uuid_compat import (
    snapshot_uuid_columns,
    patch_models_to_sqlite_uuid,
    restore_uuid_columns,
)

PATCHED_MODELS = [SampleModel, AnnotationTaskModel, AuditLogModel]
_UUID_COLUMN_SNAPSHOT = snapshot_uuid_columns(PATCHED_MODELS)


# ============================================================================
# Custom Fixture for Data Lifecycle Tables Only
# ============================================================================

@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Provide a database session with only data lifecycle tables.
    Patches UUID columns for SQLite compatibility.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    restore = patch_models_to_sqlite_uuid(PATCHED_MODELS, _UUID_COLUMN_SNAPSHOT)
    try:
        SampleModel.__table__.create(bind=engine, checkfirst=True)
        AnnotationTaskModel.__table__.create(bind=engine, checkfirst=True)
        AuditLogModel.__table__.create(bind=engine, checkfirst=True)

        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()
    finally:
        restore_uuid_columns(restore)


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating number of samples in a task
sample_count_strategy = st.integers(min_value=1, max_value=50)

# Strategy for generating number of annotations to submit
annotation_count_strategy = st.integers(min_value=0, max_value=50)

# Strategy for annotation type
annotation_type_strategy = st.sampled_from([
    AnnotationType.CLASSIFICATION,
    AnnotationType.ENTITY_RECOGNITION,
    AnnotationType.RELATION_EXTRACTION,
    AnnotationType.SENTIMENT_ANALYSIS
])


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
    annotation_type: AnnotationType
) -> tuple[dict, list[SampleModel]]:
    """Create an annotation task with samples"""
    samples = create_samples(db, sample_count)
    sample_ids = [str(s.id) for s in samples]
    
    config = TaskConfig(
        name=f"Test Task {uuid4()}",
        description="Test task for property testing",
        sample_ids=sample_ids,
        annotation_type=annotation_type,
        instructions="Test instructions",
        deadline=datetime.utcnow() + timedelta(days=7)
    )
    
    task = service.create_task(config, created_by=str(uuid4()))
    return task, samples


# ============================================================================
# Property 11: Task Progress Consistency
# **Validates: Requirements 5.4**
# ============================================================================

@pytest.mark.property
class TestTaskProgressConsistency:
    """
    Property 11: Task Progress Consistency
    
    For any annotation task, the sum of completed and in-progress annotations
    must not exceed the total number of assigned samples, and progress percentage
    must be calculated correctly.
    """
    
    @given(sample_count=sample_count_strategy)
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_progress_total_equals_sample_count(
        self,
        db_session: Session,
        sample_count: int
    ):
        """
        Property: Task progress total equals the number of assigned samples.
        
        For any task created with N samples, progress.total must equal N.
        """
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(
            db_session,
            service,
            sample_count,
            AnnotationType.CLASSIFICATION
        )
        
        # Get task progress
        progress = service.get_task_progress(task['id'])
        
        # Assert: Total equals sample count
        assert progress.total == sample_count, (
            f"Task progress total {progress.total} should equal "
            f"sample count {sample_count}"
        )
    
    @given(
        sample_count=sample_count_strategy,
        annotation_count=annotation_count_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_completed_plus_in_progress_not_exceed_total(
        self,
        db_session: Session,
        sample_count: int,
        annotation_count: int
    ):
        """
        Property: completed + in_progress <= total.
        
        For any task, the sum of completed and in_progress annotations
        must never exceed the total number of assigned samples.
        """
        # Ensure annotation count doesn't exceed sample count
        annotation_count = min(annotation_count, sample_count)
        
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(
            db_session,
            service,
            sample_count,
            AnnotationType.CLASSIFICATION
        )
        
        # Assign an annotator
        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))
        
        # Submit annotations for some samples
        for i in range(annotation_count):
            annotation = Annotation(
                task_id=task['id'],
                sample_id=str(samples[i].id),
                annotator_id=annotator_id,
                labels=[{'label': 'test', 'value': i}],
                confidence=0.9
            )
            service.submit_annotation(annotation)
        
        # Get task progress
        progress = service.get_task_progress(task['id'])
        
        # Assert: completed + in_progress <= total
        sum_progress = progress.completed + progress.in_progress
        assert sum_progress <= progress.total, (
            f"Sum of completed ({progress.completed}) and in_progress ({progress.in_progress}) "
            f"= {sum_progress} exceeds total {progress.total}"
        )
    
    @given(
        sample_count=sample_count_strategy,
        annotation_count=annotation_count_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_percentage_calculation_correct(
        self,
        db_session: Session,
        sample_count: int,
        annotation_count: int
    ):
        """
        Property: Progress percentage is calculated correctly.
        
        For any task, percentage should equal (completed / total) * 100,
        rounded to 2 decimal places.
        """
        # Ensure annotation count doesn't exceed sample count
        annotation_count = min(annotation_count, sample_count)
        
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(
            db_session,
            service,
            sample_count,
            AnnotationType.CLASSIFICATION
        )
        
        # Assign an annotator
        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))
        
        # Submit annotations for some samples
        for i in range(annotation_count):
            annotation = Annotation(
                task_id=task['id'],
                sample_id=str(samples[i].id),
                annotator_id=annotator_id,
                labels=[{'label': 'test', 'value': i}],
                confidence=0.9
            )
            service.submit_annotation(annotation)
        
        # Get task progress
        progress = service.get_task_progress(task['id'])
        
        # Calculate expected percentage
        expected_percentage = round(
            (progress.completed / progress.total * 100) if progress.total > 0 else 0.0,
            2
        )
        
        # Assert: Percentage is calculated correctly
        assert progress.percentage == expected_percentage, (
            f"Progress percentage {progress.percentage} should equal "
            f"expected {expected_percentage} (completed={progress.completed}, total={progress.total})"
        )
    
    @given(sample_count=st.integers(min_value=1, max_value=20))
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_initial_progress_is_zero(
        self,
        db_session: Session,
        sample_count: int
    ):
        """
        Property: Newly created tasks have zero progress.
        
        For any newly created task, completed and in_progress should be 0,
        and percentage should be 0.0.
        """
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(
            db_session,
            service,
            sample_count,
            AnnotationType.CLASSIFICATION
        )
        
        # Get task progress
        progress = service.get_task_progress(task['id'])
        
        # Assert: Initial progress is zero
        assert progress.completed == 0, (
            f"New task should have completed=0, got {progress.completed}"
        )
        assert progress.in_progress == 0, (
            f"New task should have in_progress=0, got {progress.in_progress}"
        )
        assert progress.percentage == 0.0, (
            f"New task should have percentage=0.0, got {progress.percentage}"
        )
    
    @given(sample_count=st.integers(min_value=1, max_value=20))
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_full_completion_reaches_100_percent(
        self,
        db_session: Session,
        sample_count: int
    ):
        """
        Property: Completing all samples results in 100% progress.
        
        For any task where all samples are annotated, percentage should be 100.0
        and completed should equal total.
        """
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(
            db_session,
            service,
            sample_count,
            AnnotationType.CLASSIFICATION
        )
        
        # Assign an annotator
        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))
        
        # Submit annotations for ALL samples
        for sample in samples:
            annotation = Annotation(
                task_id=task['id'],
                sample_id=str(sample.id),
                annotator_id=annotator_id,
                labels=[{'label': 'test', 'value': 1}],
                confidence=0.9
            )
            service.submit_annotation(annotation)
        
        # Get task progress
        progress = service.get_task_progress(task['id'])
        
        # Assert: Full completion
        assert progress.completed == progress.total, (
            f"Completed {progress.completed} should equal total {progress.total}"
        )
        assert progress.percentage == 100.0, (
            f"Percentage should be 100.0, got {progress.percentage}"
        )
    
    @given(
        sample_count=st.integers(min_value=2, max_value=20),
        annotation_count=st.integers(min_value=1, max_value=20)
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_progress_increments_monotonically(
        self,
        db_session: Session,
        sample_count: int,
        annotation_count: int
    ):
        """
        Property: Progress increments monotonically with each annotation.
        
        For any task, submitting annotations should cause completed count
        to increase monotonically (never decrease).
        """
        # Ensure annotation count doesn't exceed sample count
        annotation_count = min(annotation_count, sample_count)
        assume(annotation_count >= 1)
        
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(
            db_session,
            service,
            sample_count,
            AnnotationType.CLASSIFICATION
        )
        
        # Assign an annotator
        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))
        
        previous_completed = 0
        
        # Submit annotations one by one and check monotonicity
        for i in range(annotation_count):
            annotation = Annotation(
                task_id=task['id'],
                sample_id=str(samples[i].id),
                annotator_id=annotator_id,
                labels=[{'label': 'test', 'value': i}],
                confidence=0.9
            )
            service.submit_annotation(annotation)
            
            # Get current progress
            progress = service.get_task_progress(task['id'])
            
            # Assert: Completed count increased
            assert progress.completed >= previous_completed, (
                f"Completed count decreased from {previous_completed} to {progress.completed}"
            )
            
            # Assert: Completed count increased by exactly 1
            assert progress.completed == previous_completed + 1, (
                f"Completed count should increase by 1, but went from "
                f"{previous_completed} to {progress.completed}"
            )
            
            previous_completed = progress.completed
    
    @given(
        sample_count=st.integers(min_value=2, max_value=20),
        annotation_count=st.integers(min_value=1, max_value=20)
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_percentage_monotonically_increases(
        self,
        db_session: Session,
        sample_count: int,
        annotation_count: int
    ):
        """
        Property: Progress percentage increases monotonically.
        
        For any task, submitting annotations should cause percentage
        to increase monotonically (never decrease).
        """
        # Ensure annotation count doesn't exceed sample count
        annotation_count = min(annotation_count, sample_count)
        assume(annotation_count >= 1)
        
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(
            db_session,
            service,
            sample_count,
            AnnotationType.CLASSIFICATION
        )
        
        # Assign an annotator
        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))
        
        previous_percentage = 0.0
        
        # Submit annotations one by one and check monotonicity
        for i in range(annotation_count):
            annotation = Annotation(
                task_id=task['id'],
                sample_id=str(samples[i].id),
                annotator_id=annotator_id,
                labels=[{'label': 'test', 'value': i}],
                confidence=0.9
            )
            service.submit_annotation(annotation)
            
            # Get current progress
            progress = service.get_task_progress(task['id'])
            
            # Assert: Percentage increased or stayed the same (due to rounding)
            assert progress.percentage >= previous_percentage, (
                f"Percentage decreased from {previous_percentage} to {progress.percentage}"
            )
            
            previous_percentage = progress.percentage
    
    @given(sample_count=st.integers(min_value=1, max_value=20))
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_resubmitting_same_annotation_does_not_increase_progress(
        self,
        db_session: Session,
        sample_count: int
    ):
        """
        Property: Resubmitting annotation for same sample doesn't increase progress.
        
        For any task, submitting multiple annotations for the same sample
        should update the annotation but not increase the completed count.
        """
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(
            db_session,
            service,
            sample_count,
            AnnotationType.CLASSIFICATION
        )
        
        # Assign an annotator
        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))
        
        # Submit first annotation
        sample_id = str(samples[0].id)
        annotation1 = Annotation(
            task_id=task['id'],
            sample_id=sample_id,
            annotator_id=annotator_id,
            labels=[{'label': 'test', 'value': 1}],
            confidence=0.8
        )
        service.submit_annotation(annotation1)
        
        # Get progress after first submission
        progress1 = service.get_task_progress(task['id'])
        
        # Submit second annotation for SAME sample
        annotation2 = Annotation(
            task_id=task['id'],
            sample_id=sample_id,
            annotator_id=annotator_id,
            labels=[{'label': 'test', 'value': 2}],
            confidence=0.9
        )
        service.submit_annotation(annotation2)
        
        # Get progress after second submission
        progress2 = service.get_task_progress(task['id'])
        
        # Assert: Completed count did not increase
        assert progress2.completed == progress1.completed, (
            f"Resubmitting annotation should not increase completed count, "
            f"but it went from {progress1.completed} to {progress2.completed}"
        )
        
        # Assert: Percentage did not increase
        assert progress2.percentage == progress1.percentage, (
            f"Resubmitting annotation should not increase percentage, "
            f"but it went from {progress1.percentage} to {progress2.percentage}"
        )
    
    @given(
        sample_count=st.integers(min_value=1, max_value=20),
        annotation_type=annotation_type_strategy
    )
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_progress_consistency_across_annotation_types(
        self,
        db_session: Session,
        sample_count: int,
        annotation_type: AnnotationType
    ):
        """
        Property: Progress consistency holds for all annotation types.
        
        For any annotation type, the progress consistency properties
        (completed + in_progress <= total, correct percentage) must hold.
        """
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(
            db_session,
            service,
            sample_count,
            annotation_type
        )
        
        # Assign an annotator
        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))
        
        # Submit annotations for half the samples
        annotation_count = sample_count // 2
        for i in range(annotation_count):
            annotation = Annotation(
                task_id=task['id'],
                sample_id=str(samples[i].id),
                annotator_id=annotator_id,
                labels=[{'label': 'test', 'value': i}],
                confidence=0.9
            )
            service.submit_annotation(annotation)
        
        # Get task progress
        progress = service.get_task_progress(task['id'])
        
        # Assert: completed + in_progress <= total
        sum_progress = progress.completed + progress.in_progress
        assert sum_progress <= progress.total, (
            f"For annotation type {annotation_type.value}, "
            f"sum of completed ({progress.completed}) and in_progress ({progress.in_progress}) "
            f"= {sum_progress} exceeds total {progress.total}"
        )
        
        # Assert: Percentage is correct
        expected_percentage = round(
            (progress.completed / progress.total * 100) if progress.total > 0 else 0.0,
            2
        )
        assert progress.percentage == expected_percentage, (
            f"For annotation type {annotation_type.value}, "
            f"percentage {progress.percentage} should equal {expected_percentage}"
        )
    
    @given(sample_count=st.integers(min_value=1, max_value=20))
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_progress_values_are_non_negative(
        self,
        db_session: Session,
        sample_count: int
    ):
        """
        Property: All progress values are non-negative.
        
        For any task, total, completed, in_progress, and percentage
        must all be >= 0.
        """
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(
            db_session,
            service,
            sample_count,
            AnnotationType.CLASSIFICATION
        )
        
        # Get task progress
        progress = service.get_task_progress(task['id'])
        
        # Assert: All values are non-negative
        assert progress.total >= 0, (
            f"Total {progress.total} should be non-negative"
        )
        assert progress.completed >= 0, (
            f"Completed {progress.completed} should be non-negative"
        )
        assert progress.in_progress >= 0, (
            f"In-progress {progress.in_progress} should be non-negative"
        )
        assert progress.percentage >= 0.0, (
            f"Percentage {progress.percentage} should be non-negative"
        )
    
    @given(sample_count=st.integers(min_value=1, max_value=20))
    @settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_percentage_never_exceeds_100(
        self,
        db_session: Session,
        sample_count: int
    ):
        """
        Property: Progress percentage never exceeds 100%.
        
        For any task, percentage must be <= 100.0.
        """
        service = AnnotationTaskService(db_session)
        task, samples = create_task_with_samples(
            db_session,
            service,
            sample_count,
            AnnotationType.CLASSIFICATION
        )
        
        # Assign an annotator
        annotator_id = str(uuid4())
        service.assign_annotator(task['id'], annotator_id, str(uuid4()))
        
        # Submit annotations for all samples
        for sample in samples:
            annotation = Annotation(
                task_id=task['id'],
                sample_id=str(sample.id),
                annotator_id=annotator_id,
                labels=[{'label': 'test', 'value': 1}],
                confidence=0.9
            )
            service.submit_annotation(annotation)
        
        # Get task progress
        progress = service.get_task_progress(task['id'])
        
        # Assert: Percentage does not exceed 100
        assert progress.percentage <= 100.0, (
            f"Percentage {progress.percentage} should not exceed 100.0"
        )
