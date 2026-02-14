"""
Property-based tests for JSON response format in OpenClawDataBridge.

Tests that all successful data access requests return valid JSON that can be
parsed without errors.
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck

from src.ai_integration.data_bridge import OpenClawDataBridge
from src.export.service import ExportService
from src.export.models import ExportResult, ExportFormat
from src.sync.pipeline.ai_exporter import AIFriendlyExporter
from datetime import datetime


# ============================================================================
# Strategy Generators
# ============================================================================

@st.composite
def export_result_strategy(draw):
    """Generate valid ExportResult objects for testing."""
    export_id = draw(st.uuids()).hex
    status = draw(st.sampled_from(["completed", "success", "finished"]))
    format_type = draw(st.sampled_from([ExportFormat.JSON, ExportFormat.CSV, ExportFormat.COCO]))
    total_records = draw(st.integers(min_value=0, max_value=10000))
    exported_records = draw(st.integers(min_value=0, max_value=total_records))
    file_size = draw(st.integers(min_value=0, max_value=1000000))
    
    return ExportResult(
        export_id=export_id,
        status=status,
        format=format_type,
        total_records=total_records,
        exported_records=exported_records,
        file_path=f"/tmp/export_{export_id}.json",
        file_size=file_size,
        completed_at=datetime.utcnow(),
        error=None
    )


@st.composite
def query_filters_strategy(draw):
    """Generate various query filter combinations."""
    filters = {}
    
    # Randomly include different filter types
    if draw(st.booleans()):
        filters["format"] = draw(st.sampled_from(["json", "csv", "coco"]))
    
    if draw(st.booleans()):
        filters["project_id"] = draw(st.uuids()).hex
    
    if draw(st.booleans()):
        filters["include_annotations"] = draw(st.booleans())
    
    if draw(st.booleans()):
        filters["include_metadata"] = draw(st.booleans())
    
    if draw(st.booleans()):
        filters["batch_size"] = draw(st.integers(min_value=100, max_value=5000))
    
    return filters


# ============================================================================
# Property-Based Test for JSON Response Format
# ============================================================================

@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    export_result=export_result_strategy(),
    query_filters=query_filters_strategy(),
    num_queries=st.integers(min_value=1, max_value=10)
)
@pytest.mark.asyncio
async def test_property_json_response_format(
    export_result: ExportResult,
    query_filters: dict,
    num_queries: int
):
    """
    **Property 7: JSON Response Format**
    
    For any successful data access request, the response should be valid JSON 
    that can be parsed without errors.
    
    **Validates: Requirements 3.3**
    
    This property test verifies that:
    1. All successful query_governed_data responses are valid JSON
    2. JSON can be parsed without errors
    3. Response structure is consistent across different queries
    4. All expected fields are present in the response
    5. Field types are correct and consistent
    
    Feature: ai-application-integration, Property 7: JSON Response Format
    """
    # Create mock services
    mock_export_service = Mock(spec=ExportService)
    mock_ai_exporter = Mock(spec=AIFriendlyExporter)
    
    # Configure mock to return the generated export result
    mock_export_service.start_export.return_value = export_result.export_id
    mock_export_service.export_data_optimized.return_value = export_result
    
    # Create data bridge
    data_bridge = OpenClawDataBridge(
        export_service=mock_export_service,
        ai_exporter=mock_ai_exporter
    )
    
    # Test multiple queries with the same configuration
    for query_idx in range(num_queries):
        gateway_id = f"gateway_{query_idx}"
        tenant_id = f"tenant_{query_idx % 3}"  # Rotate through 3 tenants
        
        # Execute query
        response = await data_bridge.query_governed_data(
            gateway_id=gateway_id,
            tenant_id=tenant_id,
            filters=query_filters
        )
        
        # Property 1: Response must be a dictionary (JSON-serializable)
        assert isinstance(response, dict), \
            f"Response must be a dictionary, got {type(response)}"
        
        # Property 2: Response must be JSON-serializable
        try:
            json_string = json.dumps(response)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Response is not JSON-serializable: {e}")
        
        # Property 3: Serialized JSON must be parseable
        try:
            parsed_response = json.loads(json_string)
        except json.JSONDecodeError as e:
            pytest.fail(f"Serialized JSON cannot be parsed: {e}")
        
        # Property 4: Parsed response must equal original response
        assert parsed_response == response, \
            "Parsed JSON should equal original response"
        
        # Property 5: Response must contain required fields
        required_fields = [
            "export_id",
            "status",
            "format",
            "total_records",
            "exported_records",
            "file_path",
            "file_size"
        ]
        
        for field in required_fields:
            assert field in response, \
                f"Response missing required field: {field}"
        
        # Property 6: Field types must be correct
        assert isinstance(response["export_id"], str), \
            "export_id must be a string"
        assert isinstance(response["status"], str), \
            "status must be a string"
        assert isinstance(response["format"], str), \
            "format must be a string"
        assert isinstance(response["total_records"], int), \
            "total_records must be an integer"
        assert isinstance(response["exported_records"], int), \
            "exported_records must be an integer"
        assert isinstance(response["file_path"], str), \
            "file_path must be a string"
        assert isinstance(response["file_size"], int), \
            "file_size must be an integer"
        
        # Property 7: Optional fields must be None or correct type
        if response.get("completed_at") is not None:
            assert isinstance(response["completed_at"], str), \
                "completed_at must be a string (ISO format) when present"
            # Verify it's a valid ISO format datetime
            try:
                datetime.fromisoformat(response["completed_at"])
            except ValueError:
                pytest.fail(f"completed_at is not valid ISO format: {response['completed_at']}")
        
        if response.get("error") is not None:
            assert isinstance(response["error"], str), \
                "error must be a string when present"
        
        # Property 8: Numeric fields must be non-negative
        assert response["total_records"] >= 0, \
            "total_records must be non-negative"
        assert response["exported_records"] >= 0, \
            "exported_records must be non-negative"
        assert response["file_size"] >= 0, \
            "file_size must be non-negative"
        
        # Property 9: exported_records should not exceed total_records
        assert response["exported_records"] <= response["total_records"], \
            "exported_records should not exceed total_records"
        
        # Property 10: Response structure must be consistent across queries
        # All responses should have the same set of keys
        if query_idx == 0:
            first_response_keys = set(response.keys())
        else:
            current_response_keys = set(response.keys())
            assert current_response_keys == first_response_keys, \
                f"Response structure inconsistent: {current_response_keys} != {first_response_keys}"


# ============================================================================
# Additional Test: JSON Response with Various Data Types
# ============================================================================

@settings(
    max_examples=20,
    deadline=None
)
@given(
    total_records=st.integers(min_value=0, max_value=10000),
    exported_records=st.integers(min_value=0, max_value=10000),
    file_size=st.integers(min_value=0, max_value=1000000),
    has_error=st.booleans(),
    has_completed_at=st.booleans()
)
@pytest.mark.asyncio
async def test_json_response_with_various_data_types(
    total_records: int,
    exported_records: int,
    file_size: int,
    has_error: bool,
    has_completed_at: bool
):
    """
    Test JSON response format with various data type combinations.
    
    Ensures that responses with different field combinations are all valid JSON.
    """
    # Ensure exported_records doesn't exceed total_records
    if exported_records > total_records:
        exported_records = total_records
    
    # Create mock services
    mock_export_service = Mock(spec=ExportService)
    mock_ai_exporter = Mock(spec=AIFriendlyExporter)
    
    # Create export result with various field combinations
    export_result = ExportResult(
        export_id="test_export_123",
        status="completed",
        format=ExportFormat.JSON,
        total_records=total_records,
        exported_records=exported_records,
        file_path="/tmp/export_test.json",
        file_size=file_size,
        completed_at=datetime.utcnow() if has_completed_at else None,
        error="Test error message" if has_error else None
    )
    
    mock_export_service.start_export.return_value = export_result.export_id
    mock_export_service.export_data_optimized.return_value = export_result
    
    # Create data bridge
    data_bridge = OpenClawDataBridge(
        export_service=mock_export_service,
        ai_exporter=mock_ai_exporter
    )
    
    # Execute query
    response = await data_bridge.query_governed_data(
        gateway_id="test_gateway",
        tenant_id="test_tenant",
        filters={}
    )
    
    # Verify JSON serialization works
    try:
        json_string = json.dumps(response)
        parsed = json.loads(json_string)
        assert parsed == response
    except Exception as e:
        pytest.fail(f"JSON serialization failed: {e}")
    
    # Verify all fields are present and correct type
    assert isinstance(response["total_records"], int)
    assert isinstance(response["exported_records"], int)
    assert isinstance(response["file_size"], int)
    
    if has_error:
        assert response["error"] is not None
        assert isinstance(response["error"], str)
    
    if has_completed_at:
        assert response["completed_at"] is not None
        assert isinstance(response["completed_at"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
