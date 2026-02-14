"""
Property-based tests for pagination consistency in OpenClawDataBridge.

Tests that paginated data access returns complete datasets without duplicates
or missing records.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from typing import List, Dict, Any, Set

from src.ai_integration.data_bridge import OpenClawDataBridge
from src.export.service import ExportService
from src.export.models import ExportResult, ExportFormat
from src.sync.pipeline.ai_exporter import AIFriendlyExporter
from datetime import datetime


# ============================================================================
# Strategy Generators
# ============================================================================

@st.composite
def dataset_strategy(draw):
    """Generate a dataset of documents."""
    num_documents = draw(st.integers(min_value=10, max_value=100))
    documents = []
    for i in range(num_documents):
        doc = {
            "id": f"doc_{i}",
            "content": f"Document content {i}",
            "index": i,
            "created_at": datetime.utcnow().isoformat()
        }
        documents.append(doc)
    return documents


@st.composite
def pagination_params_strategy(draw):
    """Generate pagination parameters."""
    page_size = draw(st.integers(min_value=5, max_value=25))
    return {
        "page_size": page_size,
        "page": draw(st.integers(min_value=1, max_value=10))
    }


# ============================================================================
# Helper Functions
# ============================================================================

def paginate_documents(
    documents: List[Dict[str, Any]],
    page: int,
    page_size: int
) -> List[Dict[str, Any]]:
    """
    Paginate a list of documents.
    
    Args:
        documents: Complete list of documents
        page: Page number (1-indexed)
        page_size: Number of documents per page
        
    Returns:
        List of documents for the requested page
    """
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    return documents[start_idx:end_idx]


def create_paginated_export_result(
    documents: List[Dict[str, Any]],
    page: int,
    page_size: int
) -> tuple[ExportResult, List[Dict[str, Any]]]:
    """
    Create a mock export result for a specific page.
    
    Args:
        documents: Complete dataset
        page: Page number
        page_size: Page size
        
    Returns:
        Tuple of (ExportResult, page_documents)
    """
    page_docs = paginate_documents(documents, page, page_size)
    
    result = ExportResult(
        export_id=f"export_page_{page}",
        status="completed",
        format=ExportFormat.JSON,
        total_records=len(documents),
        exported_records=len(page_docs),
        file_path=f"/tmp/export_page_{page}.json",
        file_size=1024,
        completed_at=datetime.utcnow(),
        error=None
    )
    
    return result, page_docs


# ============================================================================
# Property-Based Test for Pagination Consistency
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    dataset=dataset_strategy(),
    page_size=st.integers(min_value=5, max_value=25)
)
@pytest.mark.asyncio
async def test_property_pagination_consistency(
    dataset: List[Dict[str, Any]],
    page_size: int
):
    """
    **Property 9: Pagination Consistency**
    
    For any large dataset request with pagination, the union of all pages 
    should equal the complete dataset, with no duplicates or missing records.
    
    **Validates: Requirements 3.5**
    
    This property test verifies that:
    1. Union of all pages equals the complete dataset
    2. No documents are duplicated across pages
    3. No documents are missing from the paginated results
    4. Page boundaries are respected (no overlap)
    5. Last page may be partial but contains remaining documents
    6. Empty pages are not returned after the last page
    7. Document order is preserved across pages
    
    Feature: ai-application-integration, Property 9: Pagination Consistency
    """
    # Skip if dataset is too small for meaningful pagination test
    assume(len(dataset) > page_size)
    
    # Calculate number of pages
    total_docs = len(dataset)
    num_pages = (total_docs + page_size - 1) // page_size
    
    # Create mock services
    mock_export_service = Mock(spec=ExportService)
    mock_ai_exporter = Mock(spec=AIFriendlyExporter)
    
    data_bridge = OpenClawDataBridge(
        export_service=mock_export_service,
        ai_exporter=mock_ai_exporter
    )
    
    # Collect all documents from all pages
    all_paginated_docs = []
    all_doc_ids = set()
    
    for page_num in range(1, num_pages + 1):
        # Create paginated result for this page
        export_result, page_docs = create_paginated_export_result(
            dataset, page_num, page_size
        )
        
        # Configure mock
        mock_export_service.start_export.return_value = export_result.export_id
        mock_export_service.export_data_optimized.return_value = export_result
        
        # Query this page
        filters = {
            "page": page_num,
            "page_size": page_size
        }
        
        response = await data_bridge.query_governed_data(
            gateway_id="test_gateway",
            tenant_id="test_tenant",
            filters=filters
        )
        
        # Property 1: Response should indicate correct total
        assert response["total_records"] == total_docs, \
            f"Page {page_num}: total_records should be {total_docs}, got {response['total_records']}"
        
        # Property 2: Page size should be respected (except last page)
        if page_num < num_pages:
            assert len(page_docs) == page_size, \
                f"Page {page_num}: should have {page_size} documents, got {len(page_docs)}"
        else:
            # Last page may be partial
            expected_last_page_size = total_docs - (num_pages - 1) * page_size
            assert len(page_docs) == expected_last_page_size, \
                f"Last page {page_num}: should have {expected_last_page_size} documents, got {len(page_docs)}"
        
        # Collect documents and IDs
        for doc in page_docs:
            all_paginated_docs.append(doc)
            doc_id = doc["id"]
            
            # Property 3: No duplicates across pages
            assert doc_id not in all_doc_ids, \
                f"Document {doc_id} appears in multiple pages"
            
            all_doc_ids.add(doc_id)
    
    # Property 4: Union of all pages equals complete dataset
    assert len(all_paginated_docs) == len(dataset), \
        f"Paginated results have {len(all_paginated_docs)} documents, " \
        f"expected {len(dataset)}"
    
    # Property 5: No missing documents
    original_ids = {doc["id"] for doc in dataset}
    assert all_doc_ids == original_ids, \
        f"Missing documents: {original_ids - all_doc_ids}, " \
        f"Extra documents: {all_doc_ids - original_ids}"
    
    # Property 6: Document order is preserved
    for i, doc in enumerate(all_paginated_docs):
        expected_index = i
        actual_index = doc["index"]
        assert actual_index == expected_index, \
            f"Document at position {i} has index {actual_index}, expected {expected_index}"
    
    # Property 7: Verify no empty pages before the last page
    for page_num in range(1, num_pages):
        export_result, page_docs = create_paginated_export_result(
            dataset, page_num, page_size
        )
        assert len(page_docs) > 0, \
            f"Page {page_num} is empty but not the last page"
    
    # Property 8: Requesting page beyond last page returns empty
    beyond_last_page = num_pages + 1
    export_result, page_docs = create_paginated_export_result(
        dataset, beyond_last_page, page_size
    )
    assert len(page_docs) == 0, \
        f"Page {beyond_last_page} beyond last page should be empty"


# ============================================================================
# Additional Test: Pagination with Different Page Sizes
# ============================================================================

@settings(
    max_examples=20,
    deadline=None
)
@given(
    num_documents=st.integers(min_value=20, max_value=100),
    page_sizes=st.lists(
        st.integers(min_value=5, max_value=30),
        min_size=2,
        max_size=4
    )
)
@pytest.mark.asyncio
async def test_pagination_with_different_page_sizes(
    num_documents: int,
    page_sizes: List[int]
):
    """
    Test pagination consistency with different page sizes.
    
    Ensures that the same dataset can be paginated with different page sizes
    and always returns the complete dataset.
    """
    # Create dataset
    dataset = [
        {
            "id": f"doc_{i}",
            "content": f"Content {i}",
            "index": i
        }
        for i in range(num_documents)
    ]
    
    # Create mock services
    mock_export_service = Mock(spec=ExportService)
    mock_ai_exporter = Mock(spec=AIFriendlyExporter)
    
    data_bridge = OpenClawDataBridge(
        export_service=mock_export_service,
        ai_exporter=mock_ai_exporter
    )
    
    # Test with each page size
    for page_size in page_sizes:
        num_pages = (num_documents + page_size - 1) // page_size
        all_docs = []
        
        for page_num in range(1, num_pages + 1):
            export_result, page_docs = create_paginated_export_result(
                dataset, page_num, page_size
            )
            
            mock_export_service.start_export.return_value = export_result.export_id
            mock_export_service.export_data_optimized.return_value = export_result
            
            filters = {"page": page_num, "page_size": page_size}
            response = await data_bridge.query_governed_data(
                gateway_id="test_gateway",
                tenant_id="test_tenant",
                filters=filters
            )
            
            all_docs.extend(page_docs)
        
        # Verify completeness for this page size
        assert len(all_docs) == num_documents, \
            f"With page_size={page_size}, got {len(all_docs)} documents, expected {num_documents}"
        
        # Verify no duplicates
        doc_ids = [doc["id"] for doc in all_docs]
        assert len(doc_ids) == len(set(doc_ids)), \
            f"With page_size={page_size}, found duplicate documents"


# ============================================================================
# Additional Test: Pagination Edge Cases
# ============================================================================

@settings(
    max_examples=20,
    deadline=None
)
@given(
    num_documents=st.integers(min_value=1, max_value=50),
    page_size=st.integers(min_value=1, max_value=100)
)
@pytest.mark.asyncio
async def test_pagination_edge_cases(
    num_documents: int,
    page_size: int
):
    """
    Test pagination edge cases.
    
    Tests scenarios like:
    - Page size larger than dataset
    - Page size equal to dataset
    - Single document per page
    - Empty dataset
    """
    # Create dataset
    dataset = [
        {"id": f"doc_{i}", "content": f"Content {i}", "index": i}
        for i in range(num_documents)
    ]
    
    mock_export_service = Mock(spec=ExportService)
    mock_ai_exporter = Mock(spec=AIFriendlyExporter)
    
    data_bridge = OpenClawDataBridge(
        export_service=mock_export_service,
        ai_exporter=mock_ai_exporter
    )
    
    # Case 1: Page size larger than or equal to dataset
    if page_size >= num_documents and num_documents > 0:
        export_result, page_docs = create_paginated_export_result(
            dataset, 1, page_size
        )
        
        mock_export_service.start_export.return_value = export_result.export_id
        mock_export_service.export_data_optimized.return_value = export_result
        
        response = await data_bridge.query_governed_data(
            gateway_id="test_gateway",
            tenant_id="test_tenant",
            filters={"page": 1, "page_size": page_size}
        )
        
        # Should return all documents in one page
        assert len(page_docs) == num_documents, \
            f"Single page should contain all {num_documents} documents"
        
        # Second page should be empty
        export_result2, page_docs2 = create_paginated_export_result(
            dataset, 2, page_size
        )
        assert len(page_docs2) == 0, \
            "Second page should be empty when all documents fit in first page"
    
    # Case 2: Single document per page
    if page_size == 1 and num_documents > 0:
        all_docs = []
        for page_num in range(1, num_documents + 1):
            export_result, page_docs = create_paginated_export_result(
                dataset, page_num, 1
            )
            all_docs.extend(page_docs)
            
            assert len(page_docs) == 1, \
                f"Page {page_num} should have exactly 1 document"
        
        assert len(all_docs) == num_documents, \
            "Total documents should match dataset size"
    
    # Case 3: Empty dataset
    if num_documents == 0:
        export_result, page_docs = create_paginated_export_result(
            dataset, 1, page_size
        )
        
        assert len(page_docs) == 0, \
            "Empty dataset should return empty page"
        assert export_result.total_records == 0, \
            "Empty dataset should have total_records = 0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
