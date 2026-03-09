"""
Performance tests for Data Lifecycle Management System.

Tests cover:
- Sample library search with large datasets (10,000+ samples)
- Pagination performance with different page sizes
- Concurrent request handling for API endpoints

**Validates: Requirements 23.1, 23.4**

Performance targets:
- Search queries: < 2 seconds for 10,000+ samples
- Pagination: < 500ms per page
- Concurrent requests: Handle 50+ concurrent users
"""

import pytest
import time
import statistics
import concurrent.futures
from datetime import datetime, timedelta
from typing import List, Dict
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.models.data_lifecycle import (
    Base,
    SampleModel,
)
from src.services.sample_library_manager import (
    SampleLibraryManager,
    SearchCriteria,
)


# =============================================================================
# Test Constants
# =============================================================================

# Performance targets from requirements
SEARCH_LATENCY_TARGET_MS = 2000  # < 2 seconds for large dataset search
PAGINATION_LATENCY_TARGET_MS = 500  # < 500ms for pagination
CONCURRENT_USERS_TARGET = 50  # Handle 50+ concurrent users

# Test data sizes
SMALL_DATASET_SIZE = 100
MEDIUM_DATASET_SIZE = 1000
LARGE_DATASET_SIZE = 10000

# Pagination sizes
PAGE_SIZES = [10, 25, 50, 100]


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def db_session() -> Session:
    """
    Provide a database session with data lifecycle tables.
    
    Uses in-memory SQLite for fast test execution.
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    engine.dispose()


@pytest.fixture
def sample_library_manager(db_session):
    """Provide a SampleLibraryManager instance."""
    return SampleLibraryManager(db_session)


def create_sample(
    db_session: Session,
    category: str = "test",
    quality_overall: float = 0.8,
    tags: List[str] = None,
    created_at: datetime = None,
) -> SampleModel:
    """Helper function to create a sample."""
    if tags is None:
        tags = ["tag1", "tag2"]
    if created_at is None:
        created_at = datetime.utcnow()
    
    sample = SampleModel(
        id=str(uuid4()),
        data_id=str(uuid4()),
        content={"test": "data"},
        category=category,
        quality_overall=quality_overall,
        quality_completeness=0.9,
        quality_accuracy=0.85,
        quality_consistency=0.8,
        tags=tags,
        version=1,
        usage_count=0,
        created_at=created_at,
        updated_at=created_at,
    )
    
    db_session.add(sample)
    db_session.commit()
    db_session.refresh(sample)
    
    return sample


def populate_samples(
    db_session: Session,
    count: int,
    categories: List[str] = None,
    quality_range: tuple = (0.5, 1.0),
    tags_pool: List[str] = None,
) -> List[SampleModel]:
    """
    Populate database with sample data.
    
    Args:
        db_session: Database session
        count: Number of samples to create
        categories: List of categories to randomly assign
        quality_range: Tuple of (min, max) quality scores
        tags_pool: Pool of tags to randomly assign
    
    Returns:
        List of created samples
    """
    import random
    
    if categories is None:
        categories = ["category_a", "category_b", "category_c", "category_d"]
    if tags_pool is None:
        tags_pool = ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"]
    
    samples = []
    base_time = datetime.utcnow() - timedelta(days=365)
    
    for i in range(count):
        # Randomize attributes for realistic distribution
        category = random.choice(categories)
        quality = random.uniform(*quality_range)
        num_tags = random.randint(1, 4)
        tags = random.sample(tags_pool, num_tags)
        created_at = base_time + timedelta(days=random.randint(0, 365))
        
        sample = SampleModel(
            id=str(uuid4()),
            data_id=str(uuid4()),
            content={"test": f"data_{i}"},
            category=category,
            quality_overall=quality,
            quality_completeness=quality + random.uniform(-0.1, 0.1),
            quality_accuracy=quality + random.uniform(-0.1, 0.1),
            quality_consistency=quality + random.uniform(-0.1, 0.1),
            tags=tags,
            version=1,
            usage_count=random.randint(0, 100),
            created_at=created_at,
            updated_at=created_at,
        )
        
        samples.append(sample)
    
    # Bulk insert for performance
    db_session.bulk_save_objects(samples)
    db_session.commit()
    
    return samples


# =============================================================================
# Sample Library Search Performance Tests
# =============================================================================

class TestSampleLibrarySearchPerformance:
    """Performance tests for sample library search with large datasets."""
    
    def test_search_small_dataset_baseline(self, db_session, sample_library_manager):
        """
        Baseline test: Search performance with small dataset (100 samples).
        
        Validates: Requirements 23.4
        """
        # Populate small dataset
        populate_samples(db_session, SMALL_DATASET_SIZE)
        
        # Test search with no filters
        criteria = SearchCriteria(limit=50, offset=0)
        
        iterations = 50
        latencies = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            results, total = sample_library_manager.search_samples(criteria)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]
        
        print(f"\nSmall Dataset Search ({SMALL_DATASET_SIZE} samples, {iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")
        print(f"  Target: < {PAGINATION_LATENCY_TARGET_MS}ms")
        
        assert p95_latency < PAGINATION_LATENCY_TARGET_MS, \
            f"P95 search latency {p95_latency:.3f}ms exceeds target"
    
    def test_search_medium_dataset(self, db_session, sample_library_manager):
        """
        Test search performance with medium dataset (1,000 samples).
        
        Validates: Requirements 23.4
        """
        # Populate medium dataset
        populate_samples(db_session, MEDIUM_DATASET_SIZE)
        
        # Test search with category filter
        criteria = SearchCriteria(
            category="category_a",
            limit=50,
            offset=0
        )
        
        iterations = 30
        latencies = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            results, total = sample_library_manager.search_samples(criteria)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]
        
        print(f"\nMedium Dataset Search ({MEDIUM_DATASET_SIZE} samples, {iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")
        print(f"  Target: < {SEARCH_LATENCY_TARGET_MS}ms")
        
        assert p95_latency < SEARCH_LATENCY_TARGET_MS, \
            f"P95 search latency {p95_latency:.3f}ms exceeds target"
    
    def test_search_large_dataset(self, db_session, sample_library_manager):
        """
        Test search performance with large dataset (10,000+ samples).
        
        This is the primary performance test for Requirement 23.4.
        
        Validates: Requirements 23.4
        """
        # Populate large dataset
        print(f"\nPopulating {LARGE_DATASET_SIZE} samples...")
        start_populate = time.perf_counter()
        populate_samples(db_session, LARGE_DATASET_SIZE)
        end_populate = time.perf_counter()
        print(f"Population completed in {(end_populate - start_populate):.2f}s")
        
        # Test search with multiple filters
        criteria = SearchCriteria(
            category="category_a",
            quality_min=0.7,
            tags=["tag1"],
            limit=50,
            offset=0
        )
        
        iterations = 20
        latencies = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            results, total = sample_library_manager.search_samples(criteria)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]
        p99_latency = sorted(latencies)[int(iterations * 0.99)]
        
        print(f"\nLarge Dataset Search ({LARGE_DATASET_SIZE} samples, {iterations} iterations):")
        print(f"  Average latency: {avg_latency:.3f}ms")
        print(f"  P95 latency: {p95_latency:.3f}ms")
        print(f"  P99 latency: {p99_latency:.3f}ms")
        print(f"  Target: < {SEARCH_LATENCY_TARGET_MS}ms")
        print(f"  Results returned: {len(results)}")
        print(f"  Total matching: {total}")
        
        assert p95_latency < SEARCH_LATENCY_TARGET_MS, \
            f"P95 search latency {p95_latency:.3f}ms exceeds target {SEARCH_LATENCY_TARGET_MS}ms"


# =============================================================================
# Pagination Performance Tests
# =============================================================================

class TestPaginationPerformance:
    """Performance tests for pagination with different page sizes."""
    
    def test_pagination_different_page_sizes(self, db_session, sample_library_manager):
        """
        Test pagination performance with various page sizes.
        
        Validates: Requirements 23.1
        """
        # Populate dataset
        populate_samples(db_session, MEDIUM_DATASET_SIZE)
        
        results = {}
        
        for page_size in PAGE_SIZES:
            criteria = SearchCriteria(limit=page_size, offset=0)
            
            iterations = 30
            latencies = []
            
            for _ in range(iterations):
                start = time.perf_counter()
                samples, total = sample_library_manager.search_samples(criteria)
                end = time.perf_counter()
                latencies.append((end - start) * 1000)
            
            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(iterations * 0.95)]
            
            results[page_size] = {
                "avg": avg_latency,
                "p95": p95_latency,
            }
        
        print(f"\nPagination Performance ({MEDIUM_DATASET_SIZE} samples):")
        for page_size, metrics in results.items():
            print(f"  Page size {page_size:3d}: avg={metrics['avg']:.3f}ms, p95={metrics['p95']:.3f}ms")
        print(f"  Target: < {PAGINATION_LATENCY_TARGET_MS}ms")
        
        # All page sizes should meet target
        for page_size, metrics in results.items():
            assert metrics["p95"] < PAGINATION_LATENCY_TARGET_MS, \
                f"Page size {page_size} P95 latency {metrics['p95']:.3f}ms exceeds target"


# =============================================================================
# Concurrent Request Handling Tests
# =============================================================================

class TestConcurrentRequestHandling:
    """Performance tests for concurrent request handling."""
    
    def test_concurrent_search_requests(self, db_session, sample_library_manager):
        """
        Test handling of concurrent search requests.
        
        Validates: Requirements 23.1
        """
        # Populate dataset
        populate_samples(db_session, MEDIUM_DATASET_SIZE)
        
        def perform_search(search_id: int) -> Dict:
            """Perform a single search operation."""
            criteria = SearchCriteria(
                category=f"category_{chr(97 + (search_id % 4))}",  # a, b, c, d
                limit=50,
                offset=(search_id % 10) * 50
            )
            
            start = time.perf_counter()
            results, total = sample_library_manager.search_samples(criteria)
            end = time.perf_counter()
            
            return {
                "search_id": search_id,
                "latency_ms": (end - start) * 1000,
                "results_count": len(results),
                "total": total,
            }
        
        # Test with increasing concurrency levels
        concurrency_levels = [10, 25, 50]
        
        for num_concurrent in concurrency_levels:
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
                start_time = time.perf_counter()
                
                # Submit all tasks
                futures = [
                    executor.submit(perform_search, i)
                    for i in range(num_concurrent)
                ]
                
                # Wait for all to complete
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
                
                end_time = time.perf_counter()
            
            # Analyze results
            latencies = [r["latency_ms"] for r in results]
            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            total_time = (end_time - start_time) * 1000
            throughput = num_concurrent / (total_time / 1000)
            
            print(f"\nConcurrent Requests ({num_concurrent} concurrent users):")
            print(f"  Total time: {total_time:.3f}ms")
            print(f"  Average latency: {avg_latency:.3f}ms")
            print(f"  P95 latency: {p95_latency:.3f}ms")
            print(f"  Throughput: {throughput:.2f} requests/second")
            print(f"  Target: Handle {CONCURRENT_USERS_TARGET}+ concurrent users")
            
            # Verify all requests completed successfully
            assert len(results) == num_concurrent, \
                f"Expected {num_concurrent} results, got {len(results)}"
            
            # Verify reasonable latency under load
            assert p95_latency < SEARCH_LATENCY_TARGET_MS * 2, \
                f"P95 latency {p95_latency:.3f}ms exceeds 2x target under {num_concurrent} concurrent users"


# =============================================================================
# Summary Report
# =============================================================================

def test_performance_summary():
    """
    Print a summary of all performance targets and requirements.
    
    This test always passes but provides documentation.
    """
    print("\n" + "=" * 70)
    print("DATA LIFECYCLE MANAGEMENT - PERFORMANCE REQUIREMENTS")
    print("=" * 70)
    print("\nRequirement 23.1: Pagination Support")
    print(f"  - Target: < {PAGINATION_LATENCY_TARGET_MS}ms per page")
    print("  - Configurable page sizes: 10, 25, 50, 100")
    print("  - Consistent results across pages")
    print("\nRequirement 23.4: Search Query Optimization")
    print(f"  - Target: < {SEARCH_LATENCY_TARGET_MS}ms for large datasets")
    print(f"  - Large dataset: {LARGE_DATASET_SIZE}+ samples")
    print("  - Proper indexing on frequently queried fields")
    print("  - Support for complex filter combinations")
    print("\nConcurrent Request Handling:")
    print(f"  - Target: Handle {CONCURRENT_USERS_TARGET}+ concurrent users")
    print("  - Mixed operation types (search, get, track usage)")
    print("  - Reasonable latency under load (< 2x normal)")
    print("=" * 70 + "\n")
    
    assert True  # Always pass
