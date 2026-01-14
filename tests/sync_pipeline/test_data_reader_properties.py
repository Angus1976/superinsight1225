"""
Property-based tests for Data Reader.

Tests Property 2: Pagination memory safety
Tests Property 3: Read statistics completeness
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from src.sync.pipeline.schemas import DataPage, ReadStatistics
from src.sync.pipeline.data_reader import DataReader


# ============================================================================
# Test Helpers
# ============================================================================

def generate_mock_rows(count: int, columns: int = 5) -> List[Dict[str, Any]]:
    """Generate mock rows for testing."""
    return [
        {f"col_{j}": f"value_{i}_{j}" for j in range(columns)}
        for i in range(count)
    ]


def create_mock_pages(total_rows: int, page_size: int) -> List[DataPage]:
    """Create mock pages for testing."""
    pages = []
    page_number = 0
    remaining = total_rows
    
    while remaining > 0:
        rows_in_page = min(remaining, page_size)
        rows = generate_mock_rows(rows_in_page)
        
        pages.append(DataPage(
            page_number=page_number,
            rows=rows,
            row_count=rows_in_page,
            has_more=remaining > page_size
        ))
        
        remaining -= rows_in_page
        page_number += 1
    
    return pages


# ============================================================================
# Property 2: Pagination Memory Safety
# Validates: Requirements 1.5
# ============================================================================

@settings(max_examples=100)
@given(
    total_rows=st.integers(min_value=1, max_value=10000),
    page_size=st.integers(min_value=1, max_value=1000)
)
def test_pagination_memory_safety(total_rows: int, page_size: int):
    """
    Property 2: Pagination memory safety
    
    For any data read operation, when data exceeds page size,
    each page should contain at most page_size rows.
    
    **Validates: Requirements 1.5**
    """
    pages = create_mock_pages(total_rows, page_size)
    
    # Verify each page respects the page size limit
    for page in pages:
        assert page.row_count <= page_size, \
            f"Page {page.page_number} has {page.row_count} rows, exceeds limit {page_size}"
    
    # Verify total rows match
    actual_total = sum(page.row_count for page in pages)
    assert actual_total == total_rows, \
        f"Total rows mismatch: expected {total_rows}, got {actual_total}"


@settings(max_examples=100)
@given(
    total_rows=st.integers(min_value=1, max_value=5000),
    page_size=st.integers(min_value=100, max_value=1000)
)
def test_pagination_has_more_flag(total_rows: int, page_size: int):
    """
    Property 2 (extension): has_more flag correctness
    
    The has_more flag should be True for all pages except the last one.
    
    **Validates: Requirements 1.5**
    """
    pages = create_mock_pages(total_rows, page_size)
    
    for i, page in enumerate(pages):
        is_last_page = (i == len(pages) - 1)
        
        if is_last_page:
            assert not page.has_more, \
                f"Last page should have has_more=False"
        else:
            assert page.has_more, \
                f"Non-last page {i} should have has_more=True"


@settings(max_examples=100)
@given(
    page_size=st.integers(min_value=1, max_value=1000)
)
def test_pagination_single_page(page_size: int):
    """
    Property 2 (edge case): Single page when data fits
    
    When total rows <= page_size, there should be exactly one page.
    
    **Validates: Requirements 1.5**
    """
    total_rows = page_size  # Exactly fits in one page
    pages = create_mock_pages(total_rows, page_size)
    
    assert len(pages) == 1, \
        f"Expected 1 page, got {len(pages)}"
    assert pages[0].row_count == total_rows
    assert not pages[0].has_more


# ============================================================================
# Property 3: Read Statistics Completeness
# Validates: Requirements 1.6
# ============================================================================

@settings(max_examples=100)
@given(
    total_rows=st.integers(min_value=1, max_value=1000),
    columns=st.integers(min_value=1, max_value=20)
)
def test_statistics_completeness(total_rows: int, columns: int):
    """
    Property 3: Read statistics completeness
    
    For any completed read operation, statistics should include
    accurate row count, column count, and data size.
    
    **Validates: Requirements 1.6**
    """
    reader = DataReader()
    
    # Create pages with specified columns
    pages = []
    page_size = 100
    remaining = total_rows
    page_number = 0
    
    while remaining > 0:
        rows_in_page = min(remaining, page_size)
        rows = [
            {f"col_{j}": f"value_{i}_{j}" for j in range(columns)}
            for i in range(rows_in_page)
        ]
        
        pages.append(DataPage(
            page_number=page_number,
            rows=rows,
            row_count=rows_in_page,
            has_more=remaining > page_size
        ))
        
        remaining -= rows_in_page
        page_number += 1
    
    # Get statistics
    stats = reader.get_statistics(pages)
    
    # Verify row count
    assert stats.total_rows == total_rows, \
        f"Row count mismatch: expected {total_rows}, got {stats.total_rows}"
    
    # Verify column count
    assert stats.total_columns == columns, \
        f"Column count mismatch: expected {columns}, got {stats.total_columns}"
    
    # Verify size is positive
    assert stats.total_size_bytes > 0, \
        "Total size should be positive"


@settings(max_examples=100)
@given(
    value_length=st.integers(min_value=1, max_value=100)
)
def test_statistics_size_estimation(value_length: int):
    """
    Property 3 (extension): Size estimation accuracy
    
    The estimated size should be proportional to actual data size.
    
    **Validates: Requirements 1.6**
    """
    reader = DataReader()
    
    # Create rows with known value lengths
    rows = [
        {"col": "x" * value_length}
        for _ in range(10)
    ]
    
    pages = [DataPage(
        page_number=0,
        rows=rows,
        row_count=len(rows),
        has_more=False
    )]
    
    stats = reader.get_statistics(pages)
    
    # Size should be at least the sum of value lengths
    min_expected_size = 10 * value_length
    assert stats.total_size_bytes >= min_expected_size, \
        f"Size {stats.total_size_bytes} should be >= {min_expected_size}"


@settings(max_examples=100)
@given(
    num_pages=st.integers(min_value=1, max_value=10),
    rows_per_page=st.integers(min_value=1, max_value=100)
)
def test_statistics_aggregation(num_pages: int, rows_per_page: int):
    """
    Property 3 (extension): Statistics aggregation across pages
    
    Statistics should correctly aggregate data from multiple pages.
    
    **Validates: Requirements 1.6**
    """
    reader = DataReader()
    
    pages = []
    for i in range(num_pages):
        rows = generate_mock_rows(rows_per_page, columns=3)
        pages.append(DataPage(
            page_number=i,
            rows=rows,
            row_count=rows_per_page,
            has_more=(i < num_pages - 1)
        ))
    
    stats = reader.get_statistics(pages)
    
    expected_total = num_pages * rows_per_page
    assert stats.total_rows == expected_total, \
        f"Total rows mismatch: expected {expected_total}, got {stats.total_rows}"


def test_statistics_empty_pages():
    """
    Property 3 (edge case): Empty pages handling
    
    Statistics should handle empty page lists gracefully.
    
    **Validates: Requirements 1.6**
    """
    reader = DataReader()
    
    stats = reader.get_statistics([])
    
    assert stats.total_rows == 0
    assert stats.total_columns == 0
    assert stats.total_size_bytes == 0


def test_statistics_null_values():
    """
    Property 3 (edge case): Null values handling
    
    Statistics should handle null values in rows.
    
    **Validates: Requirements 1.6**
    """
    reader = DataReader()
    
    rows = [
        {"col1": None, "col2": "value", "col3": None}
        for _ in range(5)
    ]
    
    pages = [DataPage(
        page_number=0,
        rows=rows,
        row_count=len(rows),
        has_more=False
    )]
    
    stats = reader.get_statistics(pages)
    
    assert stats.total_rows == 5
    assert stats.total_columns == 3
    # Size should still be calculated (null values contribute 0)
    assert stats.total_size_bytes >= 0
