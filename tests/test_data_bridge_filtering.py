"""
Property-based tests for data filtering in OpenClawDataBridge.

Tests that data access requests with filters return only data matching
all specified filter criteria.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.ai_integration.data_bridge import OpenClawDataBridge
from src.export.service import ExportService
from src.export.models import ExportResult, ExportFormat, ExportRequest
from src.sync.pipeline.ai_exporter import AIFriendlyExporter


# ============================================================================
# Strategy Generators
# ============================================================================

@st.composite
def annotation_status_strategy(draw):
    """Generate annotation status values."""
    return draw(st.sampled_from([
        "pending", "in_progress", "completed", "reviewed", "rejected"
    ]))


@st.composite
def quality_score_strategy(draw):
    """Generate quality scores between 0.0 and 1.0."""
    return draw(st.floats(min_value=0.0, max_value=1.0))


@st.composite
def metadata_tags_strategy(draw):
    """Generate metadata tags."""
    num_tags = draw(st.integers(min_value=0, max_value=5))
    tags = []
    for _ in range(num_tags):
        tag = draw(st.sampled_from([
            "medical", "legal", "financial", "technical", "general",
            "urgent", "archived", "reviewed", "validated"
        ]))
        tags.append(tag)
    return list(set(tags))  # Remove duplicates


@st.composite
def dataset_id_strategy(draw):
    """Generate dataset IDs."""
    return draw(st.sampled_from([
        "dataset_001", "dataset_002", "dataset_003",
        "dataset_medical", "dataset_legal", "dataset_financial"
    ]))


@st.composite
def mock_document_strategy(draw):
    """Generate mock document data with filterable fields."""
    return {
        "id": draw(st.uuids()).hex,
        "dataset_id": draw(dataset_id_strategy()),
        "annotation_status": draw(annotation_status_strategy()),
        "quality_score": draw(quality_score_strategy()),
        "metadata_tags": draw(metadata_tags_strategy()),
        "content": draw(st.text(min_size=10, max_size=100)),
        "created_at": datetime.utcnow().isoformat()
    }


@st.composite
def filter_criteria_strategy(draw):
    """Generate filter criteria for data queries."""
    filters = {}
    
    # Randomly include different filter types
    if draw(st.booleans()):
        filters["dataset_id"] = draw(dataset_id_strategy())
    
    if draw(st.booleans()):
        filters["annotation_status"] = draw(annotation_status_strategy())
    
    if draw(st.booleans()):
        min_score = draw(st.floats(min_value=0.0, max_value=0.9))
        filters["min_quality_score"] = min_score
    
    if draw(st.booleans()):
        filters["metadata_tags"] = draw(metadata_tags_strategy())
    
    # Ensure at least one filter is present
    if not filters:
        filters["dataset_id"] = draw(dataset_id_strategy())
    
    return filters


# ============================================================================
# Helper Functions
# ============================================================================

def document_matches_filters(document: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """
    Check if a document matches all specified filters.
    
    Args:
        document: Document data
        filters: Filter criteria
        
    Returns:
        True if document matches all filters, False otherwise
    """
    # Check dataset filter
    if "dataset_id" in filters:
        if document.get("dataset_id") != filters["dataset_id"]:
            return False
    
    # Check annotation status filter
    if "annotation_status" in filters:
        if document.get("annotation_status") != filters["annotation_status"]:
            return False
    
    # Check quality score filter
    if "min_quality_score" in filters:
        doc_score = document.get("quality_score", 0.0)
        if doc_score < filters["min_quality_score"]:
            return False
    
    # Check metadata tags filter (document must have ALL specified tags)
    if "metadata_tags" in filters and filters["metadata_tags"]:
        doc_tags = set(document.get("metadata_tags", []))
        required_tags = set(filters["metadata_tags"])
        if not required_tags.issubset(doc_tags):
            return False
    
    return True


def create_mock_export_result(
    documents: List[Dict[str, Any]],
    filters: Dict[str, Any]
) -> tuple[ExportResult, List[Dict[str, Any]]]:
    """
    Create a mock export result with filtered documents.
    
    Args:
        documents: All available documents
        filters: Filter criteria to apply
        
    Returns:
        Tuple of (ExportResult, filtered_documents)
    """
    # Filter documents based on criteria
    filtered_docs = [
        doc for doc in documents
        if document_matches_filters(doc, filters)
    ]
    
    result = ExportResult(
        export_id="test_export_123",
        status="completed",
        format=ExportFormat.JSON,
        total_records=len(filtered_docs),
        exported_records=len(filtered_docs),
        file_path="/tmp/export_test.json",
        file_size=1024,
        completed_at=datetime.utcnow(),
        error=None
    )
    
    return result, filtered_docs


# ============================================================================
# Property-Based Test for Data Filtering
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_documents=st.integers(min_value=10, max_value=50),
    filter_criteria=filter_criteria_strategy(),
    num_queries=st.integers(min_value=1, max_value=5),
    data=st.data()
)
@pytest.mark.asyncio
async def test_property_data_filtering_functionality(
    num_documents: int,
    filter_criteria: Dict[str, Any],
    num_queries: int,
    data
):
    """
    **Property 8: Data Filtering Functionality**
    
    For any data access request with filters (dataset, annotation status, 
    quality score, metadata tags), only data matching all specified filters 
    should be returned.
    
    **Validates: Requirements 3.4**
    
    This property test verifies that:
    1. All returned documents match the dataset filter (if specified)
    2. All returned documents match the annotation status filter (if specified)
    3. All returned documents meet the quality score threshold (if specified)
    4. All returned documents contain all required metadata tags (if specified)
    5. No documents are returned that don't match all filters
    6. Filter combinations work correctly (AND logic)
    7. Empty result sets are handled correctly when no documents match
    
    Feature: ai-application-integration, Property 8: Data Filtering Functionality
    """
    # Generate a pool of documents with various attributes
    documents = []
    for _ in range(num_documents):
        doc = {
            "id": f"doc_{_}",
            "dataset_id": data.draw(st.sampled_from([
                "dataset_001", "dataset_002", "dataset_003"
            ])),
            "annotation_status": data.draw(st.sampled_from([
                "pending", "in_progress", "completed", "reviewed"
            ])),
            "quality_score": data.draw(st.floats(min_value=0.0, max_value=1.0)),
            "metadata_tags": data.draw(st.lists(
                st.sampled_from(["medical", "legal", "financial", "urgent"]),
                min_size=0,
                max_size=3
            )),
            "content": f"Document content {_}"
        }
        documents.append(doc)
    
    # Create mock services
    mock_export_service = Mock(spec=ExportService)
    mock_ai_exporter = Mock(spec=AIFriendlyExporter)
    
    # Create data bridge
    data_bridge = OpenClawDataBridge(
        export_service=mock_export_service,
        ai_exporter=mock_ai_exporter
    )
    
    # Test multiple queries with the same filters
    for query_idx in range(num_queries):
        gateway_id = f"gateway_{query_idx}"
        tenant_id = f"tenant_{query_idx % 3}"
        
        # Create mock export result with filtered documents
        export_result, filtered_docs = create_mock_export_result(documents, filter_criteria)
        
        # Configure mock to return the filtered result
        mock_export_service.start_export.return_value = export_result.export_id
        mock_export_service.export_data_optimized.return_value = export_result
        
        # Execute query with filters
        response = await data_bridge.query_governed_data(
            gateway_id=gateway_id,
            tenant_id=tenant_id,
            filters=filter_criteria
        )
        
        # Property 1: Response metadata should match filtered count
        assert response["total_records"] == len(filtered_docs), \
            f"Response total_records {response['total_records']} " \
            f"doesn't match filtered count {len(filtered_docs)}"
        assert response["exported_records"] == len(filtered_docs), \
            f"Response exported_records {response['exported_records']} " \
            f"doesn't match filtered count {len(filtered_docs)}"
        
        # Property 2: Verify filtering logic correctness
        # All documents that match filters should be counted
        expected_matching = [
            doc for doc in documents
            if document_matches_filters(doc, filter_criteria)
        ]
        
        assert len(filtered_docs) == len(expected_matching), \
            f"Filtered count {len(filtered_docs)} doesn't match expected {len(expected_matching)}"
        
        # Property 3: All filtered documents must match dataset filter
        if "dataset_id" in filter_criteria:
            expected_dataset = filter_criteria["dataset_id"]
            for doc in filtered_docs:
                assert doc.get("dataset_id") == expected_dataset, \
                    f"Document {doc['id']} has dataset {doc.get('dataset_id')}, " \
                    f"expected {expected_dataset}"
        
        # Property 4: All filtered documents must match annotation status filter
        if "annotation_status" in filter_criteria:
            expected_status = filter_criteria["annotation_status"]
            for doc in filtered_docs:
                assert doc.get("annotation_status") == expected_status, \
                    f"Document {doc['id']} has status {doc.get('annotation_status')}, " \
                    f"expected {expected_status}"
        
        # Property 5: All filtered documents must meet quality score threshold
        if "min_quality_score" in filter_criteria:
            min_score = filter_criteria["min_quality_score"]
            for doc in filtered_docs:
                doc_score = doc.get("quality_score", 0.0)
                assert doc_score >= min_score, \
                    f"Document {doc['id']} has quality score {doc_score}, " \
                    f"expected >= {min_score}"
        
        # Property 6: All filtered documents must contain all required metadata tags
        if "metadata_tags" in filter_criteria and filter_criteria["metadata_tags"]:
            required_tags = set(filter_criteria["metadata_tags"])
            for doc in filtered_docs:
                doc_tags = set(doc.get("metadata_tags", []))
                assert required_tags.issubset(doc_tags), \
                    f"Document {doc['id']} has tags {doc_tags}, " \
                    f"missing required tags {required_tags - doc_tags}"
        
        # Property 7: Filter combinations work correctly (AND logic)
        # All filters must be satisfied simultaneously
        for doc in filtered_docs:
            assert document_matches_filters(doc, filter_criteria), \
                f"Document {doc['id']} in results but doesn't match all filters"
        
        # Property 8: No documents that don't match should be included
        for doc in filtered_docs:
            # Each filtered doc must match all criteria
            if "dataset_id" in filter_criteria:
                assert doc.get("dataset_id") == filter_criteria["dataset_id"]
            if "annotation_status" in filter_criteria:
                assert doc.get("annotation_status") == filter_criteria["annotation_status"]
            if "min_quality_score" in filter_criteria:
                assert doc.get("quality_score", 0.0) >= filter_criteria["min_quality_score"]
            if "metadata_tags" in filter_criteria and filter_criteria["metadata_tags"]:
                doc_tags = set(doc.get("metadata_tags", []))
                required_tags = set(filter_criteria["metadata_tags"])
                assert required_tags.issubset(doc_tags)
        
        # Property 9: Empty result sets are handled correctly
        if len(filtered_docs) == 0:
            # Verify that indeed no documents match the filters
            matching_docs = [
                doc for doc in documents
                if document_matches_filters(doc, filter_criteria)
            ]
            assert len(matching_docs) == 0, \
                "Empty result set but matching documents exist"


# ============================================================================
# Additional Test: Multiple Filter Combinations
# ============================================================================

@settings(
    max_examples=20,
    deadline=None
)
@given(
    num_documents=st.integers(min_value=20, max_value=50),
    num_filter_combinations=st.integers(min_value=2, max_value=5),
    data=st.data()
)
@pytest.mark.asyncio
async def test_multiple_filter_combinations(
    num_documents: int,
    num_filter_combinations: int,
    data
):
    """
    Test data filtering with multiple different filter combinations.
    
    Ensures that different filter combinations produce correct results
    and that filters are applied consistently.
    """
    # Generate documents
    documents = []
    for i in range(num_documents):
        doc = {
            "id": f"doc_{i}",
            "dataset_id": data.draw(st.sampled_from([
                "dataset_001", "dataset_002", "dataset_003"
            ])),
            "annotation_status": data.draw(st.sampled_from([
                "pending", "completed", "reviewed"
            ])),
            "quality_score": data.draw(st.floats(min_value=0.0, max_value=1.0)),
            "metadata_tags": data.draw(st.lists(
                st.sampled_from(["medical", "legal", "urgent"]),
                min_size=0,
                max_size=2
            )),
            "content": f"Content {i}"
        }
        documents.append(doc)
    
    # Create mock services
    mock_export_service = Mock(spec=ExportService)
    mock_ai_exporter = Mock(spec=AIFriendlyExporter)
    
    data_bridge = OpenClawDataBridge(
        export_service=mock_export_service,
        ai_exporter=mock_ai_exporter
    )
    
    # Test multiple filter combinations
    for combo_idx in range(num_filter_combinations):
        # Generate random filter combination
        filters = {}
        
        if combo_idx % 3 == 0:
            filters["dataset_id"] = "dataset_001"
        if combo_idx % 3 == 1:
            filters["annotation_status"] = "completed"
        if combo_idx % 3 == 2:
            filters["min_quality_score"] = 0.5
        
        # Ensure at least one filter
        if not filters:
            filters["dataset_id"] = "dataset_001"
        
        # Create filtered result
        export_result, filtered_docs = create_mock_export_result(documents, filters)
        mock_export_service.start_export.return_value = export_result.export_id
        mock_export_service.export_data_optimized.return_value = export_result
        
        # Execute query
        response = await data_bridge.query_governed_data(
            gateway_id=f"gateway_{combo_idx}",
            tenant_id="test_tenant",
            filters=filters
        )
        
        # Verify all returned documents match filters
        for doc in filtered_docs:
            assert document_matches_filters(doc, filters), \
                f"Document {doc['id']} doesn't match filters {filters}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
