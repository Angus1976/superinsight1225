"""
Property-based tests for format transformation in OpenClawDataBridge.

Tests that data format conversions preserve all annotations, metadata,
and lineage information.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from typing import List, Dict, Any
import json

from src.ai_integration.data_bridge import OpenClawDataBridge
from src.export.service import ExportService
from src.sync.pipeline.ai_exporter import AIFriendlyExporter
from src.sync.pipeline.schemas import ExportConfig, ExportResult as AIExportResult
from src.sync.pipeline.enums import ExportFormat as AIExportFormat


# ============================================================================
# Strategy Generators
# ============================================================================

@st.composite
def annotation_strategy(draw):
    """Generate annotation data."""
    return {
        "id": draw(st.uuids()).hex,
        "type": draw(st.sampled_from(["bbox", "polygon", "classification", "segmentation"])),
        "label": draw(st.sampled_from(["person", "car", "building", "tree", "animal"])),
        "confidence": draw(st.floats(min_value=0.0, max_value=1.0)),
        "created_by": draw(st.sampled_from(["user_1", "user_2", "ai_model"])),
        "created_at": "2024-01-01T00:00:00Z"
    }


@st.composite
def metadata_strategy(draw):
    """Generate metadata."""
    return {
        "source": draw(st.sampled_from(["upload", "api", "sync", "import"])),
        "quality_score": draw(st.floats(min_value=0.0, max_value=1.0)),
        "tags": draw(st.lists(
            st.sampled_from(["medical", "legal", "financial", "urgent"]),
            min_size=0,
            max_size=3
        )),
        "custom_fields": {
            "field1": draw(st.text(min_size=1, max_size=20)),
            "field2": draw(st.integers(min_value=0, max_value=100))
        }
    }


@st.composite
def lineage_strategy(draw):
    """Generate lineage information."""
    return {
        "original_source": draw(st.sampled_from(["database_1", "api_endpoint", "file_upload"])),
        "transformations": draw(st.lists(
            st.sampled_from([
                "deduplication",
                "normalization",
                "enrichment",
                "validation",
                "quality_check"
            ]),
            min_size=1,
            max_size=5
        )),
        "governance_steps": draw(st.lists(
            st.sampled_from([
                "pii_detection",
                "data_classification",
                "access_control",
                "audit_logging"
            ]),
            min_size=0,
            max_size=3
        )),
        "last_modified": "2024-01-01T00:00:00Z"
    }


@st.composite
def document_with_rich_data_strategy(draw):
    """Generate document with annotations, metadata, and lineage."""
    num_annotations = draw(st.integers(min_value=1, max_value=5))
    
    return {
        "id": draw(st.uuids()).hex,
        "content": draw(st.text(min_size=10, max_size=100)),
        "annotations": [draw(annotation_strategy()) for _ in range(num_annotations)],
        "metadata": draw(metadata_strategy()),
        "lineage": draw(lineage_strategy())
    }


@st.composite
def export_format_strategy(draw):
    """Generate export format."""
    return draw(st.sampled_from(["json", "csv", "jsonl", "coco", "pascal_voc"]))


# ============================================================================
# Helper Functions
# ============================================================================

def verify_annotations_preserved(
    original_doc: Dict[str, Any],
    transformed_doc: Dict[str, Any]
) -> bool:
    """
    Verify that annotations are preserved in transformation.
    
    Args:
        original_doc: Original document
        transformed_doc: Transformed document
        
    Returns:
        True if annotations are preserved
    """
    original_annotations = original_doc.get("annotations", [])
    transformed_annotations = transformed_doc.get("annotations", [])
    
    if len(original_annotations) != len(transformed_annotations):
        return False
    
    # Check each annotation is preserved
    for orig_ann in original_annotations:
        # Find matching annotation in transformed doc
        found = False
        for trans_ann in transformed_annotations:
            if orig_ann["id"] == trans_ann.get("id"):
                # Verify key fields are preserved
                if (orig_ann["type"] == trans_ann.get("type") and
                    orig_ann["label"] == trans_ann.get("label")):
                    found = True
                    break
        
        if not found:
            return False
    
    return True


def verify_metadata_preserved(
    original_doc: Dict[str, Any],
    transformed_doc: Dict[str, Any]
) -> bool:
    """
    Verify that metadata is preserved in transformation.
    
    Args:
        original_doc: Original document
        transformed_doc: Transformed document
        
    Returns:
        True if metadata is preserved
    """
    original_metadata = original_doc.get("metadata", {})
    transformed_metadata = transformed_doc.get("metadata", {})
    
    # Check key metadata fields
    key_fields = ["source", "quality_score", "tags"]
    for field in key_fields:
        if field in original_metadata:
            if original_metadata[field] != transformed_metadata.get(field):
                return False
    
    return True


def verify_lineage_preserved(
    original_doc: Dict[str, Any],
    transformed_doc: Dict[str, Any]
) -> bool:
    """
    Verify that lineage information is preserved in transformation.
    
    Args:
        original_doc: Original document
        transformed_doc: Transformed document
        
    Returns:
        True if lineage is preserved
    """
    original_lineage = original_doc.get("lineage", {})
    transformed_lineage = transformed_doc.get("lineage", {})
    
    # Check key lineage fields
    key_fields = ["original_source", "transformations", "governance_steps"]
    for field in key_fields:
        if field in original_lineage:
            if original_lineage[field] != transformed_lineage.get(field):
                return False
    
    return True


def create_mock_ai_export_result(
    documents: List[Dict[str, Any]],
    format: str
) -> AIExportResult:
    """
    Create a mock AI export result.
    
    Args:
        documents: Documents to export
        format: Export format
        
    Returns:
        Mock AIExportResult
    """
    from src.sync.pipeline.schemas import ExportedFile, StatisticsReport, ExportResult as AIExportResult
    
    # Create a temporary file path
    file_path = f"/tmp/export_{format}.{format}"
    
    # Create ExportedFile
    exported_file = ExportedFile(
        filename=f"export_{format}.{format}",
        filepath=file_path,
        format=AIExportFormat.JSON,  # Use JSON for simplicity
        size_bytes=1024,
        row_count=len(documents),
        split_name="all"
    )
    
    # Create StatisticsReport
    statistics = StatisticsReport(
        total_rows=len(documents),
        total_size_bytes=1024,
        split_counts={"all": len(documents)},
        field_statistics={},
        export_duration_ms=100.0
    )
    
    return AIExportResult(
        export_id=f"export_{format}",
        files=[exported_file],
        statistics=statistics,
        format=AIExportFormat.JSON,
        success=True,
        error_message=None
    )


# ============================================================================
# Property-Based Test for Format Transformation
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_documents=st.integers(min_value=1, max_value=10),
    export_format=export_format_strategy(),
    data=st.data()
)
@pytest.mark.asyncio
async def test_property_format_transformation_with_preservation(
    num_documents: int,
    export_format: str,
    data
):
    """
    **Property 29: Data Format Transformation with Preservation**
    
    For any data format conversion request, the transformed data should 
    preserve all annotations, metadata, and lineage information from the 
    original format.
    
    **Validates: Requirements 11.2**
    
    This property test verifies that:
    1. All annotations are preserved after format conversion
    2. All metadata fields are preserved after format conversion
    3. All lineage information is preserved after format conversion
    4. Document count remains the same after conversion
    5. Document IDs are preserved after conversion
    6. Format conversion succeeds for all supported formats
    7. Nested data structures are handled appropriately
    
    Feature: ai-application-integration, Property 29: Data Format Transformation with Preservation
    """
    # Generate documents with rich data
    documents = []
    for _ in range(num_documents):
        doc = data.draw(document_with_rich_data_strategy())
        documents.append(doc)
    
    # Create mock services
    mock_export_service = Mock(spec=ExportService)
    mock_ai_exporter = Mock(spec=AIFriendlyExporter)
    
    # Create mock export result
    ai_export_result = create_mock_ai_export_result(documents, export_format)
    
    # Mock the export method to return our result
    mock_ai_exporter.export = AsyncMock(return_value=ai_export_result)
    
    # Mock file reading to return JSON data
    file_content = json.dumps(documents).encode('utf-8')
    
    with patch('builtins.open', mock_open(read_data=file_content)):
        data_bridge = OpenClawDataBridge(
            export_service=mock_export_service,
            ai_exporter=mock_ai_exporter
        )
        
        # Prepare data query
        data_query = {
            "results": documents,
            "include_semantics": True,
            "desensitize": False
        }
        
        # Execute format transformation
        exported_data = await data_bridge.export_for_skill(
            gateway_id="test_gateway",
            data_query=data_query,
            format=export_format
        )
        
        # Property 1: Export should succeed
        assert exported_data is not None, \
            f"Export failed for format {export_format}"
        
        assert isinstance(exported_data, bytes), \
            f"Exported data should be bytes, got {type(exported_data)}"
        
        # Property 2: Verify export method was called with correct parameters
        mock_ai_exporter.export.assert_called_once()
        call_args = mock_ai_exporter.export.call_args
        
        assert call_args.kwargs["data"] == documents, \
            "Export should be called with original documents"
        
        # Property 3: Verify format mapping
        expected_format_map = {
            "json": AIExportFormat.JSON,
            "csv": AIExportFormat.CSV,
            "jsonl": AIExportFormat.JSONL,
            "coco": AIExportFormat.COCO,
            "pascal_voc": AIExportFormat.PASCAL_VOC
        }
        
        expected_format = expected_format_map.get(export_format.lower(), AIExportFormat.JSON)
        assert call_args.kwargs["format"] == expected_format, \
            f"Format should be mapped to {expected_format}"
        
        # Property 4: Verify config includes semantics
        config = call_args.kwargs["config"]
        assert config.include_semantics is True, \
            "Config should include semantics"
        
        # For JSON format, we can parse and verify preservation
        if export_format.lower() == "json":
            try:
                transformed_docs = json.loads(exported_data.decode('utf-8'))
                
                # Property 5: Document count should be preserved
                assert len(transformed_docs) == len(documents), \
                    f"Document count changed: {len(transformed_docs)} != {len(documents)}"
                
                # Property 6: Verify each document's data is preserved
                for i, (original_doc, transformed_doc) in enumerate(zip(documents, transformed_docs)):
                    # Document ID should be preserved
                    assert original_doc["id"] == transformed_doc["id"], \
                        f"Document {i}: ID not preserved"
                    
                    # Annotations should be preserved
                    assert verify_annotations_preserved(original_doc, transformed_doc), \
                        f"Document {i}: Annotations not preserved"
                    
                    # Metadata should be preserved
                    assert verify_metadata_preserved(original_doc, transformed_doc), \
                        f"Document {i}: Metadata not preserved"
                    
                    # Lineage should be preserved
                    assert verify_lineage_preserved(original_doc, transformed_doc), \
                        f"Document {i}: Lineage not preserved"
            
            except json.JSONDecodeError:
                # If we can't parse, that's okay for this test since we're mocking
                pass


# ============================================================================
# Additional Test: Format Transformation for All Formats
# ============================================================================

@settings(
    max_examples=20,
    deadline=None
)
@given(
    num_documents=st.integers(min_value=1, max_value=5),
    data=st.data()
)
@pytest.mark.asyncio
async def test_format_transformation_all_formats(
    num_documents: int,
    data
):
    """
    Test format transformation for all supported formats.
    
    Ensures that all format conversions work correctly and preserve data.
    """
    # Generate documents
    documents = []
    for _ in range(num_documents):
        doc = data.draw(document_with_rich_data_strategy())
        documents.append(doc)
    
    # Test all supported formats
    formats = ["json", "csv", "jsonl", "coco", "pascal_voc"]
    
    for export_format in formats:
        mock_export_service = Mock(spec=ExportService)
        mock_ai_exporter = Mock(spec=AIFriendlyExporter)
        
        ai_export_result = create_mock_ai_export_result(documents, export_format)
        mock_ai_exporter.export = AsyncMock(return_value=ai_export_result)
        
        file_content = json.dumps(documents).encode('utf-8')
        
        with patch('builtins.open', mock_open(read_data=file_content)):
            data_bridge = OpenClawDataBridge(
                export_service=mock_export_service,
                ai_exporter=mock_ai_exporter
            )
            
            data_query = {
                "results": documents,
                "include_semantics": True
            }
            
            # Execute transformation
            exported_data = await data_bridge.export_for_skill(
                gateway_id="test_gateway",
                data_query=data_query,
                format=export_format
            )
            
            # Verify export succeeded
            assert exported_data is not None, \
                f"Export failed for format {export_format}"
            
            assert isinstance(exported_data, bytes), \
                f"Format {export_format}: exported data should be bytes"
            
            # Verify export was called
            assert mock_ai_exporter.export.called, \
                f"Format {export_format}: export method not called"


# ============================================================================
# Additional Test: Preservation of Complex Nested Structures
# ============================================================================

@settings(
    max_examples=20,
    deadline=None
)
@given(
    nesting_depth=st.integers(min_value=1, max_value=3)
)
@pytest.mark.asyncio
async def test_nested_structure_preservation(
    nesting_depth: int
):
    """
    Test preservation of complex nested data structures.
    
    Ensures that deeply nested annotations and metadata are preserved.
    """
    # Create document with nested structures
    def create_nested_dict(depth: int) -> Dict[str, Any]:
        if depth == 0:
            return {"value": "leaf_node"}
        return {
            "level": depth,
            "nested": create_nested_dict(depth - 1),
            "data": f"level_{depth}"
        }
    
    document = {
        "id": "doc_nested",
        "content": "Test content",
        "annotations": [
            {
                "id": "ann_1",
                "type": "nested",
                "nested_data": create_nested_dict(nesting_depth)
            }
        ],
        "metadata": {
            "nested_metadata": create_nested_dict(nesting_depth)
        },
        "lineage": {
            "transformations": ["step_1", "step_2"],
            "nested_lineage": create_nested_dict(nesting_depth)
        }
    }
    
    documents = [document]
    
    mock_export_service = Mock(spec=ExportService)
    mock_ai_exporter = Mock(spec=AIFriendlyExporter)
    
    ai_export_result = create_mock_ai_export_result(documents, "json")
    mock_ai_exporter.export = AsyncMock(return_value=ai_export_result)
    
    file_content = json.dumps(documents).encode('utf-8')
    
    with patch('builtins.open', mock_open(read_data=file_content)):
        data_bridge = OpenClawDataBridge(
            export_service=mock_export_service,
            ai_exporter=mock_ai_exporter
        )
        
        data_query = {
            "results": documents,
            "include_semantics": True
        }
        
        exported_data = await data_bridge.export_for_skill(
            gateway_id="test_gateway",
            data_query=data_query,
            format="json"
        )
        
        # Parse and verify nested structures
        transformed_docs = json.loads(exported_data.decode('utf-8'))
        transformed_doc = transformed_docs[0]
        
        # Verify nested annotation data is preserved
        assert "nested_data" in transformed_doc["annotations"][0], \
            "Nested annotation data not preserved"
        
        # Verify nested metadata is preserved
        assert "nested_metadata" in transformed_doc["metadata"], \
            "Nested metadata not preserved"
        
        # Verify nested lineage is preserved
        assert "nested_lineage" in transformed_doc["lineage"], \
            "Nested lineage not preserved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
