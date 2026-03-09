"""
Property-Based Tests for Sample Library Search Correctness

Tests Property 7: Sample Library Search Correctness

**Validates: Requirements 4.2, 4.3, 23.4**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session

from src.models.data_lifecycle import SampleModel
from src.services.sample_library_manager import (
    SampleLibraryManager,
    SearchCriteria
)
from tests.conftest import db_session


# ============================================================================
# Test Strategies
# ============================================================================

# Strategy for generating categories
category_strategy = st.sampled_from([
    'medical', 'legal', 'financial', 'technical', 'general'
])

# Strategy for generating tags (lists of 0-5 tags)
tag_strategy = st.sampled_from([
    'important', 'urgent', 'reviewed', 'high-quality', 'verified',
    'draft', 'final', 'archived', 'public', 'private'
])

tags_list_strategy = st.lists(tag_strategy, min_size=0, max_size=5, unique=True)

# Strategy for generating quality scores (0.0 to 1.0)
quality_score_strategy = st.floats(min_value=0.0, max_value=1.0)

# Strategy for generating dates (within last 365 days)
def date_strategy():
    base_date = datetime.utcnow()
    return st.datetimes(
        min_value=base_date - timedelta(days=365),
        max_value=base_date
    )

# Strategy for generating sample content
content_strategy = st.fixed_dictionaries({
    'title': st.text(min_size=1, max_size=100),
    'body': st.text(min_size=1, max_size=500)
})


# ============================================================================
# Helper Functions
# ============================================================================

def create_sample(
    db: Session,
    category: str,
    tags: list,
    quality_overall: float,
    created_at: datetime
) -> SampleModel:
    """Create a sample with specified attributes"""
    sample = SampleModel(
        id=uuid4(),
        data_id=str(uuid4()),
        content={'test': 'data', 'value': 'content'},
        category=category,
        quality_overall=quality_overall,
        quality_completeness=quality_overall,
        quality_accuracy=quality_overall,
        quality_consistency=quality_overall,
        version=1,
        tags=tags,
        usage_count=0,
        last_used_at=None,
        metadata_={},
        created_at=created_at,
        updated_at=created_at
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)
    return sample


def sample_matches_criteria(sample: SampleModel, criteria: SearchCriteria) -> bool:
    """Check if a sample matches all search criteria"""
    # Category filter
    if criteria.category and sample.category != criteria.category:
        return False
    
    # Quality min filter
    if criteria.quality_min is not None and sample.quality_overall < criteria.quality_min:
        return False
    
    # Quality max filter
    if criteria.quality_max is not None and sample.quality_overall > criteria.quality_max:
        return False
    
    # Date from filter
    if criteria.date_from and sample.created_at < criteria.date_from:
        return False
    
    # Date to filter
    if criteria.date_to and sample.created_at > criteria.date_to:
        return False
    
    # Tags filter (sample must have ALL specified tags)
    if criteria.tags:
        sample_tags_set = set(sample.tags)
        for tag in criteria.tags:
            if tag not in sample_tags_set:
                return False
    
    return True


# ============================================================================
# Property 7: Sample Library Search Correctness
# **Validates: Requirements 4.2, 4.3, 23.4**
# ============================================================================

@pytest.mark.property
class TestSampleLibrarySearchCorrectness:
    """
    Property 7: Sample Library Search Correctness
    
    For any search criteria (tags, category, quality range, date range),
    all returned samples must match ALL specified criteria. This ensures
    search filtering is accurate and complete.
    """
    
    @given(
        category=category_strategy,
        search_category=st.one_of(st.none(), category_strategy)
    )
    @settings(max_examples=30, deadline=None)
    def test_category_filter_correctness(
        self,
        db_session: Session,
        category: str,
        search_category: str
    ):
        """
        Property: Category filter returns only matching samples.
        
        For any category filter, all returned samples must have exactly
        that category.
        """
        # Create samples with different categories
        manager = SampleLibraryManager(db_session)
        
        # Create sample with target category
        sample1 = create_sample(
            db_session,
            category=category,
            tags=[],
            quality_overall=0.8,
            created_at=datetime.utcnow()
        )
        
        # Create sample with different category
        other_category = 'medical' if category != 'medical' else 'legal'
        sample2 = create_sample(
            db_session,
            category=other_category,
            tags=[],
            quality_overall=0.8,
            created_at=datetime.utcnow()
        )
        
        # Search with category filter
        criteria = SearchCriteria(category=search_category)
        results, total = manager.search_samples(criteria)
        
        # Assert: All results match the category filter
        for sample in results:
            if search_category:
                assert sample.category == search_category, (
                    f"Sample {sample.id} has category '{sample.category}', "
                    f"but search was for category '{search_category}'"
                )
    
    @given(
        quality_overall=quality_score_strategy,
        quality_min=st.one_of(st.none(), quality_score_strategy),
        quality_max=st.one_of(st.none(), quality_score_strategy)
    )
    @settings(max_examples=30, deadline=None)
    def test_quality_range_filter_correctness(
        self,
        db_session: Session,
        quality_overall: float,
        quality_min: float,
        quality_max: float
    ):
        """
        Property: Quality range filter returns only samples within range.
        
        For any quality_min and quality_max, all returned samples must have
        quality_overall >= quality_min and <= quality_max.
        """
        # Ensure quality_min <= quality_max if both are specified
        if quality_min is not None and quality_max is not None:
            assume(quality_min <= quality_max)
        
        # Create sample
        manager = SampleLibraryManager(db_session)
        sample = create_sample(
            db_session,
            category='test',
            tags=[],
            quality_overall=quality_overall,
            created_at=datetime.utcnow()
        )
        
        # Search with quality range filter
        criteria = SearchCriteria(
            quality_min=quality_min,
            quality_max=quality_max
        )
        results, total = manager.search_samples(criteria)
        
        # Assert: All results are within quality range
        for result_sample in results:
            if quality_min is not None:
                assert result_sample.quality_overall >= quality_min, (
                    f"Sample {result_sample.id} has quality {result_sample.quality_overall}, "
                    f"but quality_min is {quality_min}"
                )
            if quality_max is not None:
                assert result_sample.quality_overall <= quality_max, (
                    f"Sample {result_sample.id} has quality {result_sample.quality_overall}, "
                    f"but quality_max is {quality_max}"
                )
    
    @given(
        sample_tags=tags_list_strategy,
        search_tags=tags_list_strategy
    )
    @settings(max_examples=30, deadline=None)
    def test_tags_filter_correctness(
        self,
        db_session: Session,
        sample_tags: list,
        search_tags: list
    ):
        """
        Property: Tags filter returns only samples with ALL specified tags.
        
        For any list of search tags, all returned samples must contain
        ALL of those tags (not just some).
        """
        # Skip if no search tags (no filter to test)
        assume(len(search_tags) > 0)
        
        # Create sample
        manager = SampleLibraryManager(db_session)
        sample = create_sample(
            db_session,
            category='test',
            tags=sample_tags,
            quality_overall=0.8,
            created_at=datetime.utcnow()
        )
        
        # Search with tags filter
        criteria = SearchCriteria(tags=search_tags)
        results, total = manager.search_samples(criteria)
        
        # Assert: All results have ALL search tags
        for result_sample in results:
            result_tags_set = set(result_sample.tags)
            for search_tag in search_tags:
                assert search_tag in result_tags_set, (
                    f"Sample {result_sample.id} has tags {result_sample.tags}, "
                    f"but is missing required tag '{search_tag}'"
                )
    
    @given(
        created_at=date_strategy(),
        date_from=st.one_of(st.none(), date_strategy()),
        date_to=st.one_of(st.none(), date_strategy())
    )
    @settings(max_examples=30, deadline=None)
    def test_date_range_filter_correctness(
        self,
        db_session: Session,
        created_at: datetime,
        date_from: datetime,
        date_to: datetime
    ):
        """
        Property: Date range filter returns only samples within range.
        
        For any date_from and date_to, all returned samples must have
        created_at >= date_from and <= date_to.
        """
        # Ensure date_from <= date_to if both are specified
        if date_from is not None and date_to is not None:
            assume(date_from <= date_to)
        
        # Create sample
        manager = SampleLibraryManager(db_session)
        sample = create_sample(
            db_session,
            category='test',
            tags=[],
            quality_overall=0.8,
            created_at=created_at
        )
        
        # Search with date range filter
        criteria = SearchCriteria(
            date_from=date_from,
            date_to=date_to
        )
        results, total = manager.search_samples(criteria)
        
        # Assert: All results are within date range
        for result_sample in results:
            if date_from is not None:
                assert result_sample.created_at >= date_from, (
                    f"Sample {result_sample.id} created at {result_sample.created_at}, "
                    f"but date_from is {date_from}"
                )
            if date_to is not None:
                assert result_sample.created_at <= date_to, (
                    f"Sample {result_sample.id} created at {result_sample.created_at}, "
                    f"but date_to is {date_to}"
                )
    
    @given(
        category=category_strategy,
        tags=tags_list_strategy,
        quality_overall=quality_score_strategy,
        created_at=date_strategy(),
        search_category=st.one_of(st.none(), category_strategy),
        search_tags=tags_list_strategy,
        quality_min=st.one_of(st.none(), quality_score_strategy),
        quality_max=st.one_of(st.none(), quality_score_strategy),
        date_from=st.one_of(st.none(), date_strategy()),
        date_to=st.one_of(st.none(), date_strategy())
    )
    @settings(max_examples=50, deadline=None)
    def test_combined_filters_correctness(
        self,
        db_session: Session,
        category: str,
        tags: list,
        quality_overall: float,
        created_at: datetime,
        search_category: str,
        search_tags: list,
        quality_min: float,
        quality_max: float,
        date_from: datetime,
        date_to: datetime
    ):
        """
        Property: Combined filters return only samples matching ALL criteria.
        
        For any combination of search criteria (category, tags, quality range,
        date range), all returned samples must match ALL specified criteria.
        This is the core correctness property.
        """
        # Ensure valid ranges
        if quality_min is not None and quality_max is not None:
            assume(quality_min <= quality_max)
        if date_from is not None and date_to is not None:
            assume(date_from <= date_to)
        
        # Create sample
        manager = SampleLibraryManager(db_session)
        sample = create_sample(
            db_session,
            category=category,
            tags=tags,
            quality_overall=quality_overall,
            created_at=created_at
        )
        
        # Build search criteria
        criteria = SearchCriteria(
            category=search_category,
            tags=search_tags,
            quality_min=quality_min,
            quality_max=quality_max,
            date_from=date_from,
            date_to=date_to
        )
        
        # Execute search
        results, total = manager.search_samples(criteria)
        
        # Assert: All results match ALL criteria
        for result_sample in results:
            # Check category
            if search_category:
                assert result_sample.category == search_category, (
                    f"Sample {result_sample.id} has category '{result_sample.category}', "
                    f"but search was for category '{search_category}'"
                )
            
            # Check quality range
            if quality_min is not None:
                assert result_sample.quality_overall >= quality_min, (
                    f"Sample {result_sample.id} has quality {result_sample.quality_overall}, "
                    f"but quality_min is {quality_min}"
                )
            if quality_max is not None:
                assert result_sample.quality_overall <= quality_max, (
                    f"Sample {result_sample.id} has quality {result_sample.quality_overall}, "
                    f"but quality_max is {quality_max}"
                )
            
            # Check tags (must have ALL search tags)
            if search_tags:
                result_tags_set = set(result_sample.tags)
                for search_tag in search_tags:
                    assert search_tag in result_tags_set, (
                        f"Sample {result_sample.id} has tags {result_sample.tags}, "
                        f"but is missing required tag '{search_tag}'"
                    )
            
            # Check date range
            if date_from is not None:
                assert result_sample.created_at >= date_from, (
                    f"Sample {result_sample.id} created at {result_sample.created_at}, "
                    f"but date_from is {date_from}"
                )
            if date_to is not None:
                assert result_sample.created_at <= date_to, (
                    f"Sample {result_sample.id} created at {result_sample.created_at}, "
                    f"but date_to is {date_to}"
                )
        
        # Additional check: Verify our helper function agrees
        for result_sample in results:
            assert sample_matches_criteria(result_sample, criteria), (
                f"Sample {result_sample.id} returned by search but doesn't match criteria"
            )
    
    @given(
        num_samples=st.integers(min_value=5, max_value=20),
        search_category=category_strategy
    )
    @settings(max_examples=20, deadline=None)
    def test_search_completeness(
        self,
        db_session: Session,
        num_samples: int,
        search_category: str
    ):
        """
        Property: Search returns ALL matching samples (completeness).
        
        For any search criteria, the search must return ALL samples that
        match the criteria, not just some of them.
        """
        # Create multiple samples with known categories
        manager = SampleLibraryManager(db_session)
        matching_samples = []
        non_matching_samples = []
        
        for i in range(num_samples):
            # Alternate between matching and non-matching
            if i % 2 == 0:
                sample = create_sample(
                    db_session,
                    category=search_category,
                    tags=[],
                    quality_overall=0.8,
                    created_at=datetime.utcnow()
                )
                matching_samples.append(sample)
            else:
                other_category = 'medical' if search_category != 'medical' else 'legal'
                sample = create_sample(
                    db_session,
                    category=other_category,
                    tags=[],
                    quality_overall=0.8,
                    created_at=datetime.utcnow()
                )
                non_matching_samples.append(sample)
        
        # Search with category filter
        criteria = SearchCriteria(category=search_category, limit=100)
        results, total = manager.search_samples(criteria)
        
        # Assert: All matching samples are returned
        result_ids = {str(s.id) for s in results}
        for matching_sample in matching_samples:
            assert str(matching_sample.id) in result_ids, (
                f"Sample {matching_sample.id} matches criteria but was not returned"
            )
        
        # Assert: No non-matching samples are returned
        for non_matching_sample in non_matching_samples:
            assert str(non_matching_sample.id) not in result_ids, (
                f"Sample {non_matching_sample.id} doesn't match criteria but was returned"
            )
        
        # Assert: Total count matches expected
        assert total == len(matching_samples), (
            f"Expected {len(matching_samples)} matching samples, but total is {total}"
        )
    
    @given(
        limit=st.integers(min_value=1, max_value=10),
        offset=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=20, deadline=None)
    def test_pagination_correctness(
        self,
        db_session: Session,
        limit: int,
        offset: int
    ):
        """
        Property: Pagination returns correct subset of results.
        
        For any limit and offset, the paginated results must be a correct
        subset of the full result set, and the total count must be accurate.
        """
        # Create multiple samples
        manager = SampleLibraryManager(db_session)
        num_samples = 15
        created_samples = []
        
        for i in range(num_samples):
            sample = create_sample(
                db_session,
                category='test',
                tags=[],
                quality_overall=0.8,
                created_at=datetime.utcnow() - timedelta(seconds=i)
            )
            created_samples.append(sample)
        
        # Get full results
        full_criteria = SearchCriteria(category='test', limit=100, offset=0)
        full_results, full_total = manager.search_samples(full_criteria)
        
        # Get paginated results
        paginated_criteria = SearchCriteria(
            category='test',
            limit=limit,
            offset=offset
        )
        paginated_results, paginated_total = manager.search_samples(paginated_criteria)
        
        # Assert: Total count is the same
        assert paginated_total == full_total, (
            f"Paginated total {paginated_total} doesn't match full total {full_total}"
        )
        
        # Assert: Paginated results are a subset of full results
        full_result_ids = [str(s.id) for s in full_results]
        for paginated_sample in paginated_results:
            assert str(paginated_sample.id) in full_result_ids, (
                f"Paginated sample {paginated_sample.id} not in full results"
            )
        
        # Assert: Correct number of results (accounting for offset)
        expected_count = min(limit, max(0, full_total - offset))
        assert len(paginated_results) == expected_count, (
            f"Expected {expected_count} results, but got {len(paginated_results)}"
        )
    
    def test_empty_criteria_returns_all_samples(self, db_session: Session):
        """
        Property: Empty search criteria returns all samples.
        
        When no filters are specified, the search should return all samples
        in the library.
        """
        # Create multiple samples with different attributes
        manager = SampleLibraryManager(db_session)
        
        sample1 = create_sample(
            db_session,
            category='medical',
            tags=['important'],
            quality_overall=0.9,
            created_at=datetime.utcnow()
        )
        
        sample2 = create_sample(
            db_session,
            category='legal',
            tags=['urgent'],
            quality_overall=0.7,
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        
        # Search with empty criteria
        criteria = SearchCriteria(limit=100)
        results, total = manager.search_samples(criteria)
        
        # Assert: All samples are returned
        assert total >= 2, f"Expected at least 2 samples, but got {total}"
        result_ids = {str(s.id) for s in results}
        assert str(sample1.id) in result_ids
        assert str(sample2.id) in result_ids
