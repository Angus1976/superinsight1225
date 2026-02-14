"""
Unit tests for WorkflowDesigner.

Tests workflow parsing, validation, execution, and comparison functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.ai_integration.workflow_designer import (
    WorkflowDesigner,
    WorkflowDefinition,
    ValidationResult,
    WorkflowResult,
    ComparisonResult
)
from src.ai.llm_schemas import LLMResponse, TokenUsage


@pytest.fixture
def mock_data_bridge():
    """Mock OpenClawDataBridge."""
    bridge = Mock()
    bridge.query_governed_data = AsyncMock(return_value={
        "data": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200}
        ]
    })
    return bridge


@pytest.fixture
def mock_authorization_service():
    """Mock AuthorizationService."""
    service = Mock()
    service.check_permission = Mock(return_value=True)
    return service


@pytest.fixture
def mock_llm_switcher():
    """Mock LLMSwitcher."""
    switcher = Mock()
    
    # Mock LLM response for workflow parsing
    llm_response = LLMResponse(
        content='{"name": "Test Workflow", "data_sources": [{"type": "dataset", "identifier": "test_dataset", "filters": {}, "use_governed": true}], "steps": [{"step_type": "filter", "parameters": {"field": "value", "operator": "greater_than", "value": 50}, "description": "Filter by value"}], "output": {"format": "json", "destination": "api_response", "include_quality_metrics": true}}',
        provider="openai",
        model="gpt-4",
        usage=TokenUsage(prompt_tokens=100, completion_tokens=200, total_tokens=300),
        latency_ms=500.0
    )
    
    switcher.generate = AsyncMock(return_value=llm_response)
    return switcher


@pytest.fixture
async def workflow_designer(mock_data_bridge, mock_authorization_service, mock_llm_switcher):
    """Create WorkflowDesigner instance."""
    designer = WorkflowDesigner(
        data_bridge=mock_data_bridge,
        authorization_service=mock_authorization_service,
        llm_switcher=mock_llm_switcher,
        tenant_id="test_tenant"
    )
    await designer.initialize()
    return designer


@pytest.mark.asyncio
async def test_parse_workflow_description(workflow_designer, mock_llm_switcher):
    """Test parsing natural language workflow description."""
    description = "Analyze customer feedback from last quarter, filter negative sentiment"
    
    workflow = await workflow_designer.parse_workflow_description(
        description=description,
        tenant_id="test_tenant"
    )
    
    # Verify workflow was created
    assert workflow is not None
    assert workflow.name == "Test Workflow"
    assert workflow.description == description
    assert workflow.tenant_id == "test_tenant"
    assert len(workflow.data_sources) == 1
    assert len(workflow.steps) == 1
    
    # Verify LLM was called
    mock_llm_switcher.generate.assert_called_once()


@pytest.mark.asyncio
async def test_validate_workflow_valid(workflow_designer):
    """Test workflow validation with valid workflow."""
    workflow = WorkflowDefinition(
        id="test_id",
        name="Test Workflow",
        description="Test description",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "test_dataset",
                "filters": {},
                "use_governed": True
            }
        ],
        steps=[
            {
                "step_type": "filter",
                "parameters": {"field": "value"},
                "description": "Filter step"
            }
        ],
        output={"format": "json"}
    )
    
    result = await workflow_designer.validate_workflow(workflow, "test_tenant")
    
    assert result.is_valid is True
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_validate_workflow_missing_data_source(workflow_designer):
    """Test workflow validation with missing data source info."""
    workflow = WorkflowDefinition(
        id="test_id",
        name="Test Workflow",
        description="Test description",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset"
                # Missing identifier
            }
        ],
        steps=[],
        output={"format": "json"}
    )
    
    result = await workflow_designer.validate_workflow(workflow, "test_tenant")
    
    assert result.is_valid is False
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_validate_workflow_missing_output_format(workflow_designer):
    """Test workflow validation with missing output format."""
    workflow = WorkflowDefinition(
        id="test_id",
        name="Test Workflow",
        description="Test description",
        tenant_id="test_tenant",
        data_sources=[],
        steps=[],
        output={}  # Missing format
    )
    
    result = await workflow_designer.validate_workflow(workflow, "test_tenant")
    
    assert result.is_valid is False
    assert any("format" in error.lower() for error in result.errors)


@pytest.mark.asyncio
async def test_execute_workflow_with_governed_data(workflow_designer, mock_data_bridge):
    """Test workflow execution with governed data."""
    # Create and store workflow
    workflow = WorkflowDefinition(
        id="test_workflow_id",
        name="Test Workflow",
        description="Test description",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "test_dataset",
                "filters": {},
                "use_governed": True
            }
        ],
        steps=[],
        output={"format": "json"}
    )
    workflow_designer._workflows[workflow.id] = workflow
    
    # Execute workflow
    result = await workflow_designer.execute_workflow(
        workflow_id=workflow.id,
        use_governed_data=True
    )
    
    assert result.status == "completed"
    assert result.workflow_id == workflow.id
    assert result.data is not None
    assert result.quality_metrics is not None
    assert result.quality_metrics["accuracy"] == 0.95  # Governed data has higher accuracy


@pytest.mark.asyncio
async def test_execute_workflow_with_raw_data(workflow_designer, mock_data_bridge):
    """Test workflow execution with raw data."""
    # Create and store workflow
    workflow = WorkflowDefinition(
        id="test_workflow_id",
        name="Test Workflow",
        description="Test description",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "test_dataset",
                "filters": {},
                "use_governed": False
            }
        ],
        steps=[],
        output={"format": "json"}
    )
    workflow_designer._workflows[workflow.id] = workflow
    
    # Execute workflow
    result = await workflow_designer.execute_workflow(
        workflow_id=workflow.id,
        use_governed_data=False
    )
    
    assert result.status == "completed"
    assert result.quality_metrics["accuracy"] == 0.78  # Raw data has lower accuracy


@pytest.mark.asyncio
async def test_execute_workflow_not_found(workflow_designer):
    """Test workflow execution with non-existent workflow."""
    result = await workflow_designer.execute_workflow(
        workflow_id="non_existent_id",
        use_governed_data=True
    )
    
    assert result.status == "error"
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_compare_results(workflow_designer, mock_data_bridge):
    """Test comparing results between governed and raw data."""
    # Create and store workflow
    workflow = WorkflowDefinition(
        id="test_workflow_id",
        name="Test Workflow",
        description="Test description",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "test_dataset",
                "filters": {},
                "use_governed": True
            }
        ],
        steps=[],
        output={"format": "json"}
    )
    workflow_designer._workflows[workflow.id] = workflow
    
    # Compare results
    comparison = await workflow_designer.compare_results(workflow.id)
    
    assert comparison.workflow_id == workflow.id
    assert comparison.governed_result.status == "completed"
    assert comparison.raw_result.status == "completed"
    assert comparison.comparison_metrics is not None
    
    # Verify improvement metrics
    improvements = comparison.comparison_metrics["improvements"]
    assert improvements["accuracy"] > 0  # Governed should be better
    assert improvements["overall"] > 0


@pytest.mark.asyncio
async def test_filter_step_execution(workflow_designer):
    """Test filter processing step."""
    data = [
        {"id": 1, "value": 100},
        {"id": 2, "value": 50},
        {"id": 3, "value": 200}
    ]
    
    parameters = {
        "field": "value",
        "operator": "greater_than",
        "value": 75
    }
    
    filtered = workflow_designer._apply_filter(data, parameters)
    
    assert len(filtered) == 2
    assert all(item["value"] > 75 for item in filtered)


@pytest.mark.asyncio
async def test_aggregate_step_execution(workflow_designer):
    """Test aggregate processing step."""
    data = [
        {"category": "A", "value": 100},
        {"category": "B", "value": 50},
        {"category": "A", "value": 200}
    ]
    
    parameters = {
        "group_by": "category"
    }
    
    aggregated = workflow_designer._apply_aggregate(data, parameters)
    
    assert len(aggregated) == 2
    assert any(item["category"] == "A" and item["count"] == 2 for item in aggregated)
    assert any(item["category"] == "B" and item["count"] == 1 for item in aggregated)


@pytest.mark.asyncio
async def test_quality_metrics_calculation(workflow_designer):
    """Test quality metrics calculation."""
    data = [
        {"id": 1, "name": "Item 1", "value": 100},
        {"id": 2, "name": "Item 2", "value": None},
        {"id": 3, "name": None, "value": 300}
    ]
    
    # Test with governed data
    governed_metrics = workflow_designer._calculate_quality_metrics(data, is_governed=True)
    
    assert governed_metrics["record_count"] == 3
    assert 0 <= governed_metrics["completeness"] <= 1
    assert governed_metrics["accuracy"] == 0.95
    assert governed_metrics["consistency"] == 0.92
    
    # Test with raw data
    raw_metrics = workflow_designer._calculate_quality_metrics(data, is_governed=False)
    
    assert raw_metrics["accuracy"] == 0.78
    assert raw_metrics["consistency"] == 0.75
    assert raw_metrics["accuracy"] < governed_metrics["accuracy"]


@pytest.mark.asyncio
async def test_workflow_definition_to_dict(workflow_designer):
    """Test WorkflowDefinition serialization."""
    workflow = WorkflowDefinition(
        id="test_id",
        name="Test Workflow",
        description="Test description",
        tenant_id="test_tenant",
        data_sources=[],
        steps=[],
        output={"format": "json"}
    )
    
    workflow_dict = workflow.to_dict()
    
    assert workflow_dict["id"] == "test_id"
    assert workflow_dict["name"] == "Test Workflow"
    assert workflow_dict["tenant_id"] == "test_tenant"
    assert "created_at" in workflow_dict


@pytest.mark.asyncio
async def test_parse_llm_response_with_markdown(workflow_designer):
    """Test parsing LLM response with markdown code blocks."""
    content = """```json
{
  "name": "Test Workflow",
  "data_sources": [],
  "steps": [],
  "output": {"format": "json"}
}
```"""
    
    result = workflow_designer._parse_llm_response(content)
    
    assert result["name"] == "Test Workflow"
    assert "data_sources" in result
    assert "steps" in result


@pytest.mark.asyncio
async def test_parse_llm_response_invalid_json(workflow_designer):
    """Test parsing invalid JSON from LLM."""
    content = "This is not valid JSON"
    
    result = workflow_designer._parse_llm_response(content)
    
    # Should return minimal valid structure
    assert "name" in result
    assert "data_sources" in result
    assert "steps" in result
    assert "output" in result


# Additional comprehensive tests for task 23.3

@pytest.mark.asyncio
async def test_parse_workflow_complex_description(workflow_designer, mock_llm_switcher):
    """Test parsing complex natural language workflow with multiple steps."""
    description = """
    Create a workflow that:
    1. Fetches customer feedback data from the last 6 months
    2. Filters out entries with sentiment score below 3
    3. Groups by product category
    4. Calculates average sentiment per category
    5. Exports results as CSV
    """
    
    # Mock complex LLM response
    complex_response = LLMResponse(
        content='{"name": "Customer Feedback Analysis", "data_sources": [{"type": "dataset", "identifier": "customer_feedback", "filters": {"date_range": "6_months"}, "use_governed": true}], "steps": [{"step_type": "filter", "parameters": {"field": "sentiment_score", "operator": "greater_than", "value": 3}, "description": "Filter low sentiment"}, {"step_type": "aggregate", "parameters": {"group_by": "product_category", "aggregation": "average", "field": "sentiment_score"}, "description": "Group by category"}], "output": {"format": "csv", "destination": "api_response", "include_quality_metrics": true}}',
        provider="openai",
        model="gpt-4",
        usage=TokenUsage(prompt_tokens=150, completion_tokens=300, total_tokens=450),
        latency_ms=800.0
    )
    mock_llm_switcher.generate = AsyncMock(return_value=complex_response)
    
    workflow = await workflow_designer.parse_workflow_description(
        description=description,
        tenant_id="test_tenant"
    )
    
    # Verify complex workflow structure
    assert workflow.name == "Customer Feedback Analysis"
    assert len(workflow.data_sources) == 1
    assert workflow.data_sources[0]["type"] == "dataset"
    assert workflow.data_sources[0]["identifier"] == "customer_feedback"
    assert len(workflow.steps) == 2
    assert workflow.steps[0]["step_type"] == "filter"
    assert workflow.steps[1]["step_type"] == "aggregate"
    assert workflow.output["format"] == "csv"


@pytest.mark.asyncio
async def test_parse_workflow_fallback_on_llm_failure(workflow_designer, mock_llm_switcher):
    """Test fallback parsing when LLM fails."""
    description = "Analyze sales data"
    
    # Mock LLM failure
    mock_llm_switcher.generate = AsyncMock(side_effect=Exception("LLM service unavailable"))
    
    workflow = await workflow_designer.parse_workflow_description(
        description=description,
        tenant_id="test_tenant"
    )
    
    # Should still create a workflow with fallback structure
    assert workflow is not None
    assert workflow.name == "Parsed Workflow"
    assert workflow.description == description
    assert isinstance(workflow.data_sources, list)
    assert isinstance(workflow.steps, list)


@pytest.mark.asyncio
async def test_validate_workflow_missing_step_type(workflow_designer):
    """Test workflow validation with missing step type."""
    workflow = WorkflowDefinition(
        id="test_id",
        name="Test Workflow",
        description="Test description",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "test_dataset"
            }
        ],
        steps=[
            {
                "parameters": {"field": "value"},
                "description": "Missing step_type"
            }
        ],
        output={"format": "json"}
    )
    
    result = await workflow_designer.validate_workflow(workflow, "test_tenant")
    
    assert result.is_valid is False
    assert any("step" in error.lower() and "type" in error.lower() for error in result.errors)


@pytest.mark.asyncio
async def test_validate_workflow_no_steps_warning(workflow_designer):
    """Test workflow validation warns when no processing steps."""
    workflow = WorkflowDefinition(
        id="test_id",
        name="Test Workflow",
        description="Test description",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "test_dataset"
            }
        ],
        steps=[],  # No steps
        output={"format": "json"}
    )
    
    result = await workflow_designer.validate_workflow(workflow, "test_tenant")
    
    assert result.is_valid is True  # Valid but with warning
    assert len(result.warnings) > 0
    assert any("no processing steps" in warning.lower() for warning in result.warnings)


@pytest.mark.asyncio
async def test_execute_workflow_with_filter_step(workflow_designer, mock_data_bridge):
    """Test workflow execution with filter processing step."""
    # Mock data with various values
    mock_data_bridge.query_governed_data = AsyncMock(return_value={
        "data": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 50},
            {"id": 3, "name": "Item 3", "value": 200},
            {"id": 4, "name": "Item 4", "value": 30}
        ]
    })
    
    workflow = WorkflowDefinition(
        id="filter_workflow",
        name="Filter Workflow",
        description="Test filter",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "test_dataset",
                "filters": {}
            }
        ],
        steps=[
            {
                "step_type": "filter",
                "parameters": {
                    "field": "value",
                    "operator": "greater_than",
                    "value": 75
                },
                "description": "Filter items with value > 75"
            }
        ],
        output={"format": "json"}
    )
    workflow_designer._workflows[workflow.id] = workflow
    
    result = await workflow_designer.execute_workflow(
        workflow_id=workflow.id,
        use_governed_data=True
    )
    
    assert result.status == "completed"
    assert len(result.data) == 2  # Only items with value > 75
    assert all(item["value"] > 75 for item in result.data)


@pytest.mark.asyncio
async def test_execute_workflow_with_aggregate_step(workflow_designer, mock_data_bridge):
    """Test workflow execution with aggregate processing step."""
    # Mock data with categories
    mock_data_bridge.query_governed_data = AsyncMock(return_value={
        "data": [
            {"id": 1, "category": "A", "value": 100},
            {"id": 2, "category": "B", "value": 50},
            {"id": 3, "category": "A", "value": 200},
            {"id": 4, "category": "B", "value": 150}
        ]
    })
    
    workflow = WorkflowDefinition(
        id="aggregate_workflow",
        name="Aggregate Workflow",
        description="Test aggregate",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "test_dataset",
                "filters": {}
            }
        ],
        steps=[
            {
                "step_type": "aggregate",
                "parameters": {
                    "group_by": "category"
                },
                "description": "Group by category"
            }
        ],
        output={"format": "json"}
    )
    workflow_designer._workflows[workflow.id] = workflow
    
    result = await workflow_designer.execute_workflow(
        workflow_id=workflow.id,
        use_governed_data=True
    )
    
    assert result.status == "completed"
    assert len(result.data) == 2  # Two categories
    assert all("count" in item for item in result.data)


@pytest.mark.asyncio
async def test_execute_workflow_with_multiple_steps(workflow_designer, mock_data_bridge):
    """Test workflow execution with multiple processing steps."""
    mock_data_bridge.query_governed_data = AsyncMock(return_value={
        "data": [
            {"id": 1, "category": "A", "value": 100},
            {"id": 2, "category": "B", "value": 50},
            {"id": 3, "category": "A", "value": 200},
            {"id": 4, "category": "B", "value": 30}
        ]
    })
    
    workflow = WorkflowDefinition(
        id="multi_step_workflow",
        name="Multi-Step Workflow",
        description="Test multiple steps",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "test_dataset",
                "filters": {}
            }
        ],
        steps=[
            {
                "step_type": "filter",
                "parameters": {
                    "field": "value",
                    "operator": "greater_than",
                    "value": 40
                },
                "description": "Filter value > 40"
            },
            {
                "step_type": "aggregate",
                "parameters": {
                    "group_by": "category"
                },
                "description": "Group by category"
            }
        ],
        output={"format": "json"}
    )
    workflow_designer._workflows[workflow.id] = workflow
    
    result = await workflow_designer.execute_workflow(
        workflow_id=workflow.id,
        use_governed_data=True
    )
    
    assert result.status == "completed"
    # After filter (value > 40), should have 3 items
    # After aggregate, should have 2 groups
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_compare_results_quality_difference(workflow_designer, mock_data_bridge):
    """Test comparison shows quality difference between governed and raw data."""
    workflow = WorkflowDefinition(
        id="comparison_workflow",
        name="Comparison Workflow",
        description="Test comparison",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "test_dataset",
                "filters": {}
            }
        ],
        steps=[],
        output={"format": "json"}
    )
    workflow_designer._workflows[workflow.id] = workflow
    
    comparison = await workflow_designer.compare_results(workflow.id)
    
    # Verify both executions completed
    assert comparison.governed_result.status == "completed"
    assert comparison.raw_result.status == "completed"
    
    # Verify quality metrics exist
    assert comparison.governed_result.quality_metrics is not None
    assert comparison.raw_result.quality_metrics is not None
    
    # Verify governed data has better quality
    gov_quality = comparison.governed_result.quality_metrics["overall_quality"]
    raw_quality = comparison.raw_result.quality_metrics["overall_quality"]
    assert gov_quality > raw_quality
    
    # Verify comparison metrics
    improvements = comparison.comparison_metrics["improvements"]
    assert improvements["accuracy"] > 0
    assert improvements["consistency"] > 0
    assert improvements["overall"] > 0
    assert comparison.comparison_metrics["improvement_percentage"] > 0


@pytest.mark.asyncio
async def test_filter_step_equals_operator(workflow_designer):
    """Test filter step with equals operator."""
    data = [
        {"id": 1, "status": "active"},
        {"id": 2, "status": "inactive"},
        {"id": 3, "status": "active"}
    ]
    
    parameters = {
        "field": "status",
        "operator": "equals",
        "value": "active"
    }
    
    filtered = workflow_designer._apply_filter(data, parameters)
    
    assert len(filtered) == 2
    assert all(item["status"] == "active" for item in filtered)


@pytest.mark.asyncio
async def test_filter_step_contains_operator(workflow_designer):
    """Test filter step with contains operator."""
    data = [
        {"id": 1, "name": "Product ABC"},
        {"id": 2, "name": "Service XYZ"},
        {"id": 3, "name": "Product DEF"}
    ]
    
    parameters = {
        "field": "name",
        "operator": "contains",
        "value": "Product"
    }
    
    filtered = workflow_designer._apply_filter(data, parameters)
    
    assert len(filtered) == 2
    assert all("Product" in item["name"] for item in filtered)


@pytest.mark.asyncio
async def test_filter_step_less_than_operator(workflow_designer):
    """Test filter step with less_than operator."""
    data = [
        {"id": 1, "score": 85},
        {"id": 2, "score": 45},
        {"id": 3, "score": 92}
    ]
    
    parameters = {
        "field": "score",
        "operator": "less_than",
        "value": 50
    }
    
    filtered = workflow_designer._apply_filter(data, parameters)
    
    assert len(filtered) == 1
    assert filtered[0]["score"] == 45


@pytest.mark.asyncio
async def test_quality_metrics_empty_data(workflow_designer):
    """Test quality metrics calculation with empty data."""
    data = []
    
    metrics = workflow_designer._calculate_quality_metrics(data, is_governed=True)
    
    assert metrics["completeness"] == 0.0
    assert metrics["accuracy"] == 0.0
    assert metrics["consistency"] == 0.0
    assert metrics["record_count"] == 0
    assert metrics["overall_quality"] == 0.0


@pytest.mark.asyncio
async def test_quality_metrics_completeness_calculation(workflow_designer):
    """Test completeness metric calculation."""
    # Data with some null values
    data = [
        {"id": 1, "name": "Item 1", "value": 100, "category": "A"},
        {"id": 2, "name": None, "value": 200, "category": "B"},
        {"id": 3, "name": "Item 3", "value": None, "category": None}
    ]
    
    metrics = workflow_designer._calculate_quality_metrics(data, is_governed=True)
    
    # 3 records * 4 fields = 12 total fields
    # Non-null: id(3) + name(2) + value(2) + category(2) = 9
    # Completeness = 9/12 = 0.75
    assert metrics["completeness"] == 0.75
    assert metrics["record_count"] == 3


@pytest.mark.asyncio
async def test_comparison_metrics_calculation(workflow_designer):
    """Test comparison metrics calculation logic."""
    governed_result = WorkflowResult(
        workflow_id="test",
        execution_id="exec1",
        status="completed",
        data=[],
        quality_metrics={
            "completeness": 0.95,
            "accuracy": 0.95,
            "consistency": 0.92,
            "overall_quality": 0.94
        }
    )
    
    raw_result = WorkflowResult(
        workflow_id="test",
        execution_id="exec2",
        status="completed",
        data=[],
        quality_metrics={
            "completeness": 0.80,
            "accuracy": 0.78,
            "consistency": 0.75,
            "overall_quality": 0.78
        }
    )
    
    comparison_metrics = workflow_designer._calculate_comparison_metrics(
        governed_result,
        raw_result
    )
    
    # Verify improvements
    improvements = comparison_metrics["improvements"]
    assert improvements["completeness"] == pytest.approx(0.15, abs=0.01)
    assert improvements["accuracy"] == pytest.approx(0.17, abs=0.01)
    assert improvements["consistency"] == pytest.approx(0.17, abs=0.01)
    assert improvements["overall"] == pytest.approx(0.16, abs=0.01)
    assert comparison_metrics["improvement_percentage"] == pytest.approx(16.0, abs=1.0)


@pytest.mark.asyncio
async def test_workflow_execution_timing(workflow_designer, mock_data_bridge):
    """Test that workflow execution records timing information."""
    workflow = WorkflowDefinition(
        id="timing_workflow",
        name="Timing Test",
        description="Test timing",
        tenant_id="test_tenant",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "test_dataset",
                "filters": {}
            }
        ],
        steps=[],
        output={"format": "json"}
    )
    workflow_designer._workflows[workflow.id] = workflow
    
    result = await workflow_designer.execute_workflow(
        workflow_id=workflow.id,
        use_governed_data=True
    )
    
    assert result.execution_time_ms is not None
    assert result.execution_time_ms > 0


@pytest.mark.asyncio
async def test_parse_workflow_stores_in_workflows_dict(workflow_designer, mock_llm_switcher):
    """Test that parsed workflows are stored in the workflows dictionary."""
    description = "Test workflow storage"
    
    workflow = await workflow_designer.parse_workflow_description(
        description=description,
        tenant_id="test_tenant"
    )
    
    # Verify workflow is stored
    assert workflow.id in workflow_designer._workflows
    assert workflow_designer._workflows[workflow.id] == workflow


@pytest.mark.asyncio
async def test_validation_result_to_dict(workflow_designer):
    """Test ValidationResult serialization."""
    result = ValidationResult(
        is_valid=False,
        errors=["Error 1", "Error 2"],
        warnings=["Warning 1"]
    )
    
    result_dict = result.to_dict()
    
    assert result_dict["is_valid"] is False
    assert len(result_dict["errors"]) == 2
    assert len(result_dict["warnings"]) == 1


@pytest.mark.asyncio
async def test_workflow_result_to_dict(workflow_designer):
    """Test WorkflowResult serialization."""
    result = WorkflowResult(
        workflow_id="test_workflow",
        execution_id="exec_123",
        status="completed",
        data=[{"id": 1}],
        quality_metrics={"accuracy": 0.95},
        execution_time_ms=500.0
    )
    
    result_dict = result.to_dict()
    
    assert result_dict["workflow_id"] == "test_workflow"
    assert result_dict["execution_id"] == "exec_123"
    assert result_dict["status"] == "completed"
    assert result_dict["quality_metrics"]["accuracy"] == 0.95


@pytest.mark.asyncio
async def test_comparison_result_to_dict(workflow_designer):
    """Test ComparisonResult serialization."""
    governed = WorkflowResult(
        workflow_id="test",
        execution_id="exec1",
        status="completed",
        data=[],
        quality_metrics={"accuracy": 0.95}
    )
    
    raw = WorkflowResult(
        workflow_id="test",
        execution_id="exec2",
        status="completed",
        data=[],
        quality_metrics={"accuracy": 0.78}
    )
    
    comparison = ComparisonResult(
        workflow_id="test",
        governed_result=governed,
        raw_result=raw,
        comparison_metrics={"improvement_percentage": 17.0}
    )
    
    comparison_dict = comparison.to_dict()
    
    assert comparison_dict["workflow_id"] == "test"
    assert "governed_result" in comparison_dict
    assert "raw_result" in comparison_dict
    assert comparison_dict["comparison_metrics"]["improvement_percentage"] == 17.0
