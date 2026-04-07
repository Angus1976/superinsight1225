"""
Unit tests for Enhancement Service

Tests enhancement job creation, application, validation, rollback,
and all five enhancement algorithms.
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from sqlalchemy import cast, create_engine, String, TypeDecorator
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.data_lifecycle import (
    EnhancedDataModel,
    SampleModel,
    VersionModel,
    AuditLogModel,
    EnhancementType,
    JobStatus,
    ResourceType,
    OperationType,
    OperationResult,
    Action
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
            return str(value) if isinstance(value, UUID) else str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return UUID(value) if not isinstance(value, UUID) else value
        return value


PATCHED_MODELS = [EnhancedDataModel, SampleModel, VersionModel, AuditLogModel]


def _snapshot_uuid_columns(models):
    """Pairs of (column, PGUUID type instance) for resetting between tests."""
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    pairs = []
    for model in models:
        for col in model.__table__.columns:
            if isinstance(col.type, PGUUID):
                pairs.append((col, col.type))
    return pairs


# Captured at import time (before any test mutates mapped column types).
_UUID_COLUMN_SNAPSHOT = _snapshot_uuid_columns(PATCHED_MODELS)


@pytest.fixture(scope='function')
def db_session():
    """Create an in-memory SQLite database with UUID patching"""
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )

    # Other unit tests may leave UUID columns as SQLiteUUID; normalize first.
    for col, original_pg in _UUID_COLUMN_SNAPSHOT:
        col.type = original_pg

    _uuid_col_restore = []
    for model in PATCHED_MODELS:
        for col in model.__table__.columns:
            if isinstance(col.type, PGUUID):
                _uuid_col_restore.append((col, col.type))
                col.type = SQLiteUUID()

    for model in PATCHED_MODELS:
        model.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()

    for col, original_type in _uuid_col_restore:
        col.type = original_type


@pytest.fixture
def service(db_session):
    """Create an EnhancementService instance"""
    return EnhancementService(db_session)


@pytest.fixture
def sample_content():
    """Sample content for enhancement testing"""
    return {
        'title': 'Test Document',
        'text': 'This is a sample text for testing enhancement algorithms.',
        'tags': ['test', 'sample'],
        'score': 0.75,
        'metadata': {'author': 'tester', 'version': '1.0'}
    }



# ============================================================================
# Test: Create Enhancement Job
# ============================================================================

def test_create_job_success(service):
    """Test successful enhancement job creation"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT,
        parameters={'clean_whitespace': True}
    )
    job = service.create_enhancement_job(config, created_by='admin-1')

    assert job.id is not None
    assert job.status == JobStatus.QUEUED
    assert job.config.data_id == 'data-123'
    assert job.config.enhancement_type == EnhancementType.QUALITY_IMPROVEMENT
    assert job.created_by == 'admin-1'
    assert job.started_at is not None


def test_create_job_all_enhancement_types(service):
    """Test job creation for each enhancement type"""
    for etype in EnhancementType:
        config = EnhancementConfig(
            data_id=f'data-{etype.value}',
            enhancement_type=etype
        )
        job = service.create_enhancement_job(config, created_by='admin-1')
        assert job.status == JobStatus.QUEUED
        assert job.config.enhancement_type == etype


def test_create_job_with_target_quality(service):
    """Test job creation with target quality"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.NORMALIZATION,
        target_quality=0.9
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    assert job.config.target_quality == 0.9


def test_create_job_empty_data_id(service):
    """Test job creation fails with empty data_id"""
    config = EnhancementConfig(
        data_id='',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    with pytest.raises(ValueError, match="data_id is required"):
        service.create_enhancement_job(config, created_by='admin-1')


def test_create_job_empty_created_by(service):
    """Test job creation fails with empty created_by"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    with pytest.raises(ValueError, match="created_by is required"):
        service.create_enhancement_job(config, created_by='')


def test_create_job_invalid_target_quality(service):
    """Test job creation fails with out-of-range target quality"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT,
        target_quality=1.5
    )
    with pytest.raises(ValueError, match="target_quality must be between 0 and 1"):
        service.create_enhancement_job(config, created_by='admin-1')


# ============================================================================
# Test: Get Job Status
# ============================================================================

def test_get_job_status_queued(service):
    """Test getting status of a queued job"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    assert service.get_job_status(job.id) == JobStatus.QUEUED


def test_get_job_status_not_found(service):
    """Test getting status of non-existent job"""
    with pytest.raises(ValueError, match="not found"):
        service.get_job_status(str(uuid4()))


# ============================================================================
# Test: Apply Enhancement
# ============================================================================

def test_apply_enhancement_success(service, sample_content, db_session):
    """Test successful enhancement application"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    result = service.apply_enhancement(job.id, sample_content)

    assert result['original_data_id'] == 'data-123'
    assert result['enhancement_type'] == EnhancementType.QUALITY_IMPROVEMENT.value
    assert 0 < result['quality_overall'] <= 1
    assert result['quality_improvement'] > 0
    assert result['version'] == 1
    assert service.get_job_status(job.id) == JobStatus.COMPLETED


def test_apply_enhancement_all_types(service, sample_content):
    """Test applying each enhancement type"""
    for etype in EnhancementType:
        config = EnhancementConfig(
            data_id=f'data-{etype.value}',
            enhancement_type=etype
        )
        job = service.create_enhancement_job(config, created_by='admin-1')
        result = service.apply_enhancement(job.id, sample_content)

        assert result['enhancement_type'] == etype.value
        assert 0 < result['quality_overall'] <= 1


def test_apply_enhancement_stores_original(service, sample_content):
    """Test that original content is stored for rollback"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.NOISE_REDUCTION
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    service.apply_enhancement(job.id, sample_content)

    original = service.get_original_content(job.id)
    assert original == sample_content


def test_apply_enhancement_not_found(service, sample_content):
    """Test applying enhancement to non-existent job"""
    with pytest.raises(ValueError, match="not found"):
        service.apply_enhancement(str(uuid4()), sample_content)


def test_apply_enhancement_already_completed(service, sample_content):
    """Test applying enhancement to already completed job"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    service.apply_enhancement(job.id, sample_content)

    with pytest.raises(ValueError, match="Cannot apply enhancement"):
        service.apply_enhancement(job.id, sample_content)


def test_apply_enhancement_creates_version(service, sample_content, db_session):
    """Test that applying enhancement creates a version record"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.FEATURE_EXTRACTION
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    result = service.apply_enhancement(job.id, sample_content)

    versions = db_session.query(VersionModel).filter(
        VersionModel.data_id == result['id']
    ).all()
    assert len(versions) == 1


# ============================================================================
# Test: Validate Enhancement
# ============================================================================

def test_validate_enhancement_success(service, sample_content, db_session):
    """Test validation of valid enhanced data"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    result = service.apply_enhancement(job.id, sample_content)

    validation = service.validate_enhancement(result['id'])
    assert validation.valid is True
    assert len(validation.errors) == 0


def test_validate_enhancement_not_found(service):
    """Test validation fails for non-existent enhanced data"""
    with pytest.raises(ValueError, match="not found"):
        service.validate_enhancement(str(uuid4()))


# ============================================================================
# Test: Rollback Enhancement
# ============================================================================

def test_rollback_enhancement_success(service, sample_content, db_session):
    """Test successful enhancement rollback"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    result = service.apply_enhancement(job.id, sample_content)

    # Verify enhanced data exists (coerce str id for PGUUID bind consistency)
    rid = UUID(str(result['id']))
    enhanced = db_session.get(EnhancedDataModel, rid)
    assert enhanced is not None

    # Rollback
    service.rollback_enhancement(job.id)

    # Verify enhanced data is removed
    enhanced_after = db_session.get(EnhancedDataModel, rid)
    assert enhanced_after is None

    # Verify job status changed
    assert service.get_job_status(job.id) == JobStatus.CANCELLED

    # Verify original content still accessible
    original = service.get_original_content(job.id)
    assert original == sample_content


def test_rollback_not_completed(service):
    """Test rollback fails for non-completed job"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')

    with pytest.raises(ValueError, match="must be completed"):
        service.rollback_enhancement(job.id)


def test_rollback_not_found(service):
    """Test rollback fails for non-existent job"""
    with pytest.raises(ValueError, match="not found"):
        service.rollback_enhancement(str(uuid4()))



# ============================================================================
# Test: Enhancement Algorithms
# ============================================================================

def test_augmentation_algorithm(service, sample_content):
    """Test data augmentation creates augmented fields"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.DATA_AUGMENTATION,
        parameters={'multiplier': 2}
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    result = service.apply_enhancement(job.id, sample_content)

    content = result['content']
    assert 'title_augmented' in content
    assert '[augmented]' in content['title_augmented']
    assert '_augmentation_metadata' in content


def test_quality_improvement_algorithm(service):
    """Test quality improvement cleans content"""
    dirty_content = {
        'title': '  Messy   Title  ',
        'text': 'Some   text   with   spaces',
        'empty_field': '',
        'none_field': None,
        'nested': {'key': 'value', 'empty': ''}
    }
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    result = service.apply_enhancement(job.id, dirty_content)

    content = result['content']
    assert content['title'] == 'Messy Title'
    assert content['text'] == 'Some text with spaces'
    assert 'empty_field' not in content
    assert 'none_field' not in content


def test_noise_reduction_algorithm(service):
    """Test noise reduction removes noisy fields"""
    noisy_content = {
        'title': 'Good Title',
        'text': 'Good text',
        'temp_cache': 'noise',
        'debug_info': 'noise',
        '_tmp_data': 'noise'
    }
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.NOISE_REDUCTION
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    result = service.apply_enhancement(job.id, noisy_content)

    content = result['content']
    assert 'title' in content
    assert 'text' in content
    assert 'temp_cache' not in content
    assert 'debug_info' not in content
    assert '_tmp_data' not in content


def test_feature_extraction_algorithm(service, sample_content):
    """Test feature extraction creates feature fields"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.FEATURE_EXTRACTION
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    result = service.apply_enhancement(job.id, sample_content)

    content = result['content']
    assert 'title_word_count' in content
    assert 'title_char_count' in content
    assert 'tags_length' in content
    assert '_original_content' in content
    assert '_extraction_metadata' in content


def test_normalization_algorithm(service):
    """Test normalization normalizes field values"""
    raw_content = {
        'Title': 'Mixed Case Title',
        'Score': 3.14159,
        'Tags': ['zebra', 'apple', 'mango']
    }
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.NORMALIZATION,
        parameters={'case': 'lower', 'precision': 2}
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    result = service.apply_enhancement(job.id, raw_content)

    content = result['content']
    assert content['title'] == 'mixed case title'
    assert content['score'] == 3.14
    assert content['tags'] == ['apple', 'mango', 'zebra']


# ============================================================================
# Test: Audit Logging Integration
# ============================================================================

def test_audit_log_on_create(service, db_session):
    """Test audit log created on job creation"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')

    logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.resource_id == job.id,
        AuditLogModel.operation_type == OperationType.CREATE
    ).all()
    assert len(logs) >= 1
    create_log = next(
        (l for l in logs
         if l.details.get('action') == 'create_enhancement_job'),
        None
    )
    assert create_log is not None
    assert create_log.user_id == 'admin-1'


def test_audit_log_on_apply(service, sample_content, db_session):
    """Test audit log created on enhancement application"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    result = service.apply_enhancement(job.id, sample_content)

    logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.resource_id == result['id'],
        AuditLogModel.result == OperationResult.SUCCESS
    ).all()
    apply_log = next(
        (l for l in logs
         if l.details.get('action') == 'apply_enhancement'),
        None
    )
    assert apply_log is not None
    assert apply_log.details['quality_improvement'] > 0


def test_audit_log_on_rollback(service, sample_content, db_session):
    """Test audit log created on rollback"""
    config = EnhancementConfig(
        data_id='data-123',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    service.apply_enhancement(job.id, sample_content)
    service.rollback_enhancement(job.id)

    logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.operation_type == OperationType.DELETE
    ).all()
    rollback_log = next(
        (l for l in logs
         if l.details.get('action') == 'rollback_enhancement'),
        None
    )
    assert rollback_log is not None
    assert rollback_log.details['job_id'] == job.id


# ============================================================================
# Test: Add Enhanced Data to Sample Library
# ============================================================================


def _create_completed_job(service, sample_content):
    """Helper: create and complete an enhancement job, return (job, result)."""
    config = EnhancementConfig(
        data_id='data-original-1',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')
    result = service.apply_enhancement(job.id, sample_content)
    return job, result


def test_add_to_sample_library_success(service, sample_content, db_session):
    """Test adding enhanced data to sample library creates a valid sample."""
    job, enhanced = _create_completed_job(service, sample_content)

    sample = service.add_to_sample_library(job.id, user_id='admin-1')

    assert sample['data_id'] == enhanced['id']
    assert sample['category'] == 'enhanced'
    assert sample['quality_overall'] == enhanced['quality_overall']
    assert sample['quality_completeness'] == enhanced['quality_completeness']
    assert sample['quality_accuracy'] == enhanced['quality_accuracy']
    assert sample['quality_consistency'] == enhanced['quality_consistency']
    assert sample['version'] == 1
    assert 'enhanced' in sample['tags']

    # Verify persisted in DB (string cast avoids SQLite PGUUID bind issues after
    # long test runs in the same process).
    from src.models.data_lifecycle import SampleModel
    db_sample = db_session.query(SampleModel).filter(
        cast(SampleModel.id, String) == sample['id']
    ).first()
    assert db_sample is not None
    assert db_sample.data_id == enhanced['id']


def test_add_to_sample_library_traceability(service, sample_content, db_session):
    """Test that new sample links back to original data for traceability."""
    job, enhanced = _create_completed_job(service, sample_content)

    sample = service.add_to_sample_library(job.id, user_id='admin-1')

    meta = sample['metadata']
    assert meta['original_data_id'] == 'data-original-1'
    assert meta['enhancement_job_id'] == enhanced['enhancement_job_id']
    assert meta['enhancement_type'] == EnhancementType.QUALITY_IMPROVEMENT.value
    assert meta['iteration_count'] == 1


def test_add_to_sample_library_iteration_count(service, sample_content, db_session):
    """Test iteration count increments when original data already in library."""
    # First enhancement cycle
    job1, _ = _create_completed_job(service, sample_content)
    sample1 = service.add_to_sample_library(job1.id, user_id='admin-1')
    assert sample1['metadata']['iteration_count'] == 1

    # Second enhancement cycle on same original data
    config2 = EnhancementConfig(
        data_id='data-original-1',
        enhancement_type=EnhancementType.DATA_AUGMENTATION
    )
    job2 = service.create_enhancement_job(config2, created_by='admin-1')
    service.apply_enhancement(job2.id, sample_content)
    sample2 = service.add_to_sample_library(job2.id, user_id='admin-1')

    assert sample2['metadata']['iteration_count'] == 2


def test_add_to_sample_library_creates_version(service, sample_content, db_session):
    """Test that a version record is created for traceability."""
    from src.models.data_lifecycle import VersionModel

    job, _ = _create_completed_job(service, sample_content)
    sample = service.add_to_sample_library(job.id, user_id='admin-1')

    versions = db_session.query(VersionModel).filter(
        VersionModel.data_id == sample['id']
    ).all()
    assert len(versions) == 1
    assert versions[0].created_by == 'admin-1'
    assert 'iteration' in versions[0].description.lower()


def test_add_to_sample_library_creates_audit_log(service, sample_content, db_session):
    """Test that an audit log entry is created."""
    job, _ = _create_completed_job(service, sample_content)
    sample = service.add_to_sample_library(job.id, user_id='admin-1')

    logs = db_session.query(AuditLogModel).filter(
        AuditLogModel.resource_id == sample['id']
    ).all()
    transfer_log = next(
        (l for l in logs
         if l.details.get('action') == 'add_to_sample_library'),
        None
    )
    assert transfer_log is not None
    assert transfer_log.user_id == 'admin-1'
    assert transfer_log.details['original_data_id'] == 'data-original-1'


def test_add_to_sample_library_job_not_found(service):
    """Test error when job_id doesn't exist."""
    with pytest.raises(ValueError, match="not found"):
        service.add_to_sample_library('nonexistent', user_id='admin-1')


def test_add_to_sample_library_job_not_completed(service, sample_content):
    """Test error when job is not in completed state."""
    config = EnhancementConfig(
        data_id='data-1',
        enhancement_type=EnhancementType.QUALITY_IMPROVEMENT
    )
    job = service.create_enhancement_job(config, created_by='admin-1')

    with pytest.raises(ValueError, match="expected completed"):
        service.add_to_sample_library(job.id, user_id='admin-1')


def test_add_to_sample_library_empty_job_id(service):
    """Test error when job_id is empty."""
    with pytest.raises(ValueError, match="job_id is required"):
        service.add_to_sample_library('', user_id='admin-1')


def test_add_to_sample_library_empty_user_id(service, sample_content):
    """Test error when user_id is empty."""
    job, _ = _create_completed_job(service, sample_content)
    with pytest.raises(ValueError, match="user_id is required"):
        service.add_to_sample_library(job.id, user_id='')
