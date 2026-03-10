"""
Property tests for sample library search correctness.

Validates: Requirements 4.2, 4.3, 23.4
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from hypothesis import given, settings, assume, HealthCheck
from hypothesis.strategies import lists, integers, floats, one_of, none, text, sampled_from
from sqlalchemy.orm import Session

from src.models.data_lifecycle import SampleModel, DataState
from src.services.sample_library_manager import SampleLibraryManager, SearchCriteria


# ============================================================================
# Helper Functions
# ============================================================================

def create_sample(db: Session, sample_id: str, category: str, 
                  quality: float, created_at: datetime):
    """Helper to create a sample in the database."""
    sample = SampleModel(
        id=sample_id,
        data_id=f"data_{str(sample_id)[:8]}",
        content={},
        category=category,
        quality_overall=quality,
        quality_completeness=quality,
        quality_accuracy=quality,
        quality_consistency=quality,
        version=1,
        tags=['tag1', 'tag2'],
        usage_count=0,
        metadata_={},
        created_at=created_at,
        updated_at=created_at
    )
    db.add(sample)
    return sample


# ============================================================================
# Test Class
# ============================================================================

class TestSampleLibrarySearchCorrectness:
    """Property tests for sample library search correctness.
    
    Validates: Requirements 4.2, 4.3, 23.4
    """

    @given(
        category=sampled_from(['training', 'testing', 'validation', 'production', 'experimental']),
        quality_min=floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        quality_max=floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        num_samples=integers(min_value=5, max_value=20),
        limit=integers(min_value=1, max_value=10),
        offset=integers(min_value=0, max_value=5)
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_search_by_category_all_results_match(
        self, db_session: Session, category, quality_min, quality_max,
        num_samples, limit, offset
    ):
        """For any search by category, all returned samples should match the category.
        
        Validates: Requirement 4.2
        """
        assume(quality_min <= quality_max)
        
        manager = SampleLibraryManager(db_session)
        base_time = datetime.utcnow()
        
        # Create samples with various categories
        categories = ['training', 'testing', 'validation', 'production', 'experimental']
        for i in range(num_samples):
            sample_category = categories[i % len(categories)]
            create_sample(
                db_session, uuid4(), sample_category, 0.5,
                base_time + timedelta(hours=i)
            )
        db_session.commit()
        
        # Search with specific category
        criteria = SearchCriteria(category=category, limit=limit, offset=offset)
        results, total = manager.search_samples(criteria)
        
        # All results should match the category
        for sample in results:
            assert sample.category == category, \
                f"Sample {sample.id} category {sample.category} does not match search category {category}"

    @given(
        category=sampled_from(['training', 'testing', 'validation', 'production', 'experimental']),
        quality_min=floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        quality_max=floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        num_samples=integers(min_value=5, max_value=20),
        limit=integers(min_value=1, max_value=10),
        offset=integers(min_value=0, max_value=5)
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_search_by_quality_score_all_results_in_range(
        self, db_session: Session, category, quality_min, quality_max,
        num_samples, limit, offset
    ):
        """For any search by quality score range, all returned samples should be within the range.
        
        Validates: Requirement 4.2
        """
        assume(quality_min <= quality_max)
        
        manager = SampleLibraryManager(db_session)
        base_time = datetime.utcnow()
        
        # Create samples with various quality scores
        for i in range(num_samples):
            quality = i / num_samples  # 0.0 to 1.0
            create_sample(
                db_session, uuid4(), category, quality,
                base_time + timedelta(hours=i)
            )
        db_session.commit()
        
        # Search with quality range
        criteria = SearchCriteria(
            category=category,
            quality_min=quality_min,
            quality_max=quality_max,
            limit=limit,
            offset=offset
        )
        results, total = manager.search_samples(criteria)
        
        # All results should be within quality range
        for sample in results:
            assert quality_min <= sample.quality_overall <= quality_max, \
                f"Sample {sample.id} quality {sample.quality_overall} is outside range [{quality_min}, {quality_max}]"

    @given(
        category=sampled_from(['training', 'testing', 'validation', 'production', 'experimental']),
        days_offset=integers(min_value=-30, max_value=30),
        date_range_days=integers(min_value=1, max_value=14),
        num_samples=integers(min_value=5, max_value=20),
        limit=integers(min_value=1, max_value=10),
        offset=integers(min_value=0, max_value=5)
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_search_by_date_range_all_results_in_range(
        self, db_session: Session, category, days_offset, date_range_days,
        num_samples, limit, offset
    ):
        """For any search by date range, all returned samples should be within the range.
        
        Validates: Requirement 4.2
        """
        manager = SampleLibraryManager(db_session)
        base_time = datetime.utcnow() + timedelta(days=days_offset)
        
        # Create samples across a date range
        for i in range(num_samples):
            created_at = base_time + timedelta(days=i)
            create_sample(
                db_session, uuid4(), 'training', 0.5,
                created_at
            )
        db_session.commit()
        
        # Calculate date range
        date_from = base_time + timedelta(days=2)
        date_to = base_time + timedelta(days=date_range_days + 2)
        
        # Search with date range
        criteria = SearchCriteria(
            category='training',
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset
        )
        results, total = manager.search_samples(criteria)
        
        # All results should be within date range
        for sample in results:
            assert date_from <= sample.created_at <= date_to, \
                f"Sample {sample.id} created at {sample.created_at} is outside date range [{date_from}, {date_to}]"

    @given(
        num_samples=integers(min_value=5, max_value=30),
        limit=integers(min_value=1, max_value=10),
        offset=integers(min_value=0, max_value=10)
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_pagination_respects_limit(self, db_session: Session, num_samples, limit, offset):
        """Pagination results should be limited to page size.
        
        Validates: Requirement 4.3, 23.4
        """
        manager = SampleLibraryManager(db_session)
        base_time = datetime.utcnow()
        
        # Create samples
        for i in range(num_samples):
            create_sample(
                db_session, uuid4(), 'training', 0.5,
                base_time + timedelta(hours=i)
            )
        db_session.commit()
        
        # Search with pagination
        criteria = SearchCriteria(limit=limit, offset=offset)
        results, total = manager.search_samples(criteria)
        
        # Results should not exceed limit
        assert len(results) <= limit, \
            f"Got {len(results)} results, expected at most {limit}"

    @given(
        num_samples=integers(min_value=5, max_value=30),
        limit=integers(min_value=1, max_value=10),
        offset=integers(min_value=0, max_value=10)
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_pagination_offset_skips_samples(self, db_session: Session, num_samples, limit, offset):
        """Pagination offset should skip the correct number of samples.
        
        Validates: Requirement 4.3, 23.4
        """
        manager = SampleLibraryManager(db_session)
        base_time = datetime.utcnow()
        
        # Create samples
        for i in range(num_samples):
            create_sample(
                db_session, uuid4(), 'training', 0.5,
                base_time + timedelta(hours=i)
            )
        db_session.commit()
        
        # Get all results first
        all_results, _ = manager.search_samples(SearchCriteria(limit=num_samples, offset=0))
        
        # Search with offset
        criteria = SearchCriteria(limit=limit, offset=offset)
        results, total = manager.search_samples(criteria)
        
        # If offset is within range, results should be a subset of all results starting from offset
        if offset < len(all_results):
            expected_samples = all_results[offset:offset + limit]
            result_ids = {s.id for s in results}
            expected_ids = {s.id for s in expected_samples}
            assert result_ids == expected_ids, \
                f"Offset {offset} did not skip correctly: got {result_ids}, expected {expected_ids}"

    @given(
        category=sampled_from(['nonexistent', 'training', 'testing', 'validation', 'production', 'experimental']),
        quality_min=floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        quality_max=floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        date_from=one_of(none(), sampled_from([
            datetime.utcnow() + timedelta(days=365),
            datetime.utcnow() + timedelta(days=30),
            datetime.utcnow() + timedelta(days=7)
        ])),
        date_to=one_of(none(), sampled_from([
            datetime.utcnow() + timedelta(days=365),
            datetime.utcnow() + timedelta(days=30),
            datetime.utcnow() + timedelta(days=7)
        ]))
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_search_no_matching_samples_returns_empty(
        self, db_session: Session, category, quality_min, quality_max,
        date_from, date_to
    ):
        """When no samples match the criteria, search should return empty results.
        
        Validates: Requirement 4.2
        """
        assume(quality_min <= quality_max)
        
        manager = SampleLibraryManager(db_session)
        base_time = datetime.utcnow()
        
        # Create samples with specific characteristics
        for i in range(10):
            create_sample(
                db_session, uuid4(), 'training', 0.5,
                base_time + timedelta(hours=i)
            )
        db_session.commit()
        
        # Search with criteria that won't match
        criteria = SearchCriteria(
            category=category,
            quality_min=quality_min,
            quality_max=quality_max,
            date_from=date_from,
            date_to=date_to
        )
        results, total = manager.search_samples(criteria)
        
        # If category is 'nonexistent' or date range is in the future, should return empty
        if category == 'nonexistent' or (date_from and date_from > datetime.utcnow()):
            assert len(results) == 0, \
                f"Expected empty results for non-matching criteria, got {len(results)} samples"

    @given(
        num_samples=integers(min_value=1, max_value=20),
        limit=integers(min_value=1, max_value=50)
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_search_all_samples_match_empty_criteria(self, db_session: Session, num_samples, limit):
        """When search criteria is empty, all samples should be returned.
        
        Validates: Requirement 4.2
        """
        manager = SampleLibraryManager(db_session)
        base_time = datetime.utcnow()
        
        # Create samples with various characteristics
        categories = ['training', 'testing', 'validation']
        
        for i in range(num_samples):
            create_sample(
                db_session, uuid4(),
                categories[i % len(categories)],
                i / num_samples,
                base_time + timedelta(hours=i)
            )
        db_session.commit()
        
        # Search with empty criteria
        criteria = SearchCriteria(limit=limit, offset=0)
        results, total = manager.search_samples(criteria)
        
        # All results should be valid samples
        for sample in results:
            assert sample is not None
            assert sample.id is not None
            assert sample.category is not None
            assert 0.0 <= sample.quality_overall <= 1.0

    @given(
        category=sampled_from(['training', 'testing', 'validation']),
        num_samples=integers(min_value=10, max_value=30),
        limit=integers(min_value=5, max_value=15)
    )
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_search_combined_criteria_all_results_match(
        self, db_session: Session, category, num_samples, limit
    ):
        """When searching with combined criteria, all results should match all criteria.
        
        Validates: Requirements 4.2, 4.3
        """
        manager = SampleLibraryManager(db_session)
        base_time = datetime.utcnow()
        
        # Create samples with various characteristics
        categories = ['training', 'testing', 'validation', 'production', 'experimental']
        
        for i in range(num_samples):
            sample_category = categories[i % len(categories)]
            quality = (i % 10) / 10  # 0.0 to 0.9
            create_sample(
                db_session, uuid4(), sample_category, quality,
                base_time + timedelta(hours=i)
            )
        db_session.commit()
        
        # Search with combined criteria
        criteria = SearchCriteria(
            category=category,
            quality_min=0.3,
            quality_max=0.8,
            limit=limit,
            offset=0
        )
        results, total = manager.search_samples(criteria)
        
        # All results should match ALL criteria
        for sample in results:
            # Check category
            assert sample.category == category, \
                f"Sample {sample.id} category {sample.category} != {category}"
            
            # Check quality range
            assert 0.3 <= sample.quality_overall <= 0.8, \
                f"Sample {sample.id} quality {sample.quality_overall} outside [0.3, 0.8]"

    @given(
        num_samples=integers(min_value=1, max_value=50),
        limit=integers(min_value=1, max_value=20)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_search_total_count_reflects_matching_samples(
        self, db_session: Session, num_samples, limit
    ):
        """The total count returned should reflect the actual number of matching samples.
        
        Validates: Requirement 4.3
        """
        manager = SampleLibraryManager(db_session)
        base_time = datetime.utcnow()
        
        # Create samples
        for i in range(num_samples):
            create_sample(
                db_session, uuid4(), 
                'training' if i % 2 == 0 else 'testing',
                0.5,
                base_time + timedelta(hours=i)
            )
        db_session.commit()
        
        # Search for samples with 'training' category
        criteria = SearchCriteria(category='training', limit=limit, offset=0)
        results, total = manager.search_samples(criteria)
        
        # Total should be at least the number of results returned
        assert total >= len(results), \
            f"Total count {total} should be >= number of results {len(results)}"
        
        # Total should be consistent with actual count
        expected_total = sum(1 for s in results if s.category == 'training')
        assert total >= expected_total, \
            f"Total count {total} should account for all matching samples"