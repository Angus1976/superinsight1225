"""
Unit tests for Annotation Task Service

Tests task creation, assignment, annotation submission, progress tracking,
and task completion with validation.
"""

import pytest
import json
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.connection import Base
from src.models.data_lifecycle import (
    AnnotationTaskModel,
    SampleModel,
    TaskStatus,
    AnnotationType,
    DataState,
    ResourceType,
    OperationType,
    OperationResult,
    Action
)
from src.services.annotation_task_service import (
    AnnotationTaskService,
    TaskConfig,
    Annotation,
    TaskProgress
)


# Test database setup
@pytest.fixture(scope='function')
def db_session():
    """Create an in-memory SQLite database for testing"""
    from sqlalchemy import Table, Column, String, Float, Integer, DateTime, JSON, Text, Enum as SQLEnum
    from datetime import datetime
    
    engine = create_engine('sqlite:///:memory:')
    
    metadata = Base.metadata
    
    # Create only the tables we need for annotation task testing
    samples_table = Table(
        'samples',
        metadata,
        Column('id', String(36), primary_key=True),
        Column('data_id', String(255), nullable=False),
        Column('content', JSON, nullable=False),
        Column('category', String(100), nullable=False),
        Column('quality_overall', Float, nullable=False),
        Column('quality_completeness', Float, nullable=False),
        Column('quality_accuracy', Float, nullable=False),
        Column('quality_consistency', Float, nullable=False),
        Column('version', Integer, nullable=False, default=1),
        Column('tags', JSON, nullable=False, default=list),
        Column('usage_count', Integer, nullable=False, default=0),
        Column('last_used_at', DateTime, nullable=True),
        Column('metadata', JSON, nullable=False, default=dict),
        Column('created_at', DateTime, nullable=False, default=datetime.utcnow),
        Column('updated_at', DateTime, nullable=False, default=datetime.utcnow),
        extend_existing=True
    )
    
    annotation_tasks_table = Table(
        'annotation_tasks',
        metadata,
        Column('id', String(36), primary_key=True),
        Column('name', String(255), nullable=False),
        Column('description', Text, nullable=True),
        Column('sample_ids', JSON, nullable=False),
        Column('annotation_type', String(50), nullable=False),
        Column('instructions', Text, nullable=False),
        Column('status', String(50), nullable=False, default='created'),
        Column('created_by', String(255), nullable=False),
        Column('created_at', DateTime, nullable=False, default=datetime.utcnow),
        Column('assigned_to', JSON, nullable=False, default=list),
        Column('deadline', DateTime, nullable=True),
        Column('completed_at', DateTime, nullable=True),
        Column('progress_total', Integer, nullable=False, default=0),
        Column('progress_completed', Integer, nullable=False, default=0),
        Column('progress_in_progress', Integer, nullable=False, default=0),
        Column('annotations', JSON, nullable=False, default=list),
        Column('metadata', JSON, nullable=False, default=dict),
        extend_existing=True
    )
    
    audit_logs_table = Table(
        'data_lifecycle_audit_logs',
        metadata,
        Column('id', String(36), primary_key=True),
        Column('operation_type', String(50), nullable=False),
        Column('user_id', String(255), nullable=False),
        Column('resource_type', String(50), nullable=False),
        Column('resource_id', String(255), nullable=False),
        Column('action', String(50), nullable=False),
        Column('result', String(50), nullable=False),
        Column('duration', Integer, nullable=False),
        Column('error', Text, nullable=True),
        Column('details', JSON, nullable=False, default=dict),
        Column('ip_address', String(45), nullable=True),
        Column('user_agent', String(500), nullable=True),
        Column('timestamp', DateTime, nullable=False, default=datetime.utcnow),
        extend_existing=True
    )
    
    # Create tables
    samples_table.create(engine, checkfirst=True)
    annotation_tasks_table.create(engine, checkfirst=True)
    audit_logs_table.create(engine, checkfirst=True)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def task_service(db_session):
    """Create an AnnotationTaskService instance"""
    return AnnotationTaskService(db_session)


@pytest.fixture
def samples(db_session):
    """Create sample data for testing"""
    import json
    sample_list = []
    for i in range(3):
        sample_id = str(uuid4())
        # Insert directly using SQL to avoid UUID issues with SQLite
        db_session.execute(
            """
            INSERT INTO samples (id, data_id, content, category, quality_overall, 
                               quality_completeness, quality_accuracy, quality_consistency,
                               version, tags, usage_count, last_used_at, metadata, 
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sample_id,
                f'data-{i}',
                json.dumps({'title': f'Sample {i}', 'text': f'Content {i}'}),
                'test',
                0.8, 0.8, 0.8, 0.8,
                1,
                json.dumps(['test']),
                0,
                None,
                json.dumps({'source': 'test'}),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            )
        )
        # Create a simple object to hold the ID
        class SampleObj:
            def __init__(self, sid):
                self.id = sid
        sample_list.append(SampleObj(sample_id))
    
    db_session.commit()
    return sample_list


# ============================================================================
# Test: Create Task
# ============================================================================

def test_create_task_success(task_service, samples, db_session):
    """Test successful task creation"""
    # Create task config
    config = TaskConfig(
        name='Test Annotation Task',
        description='Test task description',
        sample_ids=[str(s.id) for s in samples],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Please classify the samples',
        deadline=datetime.utcnow() + timedelta(days=7),
        assigned_to=['annotator-1', 'annotator-2']
    )
    
    # Create task
    result = task_service.create_task(config, created_by='admin-1')
    
    # Verify result
    assert result['name'] == 'Test Annotation Task'
    assert result['description'] == 'Test task description'
    assert len(result['sample_ids']) == 3
    assert result['annotation_type'] == AnnotationType.CLASSIFICATION.value
    assert result['instructions'] == 'Please classify the samples'
    assert result['status'] == TaskStatus.CREATED.value
    assert result['created_by'] == 'admin-1'
    assert len(result['assigned_to']) == 2
    assert result['progress']['total'] == 3
    assert result['progress']['completed'] == 0
    
    # Verify database state
    task = db_session.query(AnnotationTaskModel).filter(
        AnnotationTaskModel.id == result['id']
    ).first()
    assert task is not None
    assert task.status == TaskStatus.CREATED
    
    # Verify sample usage tracking
    for sample in samples:
        db_session.refresh(sample)
        assert sample.usage_count == 1
        assert sample.last_used_at is not None


def test_create_task_minimal_config(task_service, samples, db_session):
    """Test task creation with minimal configuration"""
    config = TaskConfig(
        name='Minimal Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.ENTITY_RECOGNITION,
        instructions='Annotate entities',
        deadline=None,
        assigned_to=None
    )
    
    result = task_service.create_task(config, created_by='admin-1')
    
    assert result['name'] == 'Minimal Task'
    assert result['description'] is None
    assert result['deadline'] is None
    assert result['assigned_to'] == []
    assert result['progress']['total'] == 1


def test_create_task_invalid_samples(task_service, db_session):
    """Test task creation fails with invalid sample IDs"""
    config = TaskConfig(
        name='Invalid Task',
        description=None,
        sample_ids=[str(uuid4()), str(uuid4())],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=None
    )
    
    with pytest.raises(ValueError, match="Samples not found"):
        task_service.create_task(config, created_by='admin-1')


def test_create_task_past_deadline(task_service, samples):
    """Test task creation fails with past deadline"""
    config = TaskConfig(
        name='Past Deadline Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=datetime.utcnow() - timedelta(days=1),
        assigned_to=None
    )
    
    with pytest.raises(ValueError, match="Deadline must be a future date"):
        task_service.create_task(config, created_by='admin-1')


def test_create_task_empty_name(task_service, samples):
    """Test task creation fails with empty name"""
    config = TaskConfig(
        name='   ',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=None
    )
    
    with pytest.raises(ValueError, match="Task name is required"):
        task_service.create_task(config, created_by='admin-1')


def test_create_task_empty_instructions(task_service, samples):
    """Test task creation fails with empty instructions"""
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='   ',
        deadline=None,
        assigned_to=None
    )
    
    with pytest.raises(ValueError, match="Task instructions are required"):
        task_service.create_task(config, created_by='admin-1')


# ============================================================================
# Test: Assign Annotator
# ============================================================================

def test_assign_annotator_success(task_service, samples, db_session):
    """Test successful annotator assignment"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=[]
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Assign annotator
    task_service.assign_annotator(
        task_id=task['id'],
        annotator_id='annotator-1',
        assigned_by='admin-1'
    )
    
    # Verify assignment
    updated_task = task_service.get_task(task['id'])
    assert 'annotator-1' in updated_task['assigned_to']
    assert updated_task['status'] == TaskStatus.IN_PROGRESS.value


def test_assign_annotator_multiple(task_service, samples, db_session):
    """Test assigning multiple annotators"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Assign additional annotators
    task_service.assign_annotator(task['id'], 'annotator-2', 'admin-1')
    task_service.assign_annotator(task['id'], 'annotator-3', 'admin-1')
    
    # Verify assignments
    updated_task = task_service.get_task(task['id'])
    assert len(updated_task['assigned_to']) == 3
    assert 'annotator-1' in updated_task['assigned_to']
    assert 'annotator-2' in updated_task['assigned_to']
    assert 'annotator-3' in updated_task['assigned_to']


def test_assign_annotator_duplicate(task_service, samples, db_session):
    """Test assigning same annotator twice (should not duplicate)"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Assign same annotator again
    task_service.assign_annotator(task['id'], 'annotator-1', 'admin-1')
    
    # Verify no duplicate
    updated_task = task_service.get_task(task['id'])
    assert updated_task['assigned_to'].count('annotator-1') == 1


def test_assign_annotator_completed_task(task_service, samples, db_session):
    """Test assignment fails for completed task"""
    # Create and complete task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Submit annotation and complete
    annotation = Annotation(
        task_id=task['id'],
        sample_id=str(samples[0].id),
        annotator_id='annotator-1',
        labels=[{'label': 'positive', 'score': 0.9}]
    )
    task_service.submit_annotation(annotation)
    task_service.complete_task(task['id'], 'admin-1')
    
    # Try to assign annotator
    with pytest.raises(ValueError, match="Cannot assign annotator to completed task"):
        task_service.assign_annotator(task['id'], 'annotator-2', 'admin-1')


def test_assign_annotator_not_found(task_service):
    """Test assignment fails when task not found"""
    with pytest.raises(ValueError, match="not found"):
        task_service.assign_annotator(
            task_id=str(uuid4()),
            annotator_id='annotator-1',
            assigned_by='admin-1'
        )


# ============================================================================
# Test: Get Task
# ============================================================================

def test_get_task_success(task_service, samples):
    """Test successful task retrieval"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description='Description',
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Get task
    retrieved_task = task_service.get_task(task['id'])
    
    # Verify task details
    assert retrieved_task['id'] == task['id']
    assert retrieved_task['name'] == 'Test Task'
    assert retrieved_task['description'] == 'Description'
    assert retrieved_task['status'] == TaskStatus.CREATED.value


def test_get_task_not_found(task_service):
    """Test get task fails when task not found"""
    with pytest.raises(ValueError, match="not found"):
        task_service.get_task(str(uuid4()))


# ============================================================================
# Test: Submit Annotation
# ============================================================================

def test_submit_annotation_success(task_service, samples, db_session):
    """Test successful annotation submission"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Submit annotation
    annotation = Annotation(
        task_id=task['id'],
        sample_id=str(samples[0].id),
        annotator_id='annotator-1',
        labels=[{'label': 'positive', 'score': 0.9}],
        comments='Looks good',
        confidence=0.95
    )
    result = task_service.submit_annotation(annotation)
    
    # Verify result
    assert result.task_id == task['id']
    assert result.sample_id == str(samples[0].id)
    assert result.annotator_id == 'annotator-1'
    assert result.annotation_id is not None
    
    # Verify task progress updated
    progress = task_service.get_task_progress(task['id'])
    assert progress.completed == 1
    assert progress.total == 1
    assert progress.percentage == 100.0


def test_submit_annotation_updates_existing(task_service, samples, db_session):
    """Test submitting annotation updates existing annotation for same sample"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Submit first annotation
    annotation1 = Annotation(
        task_id=task['id'],
        sample_id=str(samples[0].id),
        annotator_id='annotator-1',
        labels=[{'label': 'positive', 'score': 0.8}]
    )
    task_service.submit_annotation(annotation1)
    
    # Submit updated annotation for same sample
    annotation2 = Annotation(
        task_id=task['id'],
        sample_id=str(samples[0].id),
        annotator_id='annotator-1',
        labels=[{'label': 'negative', 'score': 0.9}]
    )
    task_service.submit_annotation(annotation2)
    
    # Verify progress didn't double-count
    progress = task_service.get_task_progress(task['id'])
    assert progress.completed == 1
    
    # Verify annotation was updated
    task_data = task_service.get_task(task['id'])
    assert len(task_data['annotations']) == 1
    assert task_data['annotations'][0]['labels'][0]['label'] == 'negative'


def test_submit_annotation_task_not_found(task_service, samples):
    """Test annotation submission fails when task not found"""
    annotation = Annotation(
        task_id=str(uuid4()),
        sample_id=str(samples[0].id),
        annotator_id='annotator-1',
        labels=[{'label': 'positive'}]
    )
    
    with pytest.raises(ValueError, match="Task .* not found"):
        task_service.submit_annotation(annotation)


def test_submit_annotation_sample_not_in_task(task_service, samples):
    """Test annotation submission fails when sample not in task"""
    # Create task with only first sample
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Try to annotate second sample
    annotation = Annotation(
        task_id=task['id'],
        sample_id=str(samples[1].id),
        annotator_id='annotator-1',
        labels=[{'label': 'positive'}]
    )
    
    with pytest.raises(ValueError, match="is not part of task"):
        task_service.submit_annotation(annotation)


def test_submit_annotation_annotator_not_assigned(task_service, samples):
    """Test annotation submission fails when annotator not assigned"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Try to submit annotation from unassigned annotator
    annotation = Annotation(
        task_id=task['id'],
        sample_id=str(samples[0].id),
        annotator_id='annotator-2',
        labels=[{'label': 'positive'}]
    )
    
    with pytest.raises(ValueError, match="is not assigned to task"):
        task_service.submit_annotation(annotation)


def test_submit_annotation_empty_labels(task_service, samples):
    """Test annotation submission fails with empty labels"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Try to submit annotation with empty labels
    annotation = Annotation(
        task_id=task['id'],
        sample_id=str(samples[0].id),
        annotator_id='annotator-1',
        labels=[]
    )
    
    with pytest.raises(ValueError, match="Annotation labels are required"):
        task_service.submit_annotation(annotation)


# ============================================================================
# Test: Get Task Progress
# ============================================================================

def test_get_task_progress_no_annotations(task_service, samples):
    """Test progress for task with no annotations"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(s.id) for s in samples],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Get progress
    progress = task_service.get_task_progress(task['id'])
    
    assert progress.total == 3
    assert progress.completed == 0
    assert progress.in_progress == 0
    assert progress.percentage == 0.0


def test_get_task_progress_partial_annotations(task_service, samples):
    """Test progress for task with partial annotations"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(s.id) for s in samples],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Submit annotation for first sample
    annotation = Annotation(
        task_id=task['id'],
        sample_id=str(samples[0].id),
        annotator_id='annotator-1',
        labels=[{'label': 'positive'}]
    )
    task_service.submit_annotation(annotation)
    
    # Get progress
    progress = task_service.get_task_progress(task['id'])
    
    assert progress.total == 3
    assert progress.completed == 1
    assert progress.percentage == 33.33


def test_get_task_progress_all_annotations(task_service, samples):
    """Test progress for task with all annotations"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(s.id) for s in samples],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Submit annotations for all samples
    for sample in samples:
        annotation = Annotation(
            task_id=task['id'],
            sample_id=str(sample.id),
            annotator_id='annotator-1',
            labels=[{'label': 'positive'}]
        )
        task_service.submit_annotation(annotation)
    
    # Get progress
    progress = task_service.get_task_progress(task['id'])
    
    assert progress.total == 3
    assert progress.completed == 3
    assert progress.percentage == 100.0


def test_get_task_progress_not_found(task_service):
    """Test progress fails when task not found"""
    with pytest.raises(ValueError, match="not found"):
        task_service.get_task_progress(str(uuid4()))


# ============================================================================
# Test: Complete Task
# ============================================================================

def test_complete_task_success(task_service, samples, db_session):
    """Test successful task completion"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(s.id) for s in samples],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Submit annotations for all samples
    for sample in samples:
        annotation = Annotation(
            task_id=task['id'],
            sample_id=str(sample.id),
            annotator_id='annotator-1',
            labels=[{'label': 'positive'}]
        )
        task_service.submit_annotation(annotation)
    
    # Complete task
    task_service.complete_task(task['id'], completed_by='admin-1')
    
    # Verify task is completed
    completed_task = task_service.get_task(task['id'])
    assert completed_task['status'] == TaskStatus.COMPLETED.value
    assert completed_task['completed_at'] is not None


def test_complete_task_incomplete_annotations(task_service, samples):
    """Test completion fails when not all samples are annotated"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(s.id) for s in samples],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Submit annotation for only first sample
    annotation = Annotation(
        task_id=task['id'],
        sample_id=str(samples[0].id),
        annotator_id='annotator-1',
        labels=[{'label': 'positive'}]
    )
    task_service.submit_annotation(annotation)
    
    # Try to complete task
    with pytest.raises(ValueError, match="Cannot complete task: 1/3 samples annotated"):
        task_service.complete_task(task['id'], completed_by='admin-1')


def test_complete_task_invalid_status(task_service, samples):
    """Test completion fails when task not in progress"""
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=[]
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Try to complete task that's still in CREATED status
    with pytest.raises(ValueError, match="Task must be IN_PROGRESS"):
        task_service.complete_task(task['id'], completed_by='admin-1')


def test_complete_task_not_found(task_service):
    """Test completion fails when task not found"""
    with pytest.raises(ValueError, match="not found"):
        task_service.complete_task(str(uuid4()), completed_by='admin-1')


# ============================================================================
# Test: Audit Logging Integration
# ============================================================================

def test_audit_logging_on_create(task_service, samples, db_session):
    """Test that audit logs are created on task creation"""
    from src.models.data_lifecycle import AuditLogModel
    
    # Create task
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    # Check audit logs
    logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.resource_id == task['id'],
        AuditLogModel.operation_type == OperationType.CREATE
    ).all()
    
    assert len(logs) >= 1
    create_log = next((log for log in logs if log.details.get('action') == 'create_task'), None)
    assert create_log is not None
    assert create_log.user_id == 'admin-1'
    assert create_log.details['task_name'] == 'Test Task'


def test_audit_logging_on_assign(task_service, samples, db_session):
    """Test that audit logs are created on annotator assignment"""
    from src.models.data_lifecycle import AuditLogModel
    
    # Create task and assign annotator
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=[]
    )
    task = task_service.create_task(config, created_by='admin-1')
    task_service.assign_annotator(task['id'], 'annotator-1', 'admin-1')
    
    # Check audit logs
    logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.resource_id == task['id'],
        AuditLogModel.operation_type == OperationType.UPDATE
    ).all()
    
    assign_log = next((log for log in logs if log.details.get('action') == 'assign_annotator'), None)
    assert assign_log is not None
    assert assign_log.user_id == 'admin-1'
    assert assign_log.details['annotator_id'] == 'annotator-1'


def test_audit_logging_on_submit_annotation(task_service, samples, db_session):
    """Test that audit logs are created on annotation submission"""
    from src.models.data_lifecycle import AuditLogModel
    
    # Create task and submit annotation
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    annotation = Annotation(
        task_id=task['id'],
        sample_id=str(samples[0].id),
        annotator_id='annotator-1',
        labels=[{'label': 'positive'}]
    )
    task_service.submit_annotation(annotation)
    
    # Check audit logs
    logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.resource_id == task['id'],
        AuditLogModel.action == Action.ANNOTATE
    ).all()
    
    assert len(logs) >= 1
    submit_log = next((log for log in logs if log.details.get('action') == 'submit_annotation'), None)
    assert submit_log is not None
    assert submit_log.user_id == 'annotator-1'


def test_audit_logging_on_complete(task_service, samples, db_session):
    """Test that audit logs are created on task completion"""
    from src.models.data_lifecycle import AuditLogModel
    
    # Create task, annotate, and complete
    config = TaskConfig(
        name='Test Task',
        description=None,
        sample_ids=[str(samples[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test',
        deadline=None,
        assigned_to=['annotator-1']
    )
    task = task_service.create_task(config, created_by='admin-1')
    
    annotation = Annotation(
        task_id=task['id'],
        sample_id=str(samples[0].id),
        annotator_id='annotator-1',
        labels=[{'label': 'positive'}]
    )
    task_service.submit_annotation(annotation)
    task_service.complete_task(task['id'], completed_by='admin-1')
    
    # Check audit logs
    logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.resource_id == task['id'],
        AuditLogModel.operation_type == OperationType.UPDATE
    ).all()
    
    complete_log = next((log for log in logs if log.details.get('action') == 'complete_task'), None)
    assert complete_log is not None
    assert complete_log.user_id == 'admin-1'
    assert complete_log.details['total_annotations'] == 1
