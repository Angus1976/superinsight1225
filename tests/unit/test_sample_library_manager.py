"""
Unit tests for Sample Library Manager Service
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, MagicMock

from src.models.data_lifecycle import Base, SampleModel, ChangeType
from src.services.sample_library_manager import (
    SampleLibraryManager,
    SearchCriteria
)


@pytest.fixture
def db_session():
    """In-memory SQLite with the real ``SampleModel`` schema (UUID + constraints)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # Only ``samples`` — full ``Base.metadata`` may include PG-only types from other imports.
    Base.metadata.create_all(engine, tables=[SampleModel.__table__])
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def manager(db_session):
    """Create a SampleLibraryManager instance"""
    return SampleLibraryManager(db_session)


@pytest.fixture
def mock_version_control():
    """Create a mock VersionControlManager"""
    mock = Mock()
    mock.create_version = Mock(return_value=Mock(id=uuid4(), version_number=1))
    return mock


@pytest.fixture
def manager_with_version_control(db_session, mock_version_control):
    """Create a SampleLibraryManager instance with version control"""
    return SampleLibraryManager(db_session, mock_version_control)


@pytest.fixture
def sample_data():
    """Sample test data"""
    return {
        'data_id': str(uuid4()),
        'content': {'title': 'Test Sample', 'body': 'Sample content'},
        'category': 'test',
        'quality_overall': 0.85,
        'quality_completeness': 0.9,
        'quality_accuracy': 0.8,
        'quality_consistency': 0.85,
        'tags': ['tag1', 'tag2'],
        'metadata': {'source': 'test'}
    }


class TestAddSample:
    """Tests for add_sample method"""
    
    def test_add_sample_success(self, manager, sample_data):
        """Test successfully adding a sample"""
        sample = manager.add_sample(**sample_data)
        
        assert sample.id is not None
        assert sample.data_id == sample_data['data_id']
        assert sample.content == sample_data['content']
        assert sample.category == sample_data['category']
        assert sample.quality_overall == sample_data['quality_overall']
        assert sample.tags == sample_data['tags']
        assert sample.usage_count == 0
        assert sample.last_used_at is None
        assert sample.version == 1
    
    def test_add_sample_with_defaults(self, manager):
        """Test adding a sample with default quality scores"""
        sample = manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 'data'},
            category='default'
        )
        
        assert sample.quality_overall == 0.8
        assert sample.quality_completeness == 0.8
        assert sample.quality_accuracy == 0.8
        assert sample.quality_consistency == 0.8
        assert sample.tags == []
        assert sample.metadata_ == {}
    
    def test_add_sample_invalid_quality_score(self, manager):
        """Test adding a sample with invalid quality score"""
        with pytest.raises(ValueError, match="quality_overall must be between 0 and 1"):
            manager.add_sample(
                data_id=str(uuid4()),
                content={'test': 'data'},
                category='test',
                quality_overall=1.5
            )
        
        with pytest.raises(ValueError, match="quality_completeness must be between 0 and 1"):
            manager.add_sample(
                data_id=str(uuid4()),
                content={'test': 'data'},
                category='test',
                quality_completeness=-0.1
            )
    
    def test_add_sample_missing_required_fields(self, manager):
        """Test adding a sample with missing required fields"""
        with pytest.raises(ValueError, match="data_id is required"):
            manager.add_sample(
                data_id='',
                content={'test': 'data'},
                category='test'
            )
        
        with pytest.raises(ValueError, match="content is required"):
            manager.add_sample(
                data_id=str(uuid4()),
                content={},
                category='test'
            )
        
        with pytest.raises(ValueError, match="category is required"):
            manager.add_sample(
                data_id=str(uuid4()),
                content={'test': 'data'},
                category=''
            )


class TestGetSample:
    """Tests for get_sample method"""
    
    def test_get_sample_success(self, manager, sample_data):
        """Test successfully retrieving a sample"""
        created_sample = manager.add_sample(**sample_data)
        
        retrieved_sample = manager.get_sample(str(created_sample.id))
        
        assert retrieved_sample is not None
        assert retrieved_sample.id == created_sample.id
        assert retrieved_sample.data_id == sample_data['data_id']
        assert retrieved_sample.content == sample_data['content']
    
    def test_get_sample_not_found(self, manager):
        """Test retrieving a non-existent sample"""
        sample = manager.get_sample(str(uuid4()))
        assert sample is None
    
    def test_get_sample_invalid_uuid(self, manager):
        """Test retrieving with invalid UUID"""
        sample = manager.get_sample('invalid-uuid')
        assert sample is None


class TestSearchSamples:
    """Tests for search_samples method"""
    
    def test_search_all_samples(self, manager):
        """Test searching without filters returns all samples"""
        # Create multiple samples
        for i in range(5):
            manager.add_sample(
                data_id=str(uuid4()),
                content={'index': i},
                category='test'
            )
        
        criteria = SearchCriteria()
        samples, total = manager.search_samples(criteria)
        
        assert len(samples) == 5
        assert total == 5
    
    def test_search_by_category(self, manager):
        """Test searching by category"""
        # Create samples with different categories
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 1},
            category='category_a'
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 2},
            category='category_b'
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 3},
            category='category_a'
        )
        
        criteria = SearchCriteria(category='category_a')
        samples, total = manager.search_samples(criteria)
        
        assert len(samples) == 2
        assert total == 2
        assert all(s.category == 'category_a' for s in samples)
    
    def test_search_by_quality_range(self, manager):
        """Test searching by quality score range"""
        # Create samples with different quality scores
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 1},
            category='test',
            quality_overall=0.5
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 2},
            category='test',
            quality_overall=0.75
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 3},
            category='test',
            quality_overall=0.9
        )
        
        criteria = SearchCriteria(quality_min=0.7, quality_max=0.85)
        samples, total = manager.search_samples(criteria)
        
        assert len(samples) == 1
        assert total == 1
        assert samples[0].quality_overall == 0.75
    
    def test_search_by_date_range(self, manager):
        """Test searching by date range"""
        now = datetime.utcnow()
        
        # Create samples with different timestamps
        sample1 = manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 1},
            category='test'
        )
        sample1.created_at = now - timedelta(days=10)
        manager.db.commit()
        
        sample2 = manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 2},
            category='test'
        )
        sample2.created_at = now - timedelta(days=5)
        manager.db.commit()
        
        sample3 = manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 3},
            category='test'
        )
        sample3.created_at = now
        manager.db.commit()
        
        criteria = SearchCriteria(
            date_from=now - timedelta(days=7),
            date_to=now
        )
        samples, total = manager.search_samples(criteria)
        
        assert len(samples) == 2
        assert total == 2
    
    def test_search_by_tags(self, manager):
        """Test searching by tags"""
        # Create samples with different tags
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 1},
            category='test',
            tags=['tag1', 'tag2']
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 2},
            category='test',
            tags=['tag2', 'tag3']
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 3},
            category='test',
            tags=['tag1', 'tag2', 'tag3']
        )
        
        # Search for samples with both tag1 and tag2
        criteria = SearchCriteria(tags=['tag1', 'tag2'])
        samples, total = manager.search_samples(criteria)
        
        assert len(samples) == 2
        assert total == 2
    
    def test_search_with_pagination(self, manager):
        """Test pagination in search results"""
        # Create 10 samples
        for i in range(10):
            manager.add_sample(
                data_id=str(uuid4()),
                content={'index': i},
                category='test'
            )
        
        # Get first page
        criteria = SearchCriteria(limit=3, offset=0)
        samples, total = manager.search_samples(criteria)
        
        assert len(samples) == 3
        assert total == 10
        
        # Get second page
        criteria = SearchCriteria(limit=3, offset=3)
        samples, total = manager.search_samples(criteria)
        
        assert len(samples) == 3
        assert total == 10
    
    def test_search_combined_filters(self, manager):
        """Test searching with multiple filters combined"""
        # Create diverse samples
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 1},
            category='category_a',
            quality_overall=0.8,
            tags=['tag1']
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 2},
            category='category_a',
            quality_overall=0.9,
            tags=['tag1', 'tag2']
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 3},
            category='category_b',
            quality_overall=0.85,
            tags=['tag1']
        )
        
        criteria = SearchCriteria(
            category='category_a',
            quality_min=0.85,
            tags=['tag1']
        )
        samples, total = manager.search_samples(criteria)
        
        assert len(samples) == 1
        assert total == 1
        assert samples[0].category == 'category_a'
        assert samples[0].quality_overall == 0.9


class TestUpdateSample:
    """Tests for update_sample method"""
    
    def test_update_sample_tags(self, manager, sample_data):
        """Test updating sample tags"""
        sample = manager.add_sample(**sample_data)
        
        updated_sample = manager.update_sample(
            str(sample.id),
            {'tags': ['new_tag1', 'new_tag2']}
        )
        
        assert updated_sample.tags == ['new_tag1', 'new_tag2']
    
    def test_update_sample_category(self, manager, sample_data):
        """Test updating sample category"""
        sample = manager.add_sample(**sample_data)
        
        updated_sample = manager.update_sample(
            str(sample.id),
            {'category': 'new_category'}
        )
        
        assert updated_sample.category == 'new_category'
    
    def test_update_sample_quality_scores(self, manager, sample_data):
        """Test updating quality scores"""
        sample = manager.add_sample(**sample_data)
        
        updated_sample = manager.update_sample(
            str(sample.id),
            {
                'quality_overall': 0.95,
                'quality_completeness': 0.98
            }
        )
        
        assert updated_sample.quality_overall == 0.95
        assert updated_sample.quality_completeness == 0.98
    
    def test_update_sample_metadata(self, manager, sample_data):
        """Test updating sample metadata"""
        sample = manager.add_sample(**sample_data)
        
        new_metadata = {'updated': True, 'version': 2}
        updated_sample = manager.update_sample(
            str(sample.id),
            {'metadata_': new_metadata}
        )
        
        assert updated_sample.metadata_ == new_metadata
    
    def test_update_sample_not_found(self, manager):
        """Test updating a non-existent sample"""
        with pytest.raises(ValueError, match="Sample .* not found"):
            manager.update_sample(
                str(uuid4()),
                {'tags': ['new_tag']}
            )
    
    def test_update_sample_invalid_field(self, manager, sample_data):
        """Test updating with invalid field"""
        sample = manager.add_sample(**sample_data)
        
        with pytest.raises(ValueError, match="Field 'id' cannot be updated"):
            manager.update_sample(
                str(sample.id),
                {'id': uuid4()}
            )
    
    def test_update_sample_invalid_quality_score(self, manager, sample_data):
        """Test updating with invalid quality score"""
        sample = manager.add_sample(**sample_data)
        
        with pytest.raises(ValueError, match="quality_overall must be between 0 and 1"):
            manager.update_sample(
                str(sample.id),
                {'quality_overall': 1.5}
            )
    
    def test_update_sample_with_version_control(self, manager_with_version_control, sample_data, mock_version_control):
        """Test updating sample creates version when version control is enabled"""
        sample = manager_with_version_control.add_sample(**sample_data)
        
        updated_sample = manager_with_version_control.update_sample(
            str(sample.id),
            {'tags': ['new_tag1', 'new_tag2']},
            updated_by='user123'
        )
        
        assert updated_sample.tags == ['new_tag1', 'new_tag2']
        
        # Verify version was created
        mock_version_control.create_version.assert_called_once()
        call_args = mock_version_control.create_version.call_args
        
        assert call_args[1]['data_id'] == sample.data_id
        assert call_args[1]['change_type'] == ChangeType.CORRECTION
        assert call_args[1]['created_by'] == 'user123'
        assert 'tags' in call_args[1]['description']
        assert call_args[1]['metadata']['sample_id'] == str(sample.id)
        assert 'tags' in call_args[1]['metadata']['updated_fields']
    
    def test_update_sample_without_version_control(self, manager, sample_data):
        """Test updating sample without version control manager"""
        sample = manager.add_sample(**sample_data)
        
        # Should work without version control
        updated_sample = manager.update_sample(
            str(sample.id),
            {'tags': ['new_tag1', 'new_tag2']},
            updated_by='user123'
        )
        
        assert updated_sample.tags == ['new_tag1', 'new_tag2']
    
    def test_update_sample_without_updated_by(self, manager_with_version_control, sample_data, mock_version_control):
        """Test updating sample without updated_by does not create version"""
        sample = manager_with_version_control.add_sample(**sample_data)
        
        updated_sample = manager_with_version_control.update_sample(
            str(sample.id),
            {'tags': ['new_tag1', 'new_tag2']}
        )
        
        assert updated_sample.tags == ['new_tag1', 'new_tag2']
        
        # Verify version was NOT created
        mock_version_control.create_version.assert_not_called()


class TestDeleteSample:
    """Tests for delete_sample method"""
    
    def test_delete_sample_success(self, manager, sample_data):
        """Test successfully deleting a sample"""
        sample = manager.add_sample(**sample_data)
        sample_id = str(sample.id)
        
        manager.delete_sample(sample_id)
        
        # Verify sample is deleted
        deleted_sample = manager.get_sample(sample_id)
        assert deleted_sample is None
    
    def test_delete_sample_not_found(self, manager):
        """Test deleting a non-existent sample"""
        with pytest.raises(ValueError, match="Sample .* not found"):
            manager.delete_sample(str(uuid4()))


class TestGetSamplesByTag:
    """Tests for get_samples_by_tag method"""
    
    def test_get_samples_by_single_tag(self, manager):
        """Test getting samples by a single tag"""
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 1},
            category='test',
            tags=['tag1', 'tag2']
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 2},
            category='test',
            tags=['tag2', 'tag3']
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 3},
            category='test',
            tags=['tag1']
        )
        
        samples = manager.get_samples_by_tag(['tag1'])
        
        assert len(samples) == 2
        assert all('tag1' in s.tags for s in samples)
    
    def test_get_samples_by_multiple_tags(self, manager):
        """Test getting samples by multiple tags (AND logic)"""
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 1},
            category='test',
            tags=['tag1', 'tag2', 'tag3']
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 2},
            category='test',
            tags=['tag1', 'tag2']
        )
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 3},
            category='test',
            tags=['tag1']
        )
        
        samples = manager.get_samples_by_tag(['tag1', 'tag2'])
        
        assert len(samples) == 2
        assert all('tag1' in s.tags and 'tag2' in s.tags for s in samples)
    
    def test_get_samples_by_tag_empty_list(self, manager):
        """Test getting samples with empty tag list"""
        samples = manager.get_samples_by_tag([])
        assert len(samples) == 0
    
    def test_get_samples_by_tag_no_matches(self, manager):
        """Test getting samples with tag that doesn't exist"""
        manager.add_sample(
            data_id=str(uuid4()),
            content={'test': 1},
            category='test',
            tags=['tag1']
        )
        
        samples = manager.get_samples_by_tag(['nonexistent_tag'])
        assert len(samples) == 0


class TestTrackUsage:
    """Tests for track_usage method"""
    
    def test_track_usage_increments_count(self, manager, sample_data):
        """Test that tracking usage increments usage count"""
        sample = manager.add_sample(**sample_data)
        sample_id = str(sample.id)
        
        assert sample.usage_count == 0
        assert sample.last_used_at is None
        
        manager.track_usage(sample_id)
        
        updated_sample = manager.get_sample(sample_id)
        assert updated_sample.usage_count == 1
        assert updated_sample.last_used_at is not None
    
    def test_track_usage_multiple_times(self, manager, sample_data):
        """Test tracking usage multiple times"""
        sample = manager.add_sample(**sample_data)
        sample_id = str(sample.id)
        
        # Track usage 3 times
        for _ in range(3):
            manager.track_usage(sample_id)
        
        updated_sample = manager.get_sample(sample_id)
        assert updated_sample.usage_count == 3
    
    def test_track_usage_updates_timestamp(self, manager, sample_data):
        """Test that tracking usage updates last_used_at timestamp"""
        sample = manager.add_sample(**sample_data)
        sample_id = str(sample.id)
        
        manager.track_usage(sample_id)
        first_timestamp = manager.get_sample(sample_id).last_used_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        manager.track_usage(sample_id)
        second_timestamp = manager.get_sample(sample_id).last_used_at
        
        assert second_timestamp > first_timestamp
    
    def test_track_usage_not_found(self, manager):
        """Test tracking usage for non-existent sample"""
        with pytest.raises(ValueError, match="Sample .* not found"):
            manager.track_usage(str(uuid4()))
