"""
Tool Framework Unit Tests.

Tests for external tool call interface, tool selection and composition,
tool execution result validation, and tool call chain management.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.tool_framework import (
    ToolCategory,
    ToolStatus,
    ExecutionStatus,
    ToolParameter,
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolChainStep,
    ToolChain,
    BaseTool,
    FunctionTool,
    ToolRegistry,
    ToolSelector,
    ToolExecutor,
    ResultValidator,
    ToolFramework,
    get_tool_framework,
    create_function_tool,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_tool_definition():
    """Create a sample tool definition."""
    return ToolDefinition(
        name="test_tool",
        description="A test tool for unit testing",
        category=ToolCategory.DATA_PROCESSING,
        parameters=[
            ToolParameter(
                name="input_data",
                param_type="dict",
                description="Input data to process",
                required=True
            ),
            ToolParameter(
                name="options",
                param_type="dict",
                description="Processing options",
                required=False,
                default={}
            )
        ],
        tags=["test", "processing"],
        timeout=10.0
    )


@pytest.fixture
def sample_function_tool(sample_tool_definition):
    """Create a sample function tool."""
    async def test_func(input_data: dict, options: dict = None):
        return {"processed": True, "data": input_data}

    return FunctionTool(sample_tool_definition, test_func)


@pytest.fixture
def tool_registry():
    """Create a tool registry for testing."""
    return ToolRegistry()


@pytest.fixture
def tool_framework():
    """Create a tool framework for testing."""
    return ToolFramework()


# =============================================================================
# ToolParameter Tests
# =============================================================================

class TestToolParameter:
    """Tests for ToolParameter class."""

    def test_parameter_creation(self):
        """Test creating a parameter."""
        param = ToolParameter(
            name="data",
            param_type="dict",
            description="Input data",
            required=True
        )

        assert param.name == "data"
        assert param.param_type == "dict"
        assert param.required is True
        assert param.default is None

    def test_parameter_with_default(self):
        """Test parameter with default value."""
        param = ToolParameter(
            name="limit",
            param_type="int",
            required=False,
            default=10
        )

        assert param.required is False
        assert param.default == 10

    def test_parameter_with_validators(self):
        """Test parameter with validators."""
        def positive_validator(val):
            return val > 0

        param = ToolParameter(
            name="count",
            param_type="int",
            validators=[positive_validator]
        )

        assert len(param.validators) == 1


# =============================================================================
# ToolDefinition Tests
# =============================================================================

class TestToolDefinition:
    """Tests for ToolDefinition class."""

    def test_definition_creation(self, sample_tool_definition):
        """Test creating a tool definition."""
        assert sample_tool_definition.name == "test_tool"
        assert sample_tool_definition.category == ToolCategory.DATA_PROCESSING
        assert len(sample_tool_definition.parameters) == 2
        assert sample_tool_definition.timeout == 10.0

    def test_definition_defaults(self):
        """Test definition default values."""
        definition = ToolDefinition(
            name="simple_tool",
            description="Simple tool",
            category=ToolCategory.ANALYSIS
        )

        assert definition.version == "1.0.0"
        assert definition.max_retries == 3
        assert definition.requires_auth is False
        assert definition.rate_limit is None


# =============================================================================
# ToolExecutionRequest Tests
# =============================================================================

class TestToolExecutionRequest:
    """Tests for ToolExecutionRequest class."""

    def test_request_creation(self):
        """Test creating an execution request."""
        request = ToolExecutionRequest(
            tool_name="test_tool",
            parameters={"key": "value"}
        )

        assert request.id is not None
        assert request.tool_name == "test_tool"
        assert request.parameters == {"key": "value"}
        assert request.priority == 0

    def test_request_with_context(self):
        """Test request with context."""
        request = ToolExecutionRequest(
            tool_name="test_tool",
            parameters={"key": "value"},
            context={"user_id": "user_001"},
            priority=5
        )

        assert request.context["user_id"] == "user_001"
        assert request.priority == 5


# =============================================================================
# ToolExecutionResult Tests
# =============================================================================

class TestToolExecutionResult:
    """Tests for ToolExecutionResult class."""

    def test_result_creation(self):
        """Test creating an execution result."""
        result = ToolExecutionResult(
            request_id="req_001",
            tool_name="test_tool",
            status=ExecutionStatus.COMPLETED,
            result={"output": "data"}
        )

        assert result.request_id == "req_001"
        assert result.status == ExecutionStatus.COMPLETED
        assert result.result == {"output": "data"}
        assert result.error is None

    def test_result_is_success_true(self):
        """Test is_success returns True for completed without error."""
        result = ToolExecutionResult(
            request_id="req_001",
            tool_name="test_tool",
            status=ExecutionStatus.COMPLETED,
            result={"output": "data"}
        )

        assert result.is_success() is True

    def test_result_is_success_false_failed(self):
        """Test is_success returns False for failed status."""
        result = ToolExecutionResult(
            request_id="req_001",
            tool_name="test_tool",
            status=ExecutionStatus.FAILED,
            error="Execution failed"
        )

        assert result.is_success() is False

    def test_result_is_success_false_with_error(self):
        """Test is_success returns False when there's an error."""
        result = ToolExecutionResult(
            request_id="req_001",
            tool_name="test_tool",
            status=ExecutionStatus.COMPLETED,
            error="Some error occurred"
        )

        assert result.is_success() is False


# =============================================================================
# ToolChainStep Tests
# =============================================================================

class TestToolChainStep:
    """Tests for ToolChainStep class."""

    def test_step_creation(self):
        """Test creating a chain step."""
        step = ToolChainStep(
            tool_name="process_data",
            parameters={"input": "data"}
        )

        assert step.step_id is not None
        assert step.tool_name == "process_data"
        assert step.on_failure == "abort"

    def test_step_with_mappings(self):
        """Test step with input mappings."""
        step = ToolChainStep(
            tool_name="analyze",
            parameters={},
            input_mappings={"data": "step1_output"},
            output_key="analysis_result"
        )

        assert step.input_mappings["data"] == "step1_output"
        assert step.output_key == "analysis_result"


# =============================================================================
# ToolChain Tests
# =============================================================================

class TestToolChain:
    """Tests for ToolChain class."""

    def test_chain_creation(self):
        """Test creating a tool chain."""
        chain = ToolChain(
            name="Data Pipeline",
            description="Process and analyze data"
        )

        assert chain.id is not None
        assert chain.name == "Data Pipeline"
        assert chain.status == ExecutionStatus.PENDING
        assert chain.steps == []

    def test_chain_with_steps(self):
        """Test chain with multiple steps."""
        chain = ToolChain(
            name="Pipeline",
            steps=[
                ToolChainStep(tool_name="fetch_data"),
                ToolChainStep(tool_name="process_data"),
                ToolChainStep(tool_name="analyze_data")
            ]
        )

        assert len(chain.steps) == 3
        assert chain.current_step == 0


# =============================================================================
# FunctionTool Tests
# =============================================================================

class TestFunctionTool:
    """Tests for FunctionTool class."""

    def test_sync_function_tool(self, sample_tool_definition):
        """Test tool with synchronous function."""
        def sync_func(input_data: dict, options: dict = None):
            return {"result": input_data}

        tool = FunctionTool(sample_tool_definition, sync_func)

        assert tool.is_async is False
        assert tool.status == ToolStatus.AVAILABLE

    def test_async_function_tool(self, sample_tool_definition):
        """Test tool with asynchronous function."""
        async def async_func(input_data: dict, options: dict = None):
            return {"result": input_data}

        tool = FunctionTool(sample_tool_definition, async_func)

        assert tool.is_async is True

    @pytest.mark.asyncio
    async def test_execute_async_tool(self, sample_function_tool):
        """Test executing async function tool."""
        result = await sample_function_tool.execute(
            {"input_data": {"key": "value"}}
        )

        assert result["processed"] is True
        assert result["data"] == {"key": "value"}

    def test_validate_parameters_success(self, sample_function_tool):
        """Test parameter validation success."""
        errors = sample_function_tool.validate_parameters(
            {"input_data": {"key": "value"}}
        )

        assert errors == []

    def test_validate_parameters_missing_required(self, sample_function_tool):
        """Test parameter validation with missing required param."""
        errors = sample_function_tool.validate_parameters({})

        assert len(errors) == 1
        assert "input_data" in errors[0]

    def test_validate_parameters_wrong_type(self, sample_function_tool):
        """Test parameter validation with wrong type."""
        errors = sample_function_tool.validate_parameters(
            {"input_data": "not_a_dict"}
        )

        assert len(errors) == 1
        assert "dict" in errors[0]

    def test_get_metrics(self, sample_function_tool):
        """Test getting tool metrics."""
        sample_function_tool.call_count = 10
        sample_function_tool.error_count = 2
        sample_function_tool.total_execution_time = 5.0

        metrics = sample_function_tool.get_metrics()

        assert metrics["call_count"] == 10
        assert metrics["error_count"] == 2
        assert metrics["error_rate"] == 0.2
        assert metrics["avg_execution_time"] == 0.5


# =============================================================================
# ToolRegistry Tests
# =============================================================================

class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_register_tool(self, tool_registry, sample_function_tool):
        """Test registering a tool."""
        tool_registry.register(sample_function_tool)

        assert "test_tool" in tool_registry.tools
        assert tool_registry.get_tool("test_tool") == sample_function_tool

    def test_register_with_aliases(self, tool_registry, sample_function_tool):
        """Test registering tool with aliases."""
        tool_registry.register(sample_function_tool, aliases=["tt", "test"])

        assert tool_registry.get_tool("tt") == sample_function_tool
        assert tool_registry.get_tool("test") == sample_function_tool

    def test_unregister_tool(self, tool_registry, sample_function_tool):
        """Test unregistering a tool."""
        tool_registry.register(sample_function_tool, aliases=["tt"])

        result = tool_registry.unregister("test_tool")

        assert result is True
        assert "test_tool" not in tool_registry.tools
        assert "tt" not in tool_registry.tool_aliases

    def test_unregister_nonexistent(self, tool_registry):
        """Test unregistering non-existent tool."""
        result = tool_registry.unregister("nonexistent")

        assert result is False

    def test_get_tool_not_found(self, tool_registry):
        """Test getting non-existent tool."""
        result = tool_registry.get_tool("nonexistent")

        assert result is None

    def test_list_tools(self, tool_registry, sample_function_tool):
        """Test listing tools."""
        tool_registry.register(sample_function_tool)

        tools = tool_registry.list_tools()

        assert len(tools) == 1
        assert tools[0].name == "test_tool"

    def test_list_tools_by_category(self, tool_registry, sample_tool_definition):
        """Test listing tools by category."""
        tool1 = FunctionTool(sample_tool_definition, lambda **k: k)

        other_def = ToolDefinition(
            name="analysis_tool",
            description="Analysis",
            category=ToolCategory.ANALYSIS
        )
        tool2 = FunctionTool(other_def, lambda **k: k)

        tool_registry.register(tool1)
        tool_registry.register(tool2)

        processing_tools = tool_registry.list_tools(category=ToolCategory.DATA_PROCESSING)

        assert len(processing_tools) == 1
        assert processing_tools[0].name == "test_tool"

    def test_search_tools(self, tool_registry, sample_function_tool):
        """Test searching tools."""
        tool_registry.register(sample_function_tool)

        results = tool_registry.search_tools("test")

        assert len(results) == 1
        assert results[0].name == "test_tool"

    def test_search_tools_by_tag(self, tool_registry, sample_function_tool):
        """Test searching tools by tag."""
        tool_registry.register(sample_function_tool)

        results = tool_registry.search_tools("processing")

        assert len(results) == 1


# =============================================================================
# ToolSelector Tests
# =============================================================================

class TestToolSelector:
    """Tests for ToolSelector class."""

    @pytest.fixture
    def selector_with_tools(self, tool_registry, sample_function_tool):
        """Create selector with registered tools."""
        tool_registry.register(sample_function_tool)
        return ToolSelector(tool_registry)

    def test_select_tool_by_name(self, selector_with_tools):
        """Test selecting tool by name match."""
        tool = selector_with_tools.select_tool("test_tool operation")

        assert tool is not None
        assert tool.definition.name == "test_tool"

    def test_select_tool_by_description(self, selector_with_tools):
        """Test selecting tool by description match."""
        tool = selector_with_tools.select_tool("unit testing task")

        assert tool is not None

    def test_select_tool_no_match(self, selector_with_tools):
        """Test selecting with no matching tool."""
        # Make tool unavailable
        selector_with_tools.registry.tools["test_tool"].status = ToolStatus.UNAVAILABLE

        tool = selector_with_tools.select_tool("some task")

        assert tool is None

    def test_select_tool_records_history(self, selector_with_tools):
        """Test that selection is recorded in history."""
        selector_with_tools.select_tool("test operation")

        assert len(selector_with_tools.selection_history) == 1
        assert selector_with_tools.selection_history[0]["selected"] == "test_tool"

    def test_select_tool_chain(self, selector_with_tools):
        """Test selecting a chain of tools."""
        # Add another tool
        other_def = ToolDefinition(
            name="analyze_tool",
            description="Analyze data",
            category=ToolCategory.ANALYSIS,
            tags=["analyze"]
        )
        other_tool = FunctionTool(other_def, lambda **k: k)
        selector_with_tools.registry.register(other_tool)

        tools = selector_with_tools.select_tool_chain("test and analyze data")

        assert len(tools) >= 1

    def test_select_tool_preferred_category(self, selector_with_tools):
        """Test selecting with preferred category."""
        tool = selector_with_tools.select_tool(
            "process data",
            preferred_categories=[ToolCategory.DATA_PROCESSING]
        )

        assert tool is not None
        assert tool.definition.category == ToolCategory.DATA_PROCESSING


# =============================================================================
# ToolExecutor Tests
# =============================================================================

class TestToolExecutor:
    """Tests for ToolExecutor class."""

    @pytest.fixture
    def executor_with_tools(self, tool_registry, sample_function_tool):
        """Create executor with registered tools."""
        tool_registry.register(sample_function_tool)
        return ToolExecutor(tool_registry)

    @pytest.mark.asyncio
    async def test_execute_success(self, executor_with_tools):
        """Test successful tool execution."""
        request = ToolExecutionRequest(
            tool_name="test_tool",
            parameters={"input_data": {"key": "value"}}
        )

        result = await executor_with_tools.execute(request)

        assert result.status == ExecutionStatus.COMPLETED
        assert result.is_success()
        assert result.result["processed"] is True

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, executor_with_tools):
        """Test execution with non-existent tool."""
        request = ToolExecutionRequest(
            tool_name="nonexistent",
            parameters={}
        )

        result = await executor_with_tools.execute(request)

        assert result.status == ExecutionStatus.FAILED
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_validation_error(self, executor_with_tools):
        """Test execution with validation error."""
        request = ToolExecutionRequest(
            tool_name="test_tool",
            parameters={}  # Missing required input_data
        )

        result = await executor_with_tools.execute(request)

        assert result.status == ExecutionStatus.FAILED
        assert "Validation errors" in result.error

    @pytest.mark.asyncio
    async def test_execute_records_history(self, executor_with_tools):
        """Test that execution is recorded in history."""
        request = ToolExecutionRequest(
            tool_name="test_tool",
            parameters={"input_data": {"key": "value"}}
        )

        await executor_with_tools.execute(request)

        assert len(executor_with_tools.execution_history) == 1

    @pytest.mark.asyncio
    async def test_execute_chain_success(self, executor_with_tools):
        """Test successful chain execution."""
        chain = ToolChain(
            name="Test Chain",
            steps=[
                ToolChainStep(
                    tool_name="test_tool",
                    parameters={"input_data": {"step": 1}},
                    output_key="step1_result"
                )
            ]
        )

        result = await executor_with_tools.execute_chain(chain)

        assert result.status == ExecutionStatus.COMPLETED
        assert "step1_result" in result.context

    @pytest.mark.asyncio
    async def test_execute_chain_with_failure_abort(self, executor_with_tools):
        """Test chain execution with failure and abort."""
        chain = ToolChain(
            name="Test Chain",
            steps=[
                ToolChainStep(
                    tool_name="nonexistent",
                    parameters={},
                    on_failure="abort"
                )
            ]
        )

        result = await executor_with_tools.execute_chain(chain)

        assert result.status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_chain_with_failure_skip(self, executor_with_tools):
        """Test chain execution with failure and skip."""
        chain = ToolChain(
            name="Test Chain",
            steps=[
                ToolChainStep(
                    tool_name="nonexistent",
                    parameters={},
                    on_failure="skip"
                ),
                ToolChainStep(
                    tool_name="test_tool",
                    parameters={"input_data": {"step": 2}}
                )
            ]
        )

        result = await executor_with_tools.execute_chain(chain)

        assert result.status == ExecutionStatus.COMPLETED

    def test_get_execution_stats(self, executor_with_tools):
        """Test getting execution statistics."""
        stats = executor_with_tools.get_execution_stats()

        assert stats["total_executions"] == 0

    @pytest.mark.asyncio
    async def test_get_execution_stats_after_executions(self, executor_with_tools):
        """Test execution stats after some executions."""
        # Execute successfully
        request = ToolExecutionRequest(
            tool_name="test_tool",
            parameters={"input_data": {"key": "value"}}
        )
        await executor_with_tools.execute(request)

        # Execute with failure
        request2 = ToolExecutionRequest(
            tool_name="nonexistent",
            parameters={}
        )
        await executor_with_tools.execute(request2)

        stats = executor_with_tools.get_execution_stats()

        assert stats["total_executions"] == 2
        assert stats["successful"] == 1
        assert stats["failed"] == 1


# =============================================================================
# ResultValidator Tests
# =============================================================================

class TestResultValidator:
    """Tests for ResultValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a result validator."""
        return ResultValidator()

    def test_validate_success(self, validator):
        """Test validating successful result."""
        result = ToolExecutionResult(
            request_id="req_001",
            tool_name="test_tool",
            status=ExecutionStatus.COMPLETED,
            result={"output": "data"}
        )

        is_valid, errors = validator.validate(result)

        assert is_valid is True
        assert errors == []

    def test_validate_failed_status(self, validator):
        """Test validating failed status."""
        result = ToolExecutionResult(
            request_id="req_001",
            tool_name="test_tool",
            status=ExecutionStatus.FAILED
        )

        is_valid, errors = validator.validate(result)

        assert is_valid is False
        assert "not completed" in errors[0]

    def test_validate_null_result(self, validator):
        """Test validating null result."""
        result = ToolExecutionResult(
            request_id="req_001",
            tool_name="test_tool",
            status=ExecutionStatus.COMPLETED,
            result=None
        )

        is_valid, errors = validator.validate(result)

        assert is_valid is False
        assert "None" in errors[0]

    def test_validate_with_custom_validator(self, validator):
        """Test validating with custom validator."""
        def check_has_output(result):
            return "output" in result

        validator.register_validator("test_tool", check_has_output)

        result = ToolExecutionResult(
            request_id="req_001",
            tool_name="test_tool",
            status=ExecutionStatus.COMPLETED,
            result={"output": "data"}
        )

        is_valid, errors = validator.validate(result)

        assert is_valid is True

    def test_validate_custom_validator_failure(self, validator):
        """Test custom validator failure."""
        def check_has_output(result):
            return "output" in result

        validator.register_validator("test_tool", check_has_output)

        result = ToolExecutionResult(
            request_id="req_001",
            tool_name="test_tool",
            status=ExecutionStatus.COMPLETED,
            result={"data": "no output key"}
        )

        is_valid, errors = validator.validate(result)

        assert is_valid is False

    def test_validation_history(self, validator):
        """Test that validation is recorded in history."""
        result = ToolExecutionResult(
            request_id="req_001",
            tool_name="test_tool",
            status=ExecutionStatus.COMPLETED,
            result={"output": "data"}
        )

        validator.validate(result)

        assert len(validator.validation_history) == 1
        assert validator.validation_history[0]["request_id"] == "req_001"


# =============================================================================
# ToolFramework Tests
# =============================================================================

class TestToolFramework:
    """Tests for ToolFramework class."""

    def test_framework_initialization(self, tool_framework):
        """Test framework initialization."""
        assert tool_framework.registry is not None
        assert tool_framework.selector is not None
        assert tool_framework.executor is not None
        assert tool_framework.validator is not None

    def test_framework_has_default_tools(self, tool_framework):
        """Test framework has default tools registered."""
        tools = tool_framework.registry.list_tools()

        tool_names = [t.name for t in tools]
        assert "data_transform" in tool_names
        assert "calculate" in tool_names
        assert "text_analyze" in tool_names

    def test_register_tool(self, tool_framework, sample_function_tool):
        """Test registering a tool with framework."""
        tool_framework.register_tool(sample_function_tool, aliases=["test"])

        assert tool_framework.registry.get_tool("test_tool") is not None
        assert tool_framework.registry.get_tool("test") is not None

    @pytest.mark.asyncio
    async def test_execute_tool(self, tool_framework):
        """Test executing a tool by name."""
        result = await tool_framework.execute_tool(
            "data_transform",
            {"data": {"key": "value"}, "operation": "keys"}
        )

        assert result.is_success()
        assert "transformed" in result.result

    @pytest.mark.asyncio
    async def test_execute_for_task(self, tool_framework):
        """Test executing tool for a task description."""
        result = await tool_framework.execute_for_task(
            "transform and process data",
            {"data": {"key": "value"}, "operation": "flatten"}
        )

        assert result.is_success()

    @pytest.mark.asyncio
    async def test_execute_calculate_tool(self, tool_framework):
        """Test executing calculate tool."""
        result = await tool_framework.execute_tool(
            "calculate",
            {"expression": "1 + 2 + 3", "variables": {}}
        )

        assert result.is_success()
        assert result.result["result"] == 6

    @pytest.mark.asyncio
    async def test_execute_text_analyze_tool(self, tool_framework):
        """Test executing text analyze tool."""
        result = await tool_framework.execute_tool(
            "text_analyze",
            {
                "text": "Hello world. This is a test.",
                "analysis_type": "basic"
            }
        )

        assert result.is_success()
        assert result.result["word_count"] > 0
        assert result.result["sentences"] == 2

    @pytest.mark.asyncio
    async def test_execute_chain(self, tool_framework):
        """Test executing a tool chain."""
        chain = ToolChain(
            name="Transform Chain",
            steps=[
                ToolChainStep(
                    tool_name="data_transform",
                    parameters={"data": {"a": 1, "b": 2}, "operation": "keys"},
                    output_key="keys_result"
                )
            ]
        )

        result = await tool_framework.execute_chain(chain)

        assert result.status == ExecutionStatus.COMPLETED
        assert "keys_result" in result.context

    def test_get_framework_stats(self, tool_framework):
        """Test getting framework statistics."""
        stats = tool_framework.get_framework_stats()

        assert stats["registered_tools"] >= 3
        assert "execution_stats" in stats
        assert "selection_history_count" in stats


# =============================================================================
# Global Function Tests
# =============================================================================

class TestGlobalFunctions:
    """Tests for global helper functions."""

    def test_get_tool_framework(self):
        """Test getting global tool framework."""
        framework1 = get_tool_framework()
        framework2 = get_tool_framework()

        assert framework1 is framework2
        assert isinstance(framework1, ToolFramework)

    def test_create_function_tool(self):
        """Test creating a function tool with helper."""
        async def my_func(data: dict):
            return {"result": data}

        tool = create_function_tool(
            name="my_tool",
            description="My custom tool",
            category=ToolCategory.DATA_PROCESSING,
            func=my_func,
            parameters=[
                ToolParameter(name="data", param_type="dict")
            ],
            tags=["custom"]
        )

        assert tool.definition.name == "my_tool"
        assert tool.definition.category == ToolCategory.DATA_PROCESSING
        assert "custom" in tool.definition.tags


# =============================================================================
# Property-Based Tests (Conceptual)
# =============================================================================

class TestToolFrameworkProperties:
    """Property-based tests for tool framework behavior."""

    @pytest.mark.asyncio
    async def test_tool_execution_atomicity(self, tool_framework):
        """Property: Tool execution should complete or fail atomically."""
        result = await tool_framework.execute_tool(
            "calculate",
            {"expression": "1 + 1"}
        )

        # Status should be terminal (not pending or running)
        assert result.status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT
        ]

    def test_tool_registration_consistency(self, tool_framework, sample_function_tool):
        """Property: Registered tools should be retrievable."""
        tool_framework.register_tool(sample_function_tool)

        retrieved = tool_framework.registry.get_tool("test_tool")

        assert retrieved is not None
        assert retrieved.definition.name == sample_function_tool.definition.name

    @pytest.mark.asyncio
    async def test_chain_dependency_handling(self, tool_framework):
        """Property: Chain should correctly handle step dependencies."""
        chain = ToolChain(
            name="Dependency Chain",
            steps=[
                ToolChainStep(
                    tool_name="calculate",
                    parameters={"expression": "5 + 5"},
                    output_key="first_result"
                ),
                ToolChainStep(
                    tool_name="data_transform",
                    parameters={"data": {}, "operation": "keys"},
                    input_mappings={"data": "first_result"},
                    output_key="second_result"
                )
            ]
        )

        result = await tool_framework.execute_chain(chain)

        # Chain should complete
        assert result.status == ExecutionStatus.COMPLETED

        # Both results should be in context
        assert "first_result" in result.context
        assert "second_result" in result.context


# =============================================================================
# Integration Tests
# =============================================================================

class TestToolFrameworkIntegration:
    """Integration tests for tool framework."""

    @pytest.mark.asyncio
    async def test_full_tool_workflow(self, tool_framework):
        """Test complete tool workflow from registration to execution."""
        # Register custom tool
        async def custom_processor(data: dict, multiplier: int = 1):
            return {"processed": data, "multiplied": multiplier * 2}

        custom_tool = create_function_tool(
            name="custom_processor",
            description="Custom data processor",
            category=ToolCategory.DATA_PROCESSING,
            func=custom_processor,
            parameters=[
                ToolParameter(name="data", param_type="dict"),
                ToolParameter(name="multiplier", param_type="int", required=False, default=1)
            ],
            tags=["custom", "processor"]
        )

        tool_framework.register_tool(custom_tool)

        # Search for it
        search_results = tool_framework.registry.search_tools("custom")
        assert len(search_results) == 1

        # Select it for a task
        selected = tool_framework.selector.select_tool("custom processor operation")
        assert selected is not None
        assert selected.definition.name == "custom_processor"

        # Execute it
        result = await tool_framework.execute_tool(
            "custom_processor",
            {"data": {"key": "value"}, "multiplier": 5}
        )

        assert result.is_success()
        assert result.result["multiplied"] == 10

        # Validate result
        is_valid, errors = tool_framework.validator.validate(result)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_multi_step_chain_execution(self, tool_framework):
        """Test executing multi-step chain with data flow."""
        chain = ToolChain(
            name="Analysis Pipeline",
            steps=[
                ToolChainStep(
                    tool_name="text_analyze",
                    parameters={
                        "text": "Hello world! This is a test sentence.",
                        "analysis_type": "basic"
                    },
                    output_key="text_analysis"
                ),
                ToolChainStep(
                    tool_name="calculate",
                    parameters={
                        "expression": "word_count * 2",
                        "variables": {}
                    },
                    input_mappings={"variables": "text_analysis"},
                    output_key="calculation"
                )
            ]
        )

        result = await tool_framework.execute_chain(chain)

        assert result.status == ExecutionStatus.COMPLETED
        assert "text_analysis" in result.context
        assert result.context["text_analysis"]["word_count"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
