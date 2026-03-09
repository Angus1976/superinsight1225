"""
Unit tests for Annotation Task API endpoints.

Tests all API endpoints for annotation task management including
task creation, annotator assignment, annotation submission,
progress tracking, and task completion.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 14.1, 14.2
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, INET

from src.database.connection import Base, get_db_session
from src.api.annotation_task_api import router
from src.models.data_lifecycle import (
    SampleModel,
    AnnotationTaskModel,
    AnnotationType,
    TaskStatus
)
from fastapi import FastAPI


# ============================================================================
# SQLite Compatibility
# ============================================================================

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    """Compile JSONB to JSON for SQLite compatibility."""
    return "JSON"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kw):
    """Compile INET to VARCHAR for SQLite compatibility."""
    return "VARCHAR(45)"


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(test_db):
    """Create test client."""
    app = FastAPI()
    app.include_router(router)
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db_session] = override_get_db
    return TestClient(app)


@pytest.fixture
def sample_data(test_db):
    """Create sample data for testing."""
    samples = []
    for i in range(3):
        sample = SampleModel(
            id=uuid4(),
            data_id=str(uuid4()),
            content={'title': f'Sample {i}', 'text': f'Content {i}'},
            category='test_category',
            quality_overall=0.8,
            quality_completeness=0.8,
            quality_accuracy=0.8,
            quality_consistency=0.8,
            version=1,
            tags=['test', f'sample{i}'],
            usage_count=0,
            last_used_at=None,
            metadata_={'source': 'test'},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db.add(sample)
        samples.append(sample)
    
    test_db.commit()
    return samples


# ============================================================================
# Test Create Annotation Task
# ============================================================================

def test_create_task_success(client, sample_data):
    """Test successful task creation."""
    sample_ids = [str(s.id) for s in sample_data]
    deadline = datetime.utcnow() + timedelta(days=7)
    
    request_data = {
        'name': 'Test Annotation Task',
        'description': 'Test task description',
        'sample_ids': sample_ids,
        'annotation_type': AnnotationType.CLASSIFICATION.value,
        'instructions': 'Please classify the samples',
        'deadline': deadline.isoformat(),
        'assigned_to': ['user1', 'user2'],
        'created_by': 'admin'
    }
    
    response = client.post('/api/annotation-tasks', json=request_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data['name'] == 'Test Annotation Task'
    assert data['description'] == 'Test task description'
    assert len(data['sample_ids']) == 3
    assert data['annotation_type'] == AnnotationType.CLASSIFICATION.value
    assert data['status'] == TaskStatus.CREATED.value
    assert data['created_by'] == 'admin'
    assert len(data['assigned_to']) == 2
    assert data['progress']['total'] == 3
    assert data['progress']['completed'] == 0


def test_create_task_minimal_fields(client, sample_data):
    """Test task creation with minimal required fields."""
    sample_ids = [str(sample_data[0].id)]
    
    request_data = {
        'name': 'Minimal Task',
        'sample_ids': sample_ids,
        'annotation_type': AnnotationType.ENTITY_RECOGNITION.value,
        'instructions': 'Annotate entities',
        'created_by': 'admin'
    }
    
    response = client.post('/api/annotation-tasks', json=request_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data['name'] == 'Minimal Task'
    assert data['description'] is None
    assert data['deadline'] is None
    assert data['assigned_to'] == []


def test_create_task_empty_name(client, sample_data):
    """Test task creation with empty name fails."""
    sample_ids = [str(sample_data[0].id)]
    
    request_data = {
        'name': '',
        'sample_ids': sample_ids,
        'annotation_type': AnnotationType.CLASSIFICATION.value,
        'instructions': 'Test instructions',
        'created_by': 'admin'
    }
    
    response = client.post('/api/annotation-tasks', json=request_data)
    
    # Pydantic validation returns 422 for validation errors
    assert response.status_code == 422


def test_create_task_empty_instructions(client, sample_data):
    """Test task creation with empty instructions fails."""
    sample_ids = [str(sample_data[0].id)]
    
    request_data = {
        'name': 'Test Task',
        'sample_ids': sample_ids,
        'annotation_type': AnnotationType.CLASSIFICATION.value,
        'instructions': '',
        'created_by': 'admin'
    }
    
    response = client.post('/api/annotation-tasks', json=request_data)
    
    # Pydantic validation returns 422 for validation errors
    assert response.status_code == 422


def test_create_task_invalid_sample_ids(client):
    """Test task creation with non-existent sample IDs fails."""
    request_data = {
        'name': 'Test Task',
        'sample_ids': [str(uuid4()), str(uuid4())],
        'annotation_type': AnnotationType.CLASSIFICATION.value,
        'instructions': 'Test instructions',
        'created_by': 'admin'
    }
    
    response = client.post('/api/annotation-tasks', json=request_data)
    
    assert response.status_code == 400
    assert 'not found' in response.json()['detail'].lower()


def test_create_task_past_deadline(client, sample_data):
    """Test task creation with past deadline fails."""
    sample_ids = [str(sample_data[0].id)]
    past_deadline = datetime.utcnow() - timedelta(days=1)
    
    request_data = {
        'name': 'Test Task',
        'sample_ids': sample_ids,
        'annotation_type': AnnotationType.CLASSIFICATION.value,
        'instructions': 'Test instructions',
        'deadline': past_deadline.isoformat(),
        'created_by': 'admin'
    }
    
    response = client.post('/api/annotation-tasks', json=request_data)
    
    assert response.status_code == 400
    assert 'future' in response.json()['detail'].lower()


# ============================================================================
# Test Assign Annotator
# ============================================================================

def test_assign_annotator_success(client, sample_data, test_db):
    """Test successful annotator assignment."""
    # Create task
    task = AnnotationTaskModel(
        id=uuid4(),
        name='Test Task',
        description='Test description',
        sample_ids=[str(sample_data[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test instructions',
        status=TaskStatus.CREATED,
        created_by='admin',
        created_at=datetime.utcnow(),
        assigned_to=[],
        deadline=None,
        completed_at=None,
        progress_total=1,
        progress_completed=0,
        progress_in_progress=0,
        annotations=[],
        metadata_={}
    )
    test_db.add(task)
    test_db.commit()
    
    request_data = {
        'annotator_id': 'user1',
        'assigned_by': 'admin'
    }
    
    response = client.put(f'/api/annotation-tasks/{task.id}/assign', json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data['annotator_id'] == 'user1'
    assert 'successfully' in data['message'].lower()


def test_assign_annotator_task_not_found(client):
    """Test assigning annotator to non-existent task fails."""
    task_id = uuid4()
    request_data = {
        'annotator_id': 'user1',
        'assigned_by': 'admin'
    }
    
    response = client.put(f'/api/annotation-tasks/{task_id}/assign', json=request_data)
    
    assert response.status_code == 404
    assert 'not found' in response.json()['detail'].lower()


def test_assign_annotator_completed_task(client, sample_data, test_db):
    """Test assigning annotator to completed task fails."""
    task = AnnotationTaskModel(
        id=uuid4(),
        name='Completed Task',
        description='Test description',
        sample_ids=[str(sample_data[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test instructions',
        status=TaskStatus.COMPLETED,
        created_by='admin',
        created_at=datetime.utcnow(),
        assigned_to=['user1'],
        deadline=None,
        completed_at=datetime.utcnow(),
        progress_total=1,
        progress_completed=1,
        progress_in_progress=0,
        annotations=[],
        metadata_={}
    )
    test_db.add(task)
    test_db.commit()
    
    request_data = {
        'annotator_id': 'user2',
        'assigned_by': 'admin'
    }
    
    response = client.put(f'/api/annotation-tasks/{task.id}/assign', json=request_data)
    
    assert response.status_code == 400
    assert 'completed' in response.json()['detail'].lower()


# ============================================================================
# Test Get Task Details
# ============================================================================

def test_get_task_details_success(client, sample_data, test_db):
    """Test successful task details retrieval."""
    task = AnnotationTaskModel(
        id=uuid4(),
        name='Test Task',
        description='Test description',
        sample_ids=[str(s.id) for s in sample_data],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test instructions',
        status=TaskStatus.IN_PROGRESS,
        created_by='admin',
        created_at=datetime.utcnow(),
        assigned_to=['user1', 'user2'],
        deadline=None,
        completed_at=None,
        progress_total=3,
        progress_completed=1,
        progress_in_progress=0,
        annotations=[{
            'id': str(uuid4()),
            'sample_id': str(sample_data[0].id),
            'annotator_id': 'user1',
            'labels': [{'label': 'positive'}],
            'submitted_at': datetime.utcnow().isoformat()
        }],
        metadata_={}
    )
    test_db.add(task)
    test_db.commit()
    
    response = client.get(f'/api/annotation-tasks/{task.id}')
    
    assert response.status_code == 200
    data = response.json()
    assert data['name'] == 'Test Task'
    assert data['status'] == TaskStatus.IN_PROGRESS.value
    assert len(data['sample_ids']) == 3
    assert len(data['assigned_to']) == 2
    assert data['progress']['total'] == 3
    assert data['progress']['completed'] == 1
    assert len(data['annotations']) == 1


def test_get_task_details_not_found(client):
    """Test getting details of non-existent task fails."""
    task_id = uuid4()
    
    response = client.get(f'/api/annotation-tasks/{task_id}')
    
    assert response.status_code == 404
    assert 'not found' in response.json()['detail'].lower()


# ============================================================================
# Test Submit Annotation
# ============================================================================

def test_submit_annotation_success(client, sample_data, test_db):
    """Test successful annotation submission."""
    task = AnnotationTaskModel(
        id=uuid4(),
        name='Test Task',
        description='Test description',
        sample_ids=[str(sample_data[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test instructions',
        status=TaskStatus.IN_PROGRESS,
        created_by='admin',
        created_at=datetime.utcnow(),
        assigned_to=['user1'],
        deadline=None,
        completed_at=None,
        progress_total=1,
        progress_completed=0,
        progress_in_progress=0,
        annotations=[],
        metadata_={}
    )
    test_db.add(task)
    test_db.commit()
    
    request_data = {
        'sample_id': str(sample_data[0].id),
        'annotator_id': 'user1',
        'labels': [{'label': 'positive', 'confidence': 0.9}],
        'comments': 'Clear positive sentiment',
        'confidence': 0.9
    }
    
    response = client.post(f'/api/annotation-tasks/{task.id}/annotations', json=request_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data['sample_id'] == str(sample_data[0].id)
    assert data['annotator_id'] == 'user1'
    assert 'annotation_id' in data
    assert 'submitted_at' in data


def test_submit_annotation_task_not_found(client, sample_data):
    """Test submitting annotation to non-existent task fails."""
    task_id = uuid4()
    request_data = {
        'sample_id': str(sample_data[0].id),
        'annotator_id': 'user1',
        'labels': [{'label': 'positive'}]
    }
    
    response = client.post(f'/api/annotation-tasks/{task_id}/annotations', json=request_data)
    
    assert response.status_code == 404
    assert 'not found' in response.json()['detail'].lower()


def test_submit_annotation_sample_not_in_task(client, sample_data, test_db):
    """Test submitting annotation for sample not in task fails."""
    task = AnnotationTaskModel(
        id=uuid4(),
        name='Test Task',
        description='Test description',
        sample_ids=[str(sample_data[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test instructions',
        status=TaskStatus.IN_PROGRESS,
        created_by='admin',
        created_at=datetime.utcnow(),
        assigned_to=['user1'],
        deadline=None,
        completed_at=None,
        progress_total=1,
        progress_completed=0,
        progress_in_progress=0,
        annotations=[],
        metadata_={}
    )
    test_db.add(task)
    test_db.commit()
    
    request_data = {
        'sample_id': str(sample_data[1].id),  # Different sample
        'annotator_id': 'user1',
        'labels': [{'label': 'positive'}]
    }
    
    response = client.post(f'/api/annotation-tasks/{task.id}/annotations', json=request_data)
    
    assert response.status_code == 400
    assert 'not part of task' in response.json()['detail'].lower()


def test_submit_annotation_annotator_not_assigned(client, sample_data, test_db):
    """Test submitting annotation by unassigned annotator fails."""
    task = AnnotationTaskModel(
        id=uuid4(),
        name='Test Task',
        description='Test description',
        sample_ids=[str(sample_data[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test instructions',
        status=TaskStatus.IN_PROGRESS,
        created_by='admin',
        created_at=datetime.utcnow(),
        assigned_to=['user1'],
        deadline=None,
        completed_at=None,
        progress_total=1,
        progress_completed=0,
        progress_in_progress=0,
        annotations=[],
        metadata_={}
    )
    test_db.add(task)
    test_db.commit()
    
    request_data = {
        'sample_id': str(sample_data[0].id),
        'annotator_id': 'user2',  # Not assigned
        'labels': [{'label': 'positive'}]
    }
    
    response = client.post(f'/api/annotation-tasks/{task.id}/annotations', json=request_data)
    
    assert response.status_code == 400
    assert 'not assigned' in response.json()['detail'].lower()


def test_submit_annotation_empty_labels(client, sample_data, test_db):
    """Test submitting annotation with empty labels fails."""
    task = AnnotationTaskModel(
        id=uuid4(),
        name='Test Task',
        description='Test description',
        sample_ids=[str(sample_data[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test instructions',
        status=TaskStatus.IN_PROGRESS,
        created_by='admin',
        created_at=datetime.utcnow(),
        assigned_to=['user1'],
        deadline=None,
        completed_at=None,
        progress_total=1,
        progress_completed=0,
        progress_in_progress=0,
        annotations=[],
        metadata_={}
    )
    test_db.add(task)
    test_db.commit()
    
    request_data = {
        'sample_id': str(sample_data[0].id),
        'annotator_id': 'user1',
        'labels': []
    }
    
    response = client.post(f'/api/annotation-tasks/{task.id}/annotations', json=request_data)
    
    # Pydantic validation returns 422 for validation errors
    assert response.status_code == 422


# ============================================================================
# Test Get Task Progress
# ============================================================================

def test_get_task_progress_success(client, sample_data, test_db):
    """Test successful task progress retrieval."""
    task = AnnotationTaskModel(
        id=uuid4(),
        name='Test Task',
        description='Test description',
        sample_ids=[str(s.id) for s in sample_data],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test instructions',
        status=TaskStatus.IN_PROGRESS,
        created_by='admin',
        created_at=datetime.utcnow(),
        assigned_to=['user1'],
        deadline=None,
        completed_at=None,
        progress_total=3,
        progress_completed=2,
        progress_in_progress=0,
        annotations=[],
        metadata_={}
    )
    test_db.add(task)
    test_db.commit()
    
    response = client.get(f'/api/annotation-tasks/{task.id}/progress')
    
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 3
    assert data['completed'] == 2
    assert data['in_progress'] == 0
    assert data['percentage'] == pytest.approx(66.67, rel=0.01)


def test_get_task_progress_not_found(client):
    """Test getting progress of non-existent task fails."""
    task_id = uuid4()
    
    response = client.get(f'/api/annotation-tasks/{task_id}/progress')
    
    assert response.status_code == 404
    assert 'not found' in response.json()['detail'].lower()


# ============================================================================
# Test Complete Task
# ============================================================================

def test_complete_task_success(client, sample_data, test_db):
    """Test successful task completion."""
    task = AnnotationTaskModel(
        id=uuid4(),
        name='Test Task',
        description='Test description',
        sample_ids=[str(sample_data[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test instructions',
        status=TaskStatus.IN_PROGRESS,
        created_by='admin',
        created_at=datetime.utcnow(),
        assigned_to=['user1'],
        deadline=None,
        completed_at=None,
        progress_total=1,
        progress_completed=1,  # All samples annotated
        progress_in_progress=0,
        annotations=[{
            'id': str(uuid4()),
            'sample_id': str(sample_data[0].id),
            'annotator_id': 'user1',
            'labels': [{'label': 'positive'}],
            'submitted_at': datetime.utcnow().isoformat()
        }],
        metadata_={}
    )
    test_db.add(task)
    test_db.commit()
    
    request_data = {
        'completed_by': 'admin'
    }
    
    response = client.post(f'/api/annotation-tasks/{task.id}/complete', json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert 'successfully' in data['message'].lower()
    assert data['completed_by'] == 'admin'


def test_complete_task_not_found(client):
    """Test completing non-existent task fails."""
    task_id = uuid4()
    request_data = {
        'completed_by': 'admin'
    }
    
    response = client.post(f'/api/annotation-tasks/{task_id}/complete', json=request_data)
    
    assert response.status_code == 404
    assert 'not found' in response.json()['detail'].lower()


def test_complete_task_not_all_annotated(client, sample_data, test_db):
    """Test completing task with incomplete annotations fails."""
    task = AnnotationTaskModel(
        id=uuid4(),
        name='Test Task',
        description='Test description',
        sample_ids=[str(s.id) for s in sample_data],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test instructions',
        status=TaskStatus.IN_PROGRESS,
        created_by='admin',
        created_at=datetime.utcnow(),
        assigned_to=['user1'],
        deadline=None,
        completed_at=None,
        progress_total=3,
        progress_completed=1,  # Only 1 of 3 annotated
        progress_in_progress=0,
        annotations=[],
        metadata_={}
    )
    test_db.add(task)
    test_db.commit()
    
    request_data = {
        'completed_by': 'admin'
    }
    
    response = client.post(f'/api/annotation-tasks/{task.id}/complete', json=request_data)
    
    assert response.status_code == 400
    assert 'all samples must be annotated' in response.json()['detail'].lower()


def test_complete_task_wrong_status(client, sample_data, test_db):
    """Test completing task in wrong status fails."""
    task = AnnotationTaskModel(
        id=uuid4(),
        name='Test Task',
        description='Test description',
        sample_ids=[str(sample_data[0].id)],
        annotation_type=AnnotationType.CLASSIFICATION,
        instructions='Test instructions',
        status=TaskStatus.CREATED,  # Not IN_PROGRESS
        created_by='admin',
        created_at=datetime.utcnow(),
        assigned_to=['user1'],
        deadline=None,
        completed_at=None,
        progress_total=1,
        progress_completed=1,
        progress_in_progress=0,
        annotations=[],
        metadata_={}
    )
    test_db.add(task)
    test_db.commit()
    
    request_data = {
        'completed_by': 'admin'
    }
    
    response = client.post(f'/api/annotation-tasks/{task.id}/complete', json=request_data)
    
    assert response.status_code == 400
    assert 'in_progress' in response.json()['detail'].lower()


# ============================================================================
# Test List Tasks
# ============================================================================

def test_list_tasks_success(client, sample_data, test_db):
    """Test successful task listing."""
    # Create multiple tasks
    for i in range(5):
        task = AnnotationTaskModel(
            id=uuid4(),
            name=f'Task {i}',
            description=f'Description {i}',
            sample_ids=[str(sample_data[0].id)],
            annotation_type=AnnotationType.CLASSIFICATION,
            instructions='Test instructions',
            status=TaskStatus.CREATED if i < 3 else TaskStatus.IN_PROGRESS,
            created_by='admin',
            created_at=datetime.utcnow(),
            assigned_to=['user1'] if i >= 3 else [],
            deadline=None,
            completed_at=None,
            progress_total=1,
            progress_completed=0,
            progress_in_progress=0,
            annotations=[],
            metadata_={}
        )
        test_db.add(task)
    test_db.commit()
    
    response = client.get('/api/annotation-tasks?page=1&page_size=10')
    
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 5
    assert len(data['items']) == 5
    assert data['page'] == 1
    assert data['page_size'] == 10


def test_list_tasks_with_pagination(client, sample_data, test_db):
    """Test task listing with pagination."""
    # Create 15 tasks
    for i in range(15):
        task = AnnotationTaskModel(
            id=uuid4(),
            name=f'Task {i}',
            description=f'Description {i}',
            sample_ids=[str(sample_data[0].id)],
            annotation_type=AnnotationType.CLASSIFICATION,
            instructions='Test instructions',
            status=TaskStatus.CREATED,
            created_by='admin',
            created_at=datetime.utcnow(),
            assigned_to=[],
            deadline=None,
            completed_at=None,
            progress_total=1,
            progress_completed=0,
            progress_in_progress=0,
            annotations=[],
            metadata_={}
        )
        test_db.add(task)
    test_db.commit()
    
    # Get page 1
    response = client.get('/api/annotation-tasks?page=1&page_size=10')
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 15
    assert len(data['items']) == 10
    assert data['total_pages'] == 2
    
    # Get page 2
    response = client.get('/api/annotation-tasks?page=2&page_size=10')
    assert response.status_code == 200
    data = response.json()
    assert len(data['items']) == 5


def test_list_tasks_filter_by_status(client, sample_data, test_db):
    """Test task listing with status filter."""
    # Create tasks with different statuses
    for status in [TaskStatus.CREATED, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]:
        task = AnnotationTaskModel(
            id=uuid4(),
            name=f'Task {status.value}',
            description='Test description',
            sample_ids=[str(sample_data[0].id)],
            annotation_type=AnnotationType.CLASSIFICATION,
            instructions='Test instructions',
            status=status,
            created_by='admin',
            created_at=datetime.utcnow(),
            assigned_to=['user1'],
            deadline=None,
            completed_at=datetime.utcnow() if status == TaskStatus.COMPLETED else None,
            progress_total=1,
            progress_completed=1 if status == TaskStatus.COMPLETED else 0,
            progress_in_progress=0,
            annotations=[],
            metadata_={}
        )
        test_db.add(task)
    test_db.commit()
    
    response = client.get(f'/api/annotation-tasks?status_filter={TaskStatus.IN_PROGRESS.value}')
    
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 1
    assert data['items'][0]['status'] == TaskStatus.IN_PROGRESS.value


def test_list_tasks_filter_by_created_by(client, sample_data, test_db):
    """Test task listing with creator filter."""
    # Create tasks by different users
    for user in ['admin', 'user1', 'user2']:
        task = AnnotationTaskModel(
            id=uuid4(),
            name=f'Task by {user}',
            description='Test description',
            sample_ids=[str(sample_data[0].id)],
            annotation_type=AnnotationType.CLASSIFICATION,
            instructions='Test instructions',
            status=TaskStatus.CREATED,
            created_by=user,
            created_at=datetime.utcnow(),
            assigned_to=[],
            deadline=None,
            completed_at=None,
            progress_total=1,
            progress_completed=0,
            progress_in_progress=0,
            annotations=[],
            metadata_={}
        )
        test_db.add(task)
    test_db.commit()
    
    response = client.get('/api/annotation-tasks?created_by=admin')
    
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 1
    assert data['items'][0]['created_by'] == 'admin'


def test_list_tasks_empty(client):
    """Test listing tasks when none exist."""
    response = client.get('/api/annotation-tasks')
    
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 0
    assert len(data['items']) == 0
    assert data['total_pages'] == 0
