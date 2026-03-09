"""
Unit tests for Version Control Manager Service

Tests version creation, retrieval, comparison, rollback, tagging,
and checksum verification functionality.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.connection import Base
from src.models.data_lifecycle import VersionModel, ChangeType
from src.services.version_control_manager import VersionControlManager


# Test database setup
@pytest.fixture(scope='function')
def db_session():
    """Create an in-memory SQLite database for testing"""
    from sqlalchemy import Table, Column, String, Integer, DateTime, JSON, Text, MetaData
    from datetime import datetime
    
    engine = create_engine('sqlite:///:memory:')
    
    # Create a separate metadata for testing
    metadata = MetaData()
    
    # Create only the versions table for testing
    versions_table = Table(
        'versions',
        metadata,
        Column('id', String(36), primary_key=True, default=lambda: str(uuid4())),
        Column('data_id', String(255), nullable=False),
        Column('version_number', Integer, nullable=False),
        Column('content', JSON, nullable=False),
        Column('change_type', String(50), nullable=False),
        Column('description', Text, nullable=True),
        Column('parent_version_id', String(36), nullable=True),
        Column('checksum', String(64), nullable=False),
        Column('tags', JSON, nullable=False, default=list),
        Column('created_by', String(255), nullable=False),
        Column('created_at', DateTime, nullable=False, default=datetime.utcnow),
        Column('metadata', JSON, nullable=False, default=dict)
    )
    
    metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def version_manager(db_session):
    """Create a VersionControlManager instance"""
    return VersionControlManager(db_session)


@pytest.fixture
def sample_content():
    """Sample content for testing"""
    return {
        'title': 'Test Document',
        'sections': [
            {'heading': 'Introduction', 'content': 'This is a test'},
            {'heading': 'Body', 'content': 'Main content here'}
        ],
        'metadata': {
            'author': 'Test User',
            'tags': ['test', 'sample']
        }
    }


# ============================================================================
# Test: Create Version
# ============================================================================

def test_create_version_success(version_manager, sample_content):
    """Test creating a version successfully"""
    data_id = str(uuid4())
    
    version = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123',
        description='Initial version'
    )
    
    assert version is not None
    assert version.data_id == data_id
    assert version.version_number == 1
    assert version.content == sample_content
    assert version.change_type == ChangeType.INITIAL
    assert version.created_by == 'user123'
    assert version.description == 'Initial version'
    assert version.checksum is not None
    assert len(version.checksum) == 64  # SHA-256 hex length
    assert version.tags == []


def test_create_version_monotonic_increment(version_manager, sample_content):
    """Test that version numbers increase monotonically"""
    data_id = str(uuid4())
    
    # Create first version
    v1 = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    assert v1.version_number == 1
    
    # Create second version
    modified_content = sample_content.copy()
    modified_content['title'] = 'Modified Document'
    
    v2 = version_manager.create_version(
        data_id=data_id,
        content=modified_content,
        change_type=ChangeType.ANNOTATION,
        created_by='user123',
        parent_version_id=str(v1.id)
    )
    assert v2.version_number == 2
    
    # Create third version
    v3 = version_manager.create_version(
        data_id=data_id,
        content=modified_content,
        change_type=ChangeType.ENHANCEMENT,
        created_by='user456',
        parent_version_id=str(v2.id)
    )
    assert v3.version_number == 3


def test_create_version_with_parent(version_manager, sample_content):
    """Test creating a version with parent version tracking"""
    data_id = str(uuid4())
    
    # Create parent version
    parent = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    # Create child version
    child = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.ANNOTATION,
        created_by='user123',
        parent_version_id=str(parent.id)
    )
    
    assert child.parent_version_id == parent.id


def test_create_version_missing_data_id(version_manager, sample_content):
    """Test that creating version without data_id raises error"""
    with pytest.raises(ValueError, match="data_id is required"):
        version_manager.create_version(
            data_id='',
            content=sample_content,
            change_type=ChangeType.INITIAL,
            created_by='user123'
        )


def test_create_version_missing_content(version_manager):
    """Test that creating version without content raises error"""
    with pytest.raises(ValueError, match="content is required"):
        version_manager.create_version(
            data_id=str(uuid4()),
            content={},
            change_type=ChangeType.INITIAL,
            created_by='user123'
        )


def test_create_version_missing_created_by(version_manager, sample_content):
    """Test that creating version without created_by raises error"""
    with pytest.raises(ValueError, match="created_by is required"):
        version_manager.create_version(
            data_id=str(uuid4()),
            content=sample_content,
            change_type=ChangeType.INITIAL,
            created_by=''
        )


def test_create_version_invalid_parent(version_manager, sample_content):
    """Test that creating version with invalid parent raises error"""
    with pytest.raises(ValueError, match="Parent version .* not found"):
        version_manager.create_version(
            data_id=str(uuid4()),
            content=sample_content,
            change_type=ChangeType.ANNOTATION,
            created_by='user123',
            parent_version_id=str(uuid4())  # Non-existent parent
        )


def test_create_version_parent_different_data_id(version_manager, sample_content):
    """Test that parent version must belong to same data_id"""
    # Create parent for different data_id
    parent = version_manager.create_version(
        data_id=str(uuid4()),
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    # Try to create version with parent from different data_id
    with pytest.raises(ValueError, match="Parent version belongs to different data_id"):
        version_manager.create_version(
            data_id=str(uuid4()),  # Different data_id
            content=sample_content,
            change_type=ChangeType.ANNOTATION,
            created_by='user123',
            parent_version_id=str(parent.id)
        )


# ============================================================================
# Test: Get Version
# ============================================================================

def test_get_version_success(version_manager, sample_content):
    """Test retrieving a version by ID"""
    data_id = str(uuid4())
    
    created_version = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    retrieved_version = version_manager.get_version(str(created_version.id))
    
    assert retrieved_version is not None
    assert retrieved_version.id == created_version.id
    assert retrieved_version.data_id == data_id
    assert retrieved_version.content == sample_content


def test_get_version_not_found(version_manager):
    """Test retrieving non-existent version returns None"""
    version = version_manager.get_version(str(uuid4()))
    assert version is None


def test_get_version_invalid_id(version_manager):
    """Test retrieving version with invalid ID returns None"""
    version = version_manager.get_version('invalid-uuid')
    assert version is None


# ============================================================================
# Test: Get Version History
# ============================================================================

def test_get_version_history_success(version_manager, sample_content):
    """Test retrieving version history for a data item"""
    data_id = str(uuid4())
    
    # Create multiple versions
    v1 = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    v2 = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.ANNOTATION,
        created_by='user123'
    )
    
    v3 = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.ENHANCEMENT,
        created_by='user456'
    )
    
    # Get history
    history = version_manager.get_version_history(data_id)
    
    assert len(history) == 3
    # Should be ordered by version number descending (newest first)
    assert history[0].id == v3.id
    assert history[1].id == v2.id
    assert history[2].id == v1.id


def test_get_version_history_with_limit(version_manager, sample_content):
    """Test retrieving version history with limit"""
    data_id = str(uuid4())
    
    # Create 5 versions
    for i in range(5):
        version_manager.create_version(
            data_id=data_id,
            content=sample_content,
            change_type=ChangeType.INITIAL if i == 0 else ChangeType.ANNOTATION,
            created_by='user123'
        )
    
    # Get history with limit
    history = version_manager.get_version_history(data_id, limit=3)
    
    assert len(history) == 3
    # Should get the 3 most recent versions
    assert history[0].version_number == 5
    assert history[1].version_number == 4
    assert history[2].version_number == 3


def test_get_version_history_empty(version_manager):
    """Test retrieving version history for non-existent data returns empty list"""
    history = version_manager.get_version_history(str(uuid4()))
    assert history == []


# ============================================================================
# Test: Compare Versions
# ============================================================================

def test_compare_versions_success(version_manager):
    """Test comparing two versions"""
    data_id = str(uuid4())
    
    content1 = {
        'title': 'Original Title',
        'sections': [
            {'heading': 'Intro', 'content': 'Original content'}
        ]
    }
    
    content2 = {
        'title': 'Modified Title',
        'sections': [
            {'heading': 'Intro', 'content': 'Modified content'}
        ],
        'new_field': 'Added field'
    }
    
    v1 = version_manager.create_version(
        data_id=data_id,
        content=content1,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    v2 = version_manager.create_version(
        data_id=data_id,
        content=content2,
        change_type=ChangeType.ANNOTATION,
        created_by='user456'
    )
    
    diff = version_manager.compare_versions(str(v1.id), str(v2.id))
    
    assert diff is not None
    assert diff.version_id1 == v1.id
    assert diff.version_id2 == v2.id
    assert len(diff.changes) > 0
    assert diff.summary['data_id'] == data_id
    assert diff.summary['version1_number'] == 1
    assert diff.summary['version2_number'] == 2
    assert diff.summary['checksum_match'] is False


def test_compare_versions_identical(version_manager, sample_content):
    """Test comparing identical versions shows no changes"""
    data_id = str(uuid4())
    
    v1 = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    v2 = version_manager.create_version(
        data_id=data_id,
        content=sample_content,  # Same content
        change_type=ChangeType.ANNOTATION,
        created_by='user123'
    )
    
    diff = version_manager.compare_versions(str(v1.id), str(v2.id))
    
    assert len(diff.changes) == 0
    assert diff.summary['checksum_match'] is True


def test_compare_versions_not_found(version_manager, sample_content):
    """Test comparing with non-existent version raises error"""
    data_id = str(uuid4())
    
    v1 = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    with pytest.raises(ValueError, match="Version .* not found"):
        version_manager.compare_versions(str(v1.id), str(uuid4()))


def test_compare_versions_different_data_ids(version_manager, sample_content):
    """Test comparing versions from different data items raises error"""
    v1 = version_manager.create_version(
        data_id=str(uuid4()),
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    v2 = version_manager.create_version(
        data_id=str(uuid4()),  # Different data_id
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    with pytest.raises(ValueError, match="Versions belong to different data items"):
        version_manager.compare_versions(str(v1.id), str(v2.id))


# ============================================================================
# Test: Rollback to Version
# ============================================================================

def test_rollback_to_version_success(version_manager):
    """Test rolling back to a previous version"""
    data_id = str(uuid4())
    
    original_content = {'title': 'Original', 'value': 1}
    modified_content = {'title': 'Modified', 'value': 2}
    
    v1 = version_manager.create_version(
        data_id=data_id,
        content=original_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    v2 = version_manager.create_version(
        data_id=data_id,
        content=modified_content,
        change_type=ChangeType.ANNOTATION,
        created_by='user123'
    )
    
    # Rollback to v1
    rollback_version = version_manager.rollback_to_version(
        data_id=data_id,
        version_id=str(v1.id),
        rolled_back_by='admin',
        reason='Reverting bad changes'
    )
    
    assert rollback_version is not None
    assert rollback_version.version_number == 3  # New version created
    assert rollback_version.content == original_content  # Content from v1
    assert rollback_version.change_type == ChangeType.CORRECTION
    assert rollback_version.created_by == 'admin'
    assert 'Rolled back to version 1' in rollback_version.description
    assert 'Reverting bad changes' in rollback_version.description
    assert rollback_version.metadata_['rollback'] is True
    assert rollback_version.metadata_['target_version_number'] == 1


def test_rollback_to_version_not_found(version_manager):
    """Test rollback with non-existent version raises error"""
    with pytest.raises(ValueError, match="Version .* not found"):
        version_manager.rollback_to_version(
            data_id=str(uuid4()),
            version_id=str(uuid4()),
            rolled_back_by='admin'
        )


def test_rollback_to_version_different_data_id(version_manager, sample_content):
    """Test rollback to version from different data_id raises error"""
    v1 = version_manager.create_version(
        data_id=str(uuid4()),
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    with pytest.raises(ValueError, match="belongs to different data_id"):
        version_manager.rollback_to_version(
            data_id=str(uuid4()),  # Different data_id
            version_id=str(v1.id),
            rolled_back_by='admin'
        )


# ============================================================================
# Test: Tag Version
# ============================================================================

def test_tag_version_success(version_manager, sample_content):
    """Test adding a tag to a version"""
    data_id = str(uuid4())
    
    version = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    tagged_version = version_manager.tag_version(str(version.id), 'production')
    
    assert 'production' in tagged_version.tags


def test_tag_version_multiple_tags(version_manager, sample_content):
    """Test adding multiple tags to a version"""
    data_id = str(uuid4())
    
    version = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    version_manager.tag_version(str(version.id), 'stable')
    version_manager.tag_version(str(version.id), 'production')
    tagged_version = version_manager.tag_version(str(version.id), 'release-1.0')
    
    assert 'stable' in tagged_version.tags
    assert 'production' in tagged_version.tags
    assert 'release-1.0' in tagged_version.tags
    assert len(tagged_version.tags) == 3


def test_tag_version_duplicate_tag(version_manager, sample_content):
    """Test adding duplicate tag doesn't create duplicates"""
    data_id = str(uuid4())
    
    version = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    version_manager.tag_version(str(version.id), 'production')
    tagged_version = version_manager.tag_version(str(version.id), 'production')
    
    assert tagged_version.tags.count('production') == 1


def test_tag_version_empty_tag(version_manager, sample_content):
    """Test adding empty tag raises error"""
    data_id = str(uuid4())
    
    version = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    with pytest.raises(ValueError, match="Tag cannot be empty"):
        version_manager.tag_version(str(version.id), '')


def test_tag_version_not_found(version_manager):
    """Test tagging non-existent version raises error"""
    with pytest.raises(ValueError, match="Version .* not found"):
        version_manager.tag_version(str(uuid4()), 'production')


# ============================================================================
# Test: Verify Checksum
# ============================================================================

def test_verify_checksum_valid(version_manager, sample_content):
    """Test verifying a valid checksum"""
    data_id = str(uuid4())
    
    version = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    is_valid, error = version_manager.verify_checksum(str(version.id))
    
    assert is_valid is True
    assert error is None


def test_verify_checksum_not_found(version_manager):
    """Test verifying checksum for non-existent version"""
    is_valid, error = version_manager.verify_checksum(str(uuid4()))
    
    assert is_valid is False
    assert 'not found' in error


def test_verify_checksum_tampered(version_manager, sample_content, db_session):
    """Test verifying checksum detects tampering"""
    data_id = str(uuid4())
    
    version = version_manager.create_version(
        data_id=data_id,
        content=sample_content,
        change_type=ChangeType.INITIAL,
        created_by='user123'
    )
    
    # Tamper with content directly in database
    db_version = db_session.query(VersionModel).filter(
        VersionModel.id == version.id
    ).first()
    db_version.content = {'tampered': 'data'}
    db_session.commit()
    
    is_valid, error = version_manager.verify_checksum(str(version.id))
    
    assert is_valid is False
    assert 'Checksum mismatch' in error


# ============================================================================
# Test: Checksum Calculation
# ============================================================================

def test_checksum_deterministic(version_manager):
    """Test that checksum calculation is deterministic"""
    content = {
        'title': 'Test',
        'sections': [{'a': 1}, {'b': 2}],
        'metadata': {'key': 'value'}
    }
    
    checksum1 = version_manager._calculate_checksum(content)
    checksum2 = version_manager._calculate_checksum(content)
    
    assert checksum1 == checksum2


def test_checksum_different_for_different_content(version_manager):
    """Test that different content produces different checksums"""
    content1 = {'title': 'Test 1'}
    content2 = {'title': 'Test 2'}
    
    checksum1 = version_manager._calculate_checksum(content1)
    checksum2 = version_manager._calculate_checksum(content2)
    
    assert checksum1 != checksum2


def test_checksum_key_order_independent(version_manager):
    """Test that checksum is independent of key order"""
    content1 = {'a': 1, 'b': 2, 'c': 3}
    content2 = {'c': 3, 'a': 1, 'b': 2}
    
    checksum1 = version_manager._calculate_checksum(content1)
    checksum2 = version_manager._calculate_checksum(content2)
    
    assert checksum1 == checksum2


# ============================================================================
# Test: Diff Calculation
# ============================================================================

def test_diff_calculation_added_field(version_manager):
    """Test diff calculation detects added fields"""
    content1 = {'title': 'Test'}
    content2 = {'title': 'Test', 'new_field': 'value'}
    
    changes = version_manager._calculate_diff(content1, content2)
    
    assert len(changes) == 1
    assert changes[0]['type'] == 'added'
    assert changes[0]['path'] == 'new_field'
    assert changes[0]['new_value'] == 'value'


def test_diff_calculation_removed_field(version_manager):
    """Test diff calculation detects removed fields"""
    content1 = {'title': 'Test', 'old_field': 'value'}
    content2 = {'title': 'Test'}
    
    changes = version_manager._calculate_diff(content1, content2)
    
    assert len(changes) == 1
    assert changes[0]['type'] == 'removed'
    assert changes[0]['path'] == 'old_field'
    assert changes[0]['old_value'] == 'value'


def test_diff_calculation_modified_field(version_manager):
    """Test diff calculation detects modified fields"""
    content1 = {'title': 'Original'}
    content2 = {'title': 'Modified'}
    
    changes = version_manager._calculate_diff(content1, content2)
    
    assert len(changes) == 1
    assert changes[0]['type'] == 'modified'
    assert changes[0]['path'] == 'title'
    assert changes[0]['old_value'] == 'Original'
    assert changes[0]['new_value'] == 'Modified'


def test_diff_calculation_nested_changes(version_manager):
    """Test diff calculation handles nested structures"""
    content1 = {
        'metadata': {
            'author': 'John',
            'version': 1
        }
    }
    content2 = {
        'metadata': {
            'author': 'Jane',
            'version': 1
        }
    }
    
    changes = version_manager._calculate_diff(content1, content2)
    
    assert len(changes) == 1
    assert changes[0]['type'] == 'modified'
    assert changes[0]['path'] == 'metadata.author'
    assert changes[0]['old_value'] == 'John'
    assert changes[0]['new_value'] == 'Jane'


def test_diff_calculation_no_changes(version_manager):
    """Test diff calculation with identical content"""
    content = {'title': 'Test', 'value': 123}
    
    changes = version_manager._calculate_diff(content, content)
    
    assert len(changes) == 0
