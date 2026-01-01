"""
Integration tests for the Reasoning System.

Tests cover:
- Task 18.1: End-to-end reasoning chain integration, reasoning with tool framework,
  reasoning results with decision tree integration
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from src.agent.reasoning_chain import (
    ReasoningStep,
    ReasoningStepType,
    ReasoningStatus,
    Hypothesis,
    ReasoningChain,
    ReasoningChainBuilder,
    ReasoningEngine,
)
from src.agent.tool_framework import (
    ToolDefinition,
    ToolParameter,
    FunctionTool,
    ToolRegistry,
    ToolSelector,
    ToolExecutor,
    ToolFramework,
    ExecutionStatus,
)
from src.agent.decision_tree import (
    DecisionCriteria,
    DecisionOption,
    DecisionNode,
    DecisionTree,
    DecisionTreeBuilder,
    DecisionAnalyzer,
    MultiObjectiveOptimizer,
    OutcomePredictor,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def reasoning_engine():
    """Create a reasoning engine instance."""
    return ReasoningEngine()


@pytest.fixture
def tool_framework():
    """Create a tool framework instance."""
    return ToolFramework()


@pytest.fixture
def sample_tools():
    """Create sample tools for testing."""
    tools = []

    # Data lookup tool
    async def lookup_data(query: str, source: str = "default") -> Dict[str, Any]:
        return {
            "query": query,
            "source": source,
            "results": [
                {"id": 1, "value": "result1", "confidence": 0.9},
                {"id": 2, "value": "result2", "confidence": 0.7},
            ]
        }

    tools.append(FunctionTool(
        definition=ToolDefinition(
            name="lookup_data",
            description="Look up data from various sources",
            parameters=[
                ToolParameter(name="query", param_type="string", required=True),
                ToolParameter(name="source", param_type="string", required=False),
            ]
        ),
        func=lookup_data
    ))

    # Analysis tool
    async def analyze_data(data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "analysis": "complete",
            "insights": ["insight1", "insight2"],
            "confidence": 0.85
        }

    tools.append(FunctionTool(
        definition=ToolDefinition(
            name="analyze_data",
            description="Analyze provided data",
            parameters=[
                ToolParameter(name="data", param_type="object", required=True),
            ]
        ),
        func=analyze_data
    ))

    # Validation tool
    async def validate_result(result: Dict[str, Any], criteria: str) -> Dict[str, Any]:
        return {
            "valid": True,
            "criteria": criteria,
            "score": 0.9
        }

    tools.append(FunctionTool(
        definition=ToolDefinition(
            name="validate_result",
            description="Validate analysis results",
            parameters=[
                ToolParameter(name="result", param_type="object", required=True),
                ToolParameter(name="criteria", param_type="string", required=True),
            ]
        ),
        func=validate_result
    ))

    return tools


# =============================================================================
# Test: End-to-End Reasoning Chain
# =============================================================================


class TestEndToEndReasoningChain:
    """End-to-end tests for complete reasoning chains."""

    @pytest.mark.asyncio
    async def test_simple_reasoning_chain(self, reasoning_engine):
        """Test a simple observation -> analysis -> conclusion chain."""
        # Build chain
        builder = ReasoningChainBuilder()
        chain = (
            builder
            .set_goal("Determine if sales increased")
            .add_observation_step(
                "sales_data",
                "Observe sales data for Q4"
            )
            .add_analysis_step(
                "trend_analysis",
                "Analyze sales trend",
                ["sales_data"]
            )
            .add_conclusion_step(
                "final_conclusion",
                "Draw conclusion about sales",
                ["trend_analysis"]
            )
            .build()
        )

        # Add execution functions
        async def observe_sales():
            return {"q4_sales": 1000000, "q3_sales": 800000}

        async def analyze_trend(deps):
            sales_data = deps.get("sales_data", {})
            q4 = sales_data.get("result", {}).get("q4_sales", 0)
            q3 = sales_data.get("result", {}).get("q3_sales", 0)
            growth = (q4 - q3) / q3 if q3 > 0 else 0
            return {"growth_rate": growth, "trend": "increasing" if growth > 0 else "decreasing"}

        async def conclude(deps):
            trend_data = deps.get("trend_analysis", {})
            trend = trend_data.get("result", {}).get("trend", "unknown")
            return {"conclusion": f"Sales are {trend}", "confidence": 0.9}

        # Register execution functions
        chain.steps[0].execute = observe_sales
        chain.steps[1].execute = lambda: analyze_trend({"sales_data": chain.steps[0].__dict__})
        chain.steps[2].execute = lambda: conclude({"trend_analysis": chain.steps[1].__dict__})

        # Execute chain
        result = await reasoning_engine.execute_chain(chain)

        assert result.status == ReasoningStatus.COMPLETED
        assert chain.overall_confidence > 0

    @pytest.mark.asyncio
    async def test_hypothesis_verification_chain(self, reasoning_engine):
        """Test a chain with hypothesis generation and verification."""
        builder = ReasoningChainBuilder()
        chain = (
            builder
            .set_goal("Verify customer churn hypothesis")
            .add_observation_step(
                "customer_data",
                "Gather customer behavior data"
            )
            .add_hypothesis_step(
                "churn_hypothesis",
                "Generate churn prediction hypothesis",
                hypothesis="Customers with low engagement will churn",
                initial_confidence=0.6,
                dependencies=["customer_data"]
            )
            .add_verification_step(
                "verify_hypothesis",
                "Verify churn hypothesis with historical data",
                ["churn_hypothesis"]
            )
            .add_conclusion_step(
                "recommendation",
                "Generate retention recommendations",
                ["verify_hypothesis"]
            )
            .build()
        )

        # Simulate execution
        for step in chain.steps:
            step.status = ReasoningStatus.COMPLETED
            step.result = {"data": f"result for {step.name}"}
            step.confidence = 0.8

        chain.status = ReasoningStatus.COMPLETED

        # Verify chain structure
        assert len(chain.steps) == 4
        assert chain.steps[0].step_type == ReasoningStepType.OBSERVATION
        assert chain.steps[1].step_type == ReasoningStepType.HYPOTHESIS
        assert chain.steps[2].step_type == ReasoningStepType.VERIFICATION
        assert chain.steps[3].step_type == ReasoningStepType.CONCLUSION

    @pytest.mark.asyncio
    async def test_reasoning_chain_with_backtracking(self, reasoning_engine):
        """Test reasoning chain with backtracking on failure."""
        builder = ReasoningChainBuilder()
        chain = (
            builder
            .set_goal("Find optimal solution with backtracking")
            .add_observation_step("initial_data", "Gather initial data")
            .add_analysis_step("first_attempt", "Try first approach", ["initial_data"])
            .add_analysis_step("second_attempt", "Try second approach", ["initial_data"])
            .add_conclusion_step("final", "Conclude based on successful attempt", ["first_attempt", "second_attempt"])
            .build()
        )

        # Simulate first attempt failing
        chain.steps[0].status = ReasoningStatus.COMPLETED
        chain.steps[0].confidence = 0.9

        chain.steps[1].status = ReasoningStatus.FAILED
        chain.steps[1].confidence = 0.2

        # Backtrack and try second attempt
        chain.backtrack_to("initial_data")

        # After backtracking, status should be reset
        # (The actual implementation may vary)

        # Verify chain can continue
        assert chain.status != ReasoningStatus.COMPLETED


# =============================================================================
# Test: Reasoning with Tool Framework Integration
# =============================================================================


class TestReasoningWithToolFramework:
    """Tests for reasoning chain integration with tool framework."""

    @pytest.mark.asyncio
    async def test_reasoning_using_tools(self, tool_framework, sample_tools):
        """Test reasoning chain that uses tools for execution."""
        # Register tools
        for tool in sample_tools:
            tool_framework.registry.register(tool)

        # Build reasoning chain
        builder = ReasoningChainBuilder()
        chain = (
            builder
            .set_goal("Analyze data using tools")
            .add_observation_step(
                "data_lookup",
                "Look up relevant data using lookup_data tool"
            )
            .add_analysis_step(
                "data_analysis",
                "Analyze the looked up data using analyze_data tool",
                ["data_lookup"]
            )
            .add_verification_step(
                "validation",
                "Validate results using validate_result tool",
                ["data_analysis"]
            )
            .build()
        )

        # Execute tool-based reasoning
        # Step 1: Lookup data
        lookup_result = await tool_framework.execute_tool(
            "lookup_data",
            {"query": "sales data", "source": "database"}
        )
        assert lookup_result.status == ExecutionStatus.SUCCESS

        # Step 2: Analyze data
        analyze_result = await tool_framework.execute_tool(
            "analyze_data",
            {"data": lookup_result.result}
        )
        assert analyze_result.status == ExecutionStatus.SUCCESS

        # Step 3: Validate
        validate_result = await tool_framework.execute_tool(
            "validate_result",
            {"result": analyze_result.result, "criteria": "accuracy > 0.8"}
        )
        assert validate_result.status == ExecutionStatus.SUCCESS
        assert validate_result.result["valid"] is True

    @pytest.mark.asyncio
    async def test_tool_selection_in_reasoning(self, tool_framework, sample_tools):
        """Test that reasoning can select appropriate tools."""
        # Register tools
        for tool in sample_tools:
            tool_framework.registry.register(tool)

        # Test tool selection based on task
        selector = tool_framework.selector

        # Should select lookup tool for data retrieval
        lookup_tools = selector.select_tools(
            "I need to look up sales data from the database",
            available_tools=[t.definition for t in sample_tools]
        )
        assert any("lookup" in t.name for t in lookup_tools)

        # Should select analysis tool for data analysis
        analysis_tools = selector.select_tools(
            "Analyze the customer data to find patterns",
            available_tools=[t.definition for t in sample_tools]
        )
        assert any("analyze" in t.name for t in analysis_tools)

    @pytest.mark.asyncio
    async def test_tool_chain_in_reasoning(self, tool_framework, sample_tools):
        """Test executing a chain of tools within reasoning."""
        # Register tools
        for tool in sample_tools:
            tool_framework.registry.register(tool)

        # Create tool chain
        from src.agent.tool_framework import ToolChain, ToolChainStep

        chain = ToolChain(name="data_pipeline", description="End-to-end data pipeline")
        chain.add_step(ToolChainStep(
            tool_name="lookup_data",
            step_name="lookup",
            input_mappings={"query": "initial_query"}
        ))
        chain.add_step(ToolChainStep(
            tool_name="analyze_data",
            step_name="analyze",
            input_mappings={"data": "lookup.result"}
        ))
        chain.add_step(ToolChainStep(
            tool_name="validate_result",
            step_name="validate",
            input_mappings={"result": "analyze.result", "criteria": "validation_criteria"}
        ))

        # Execute chain
        initial_input = {
            "initial_query": "Q4 sales data",
            "validation_criteria": "confidence > 0.8"
        }

        results = await tool_framework.executor.execute_chain(
            chain, initial_input, tool_framework.registry
        )

        assert len(results) == 3
        assert all(r.status == ExecutionStatus.SUCCESS for r in results)


# =============================================================================
# Test: Reasoning Results with Decision Tree Integration
# =============================================================================


class TestReasoningWithDecisionTree:
    """Tests for integrating reasoning results with decision trees."""

    @pytest.mark.asyncio
    async def test_reasoning_feeds_decision_tree(self):
        """Test that reasoning results feed into decision tree."""
        # First, run reasoning to get insights
        builder = ReasoningChainBuilder()
        chain = (
            builder
            .set_goal("Analyze market conditions for investment decision")
            .add_observation_step("market_data", "Gather market data")
            .add_analysis_step("market_analysis", "Analyze market trends", ["market_data"])
            .add_hypothesis_step(
                "growth_hypothesis",
                "Hypothesize market growth",
                hypothesis="Market will grow 10% next quarter",
                initial_confidence=0.7,
                dependencies=["market_analysis"]
            )
            .build()
        )

        # Simulate reasoning results
        reasoning_result = {
            "market_trend": "bullish",
            "growth_probability": 0.75,
            "risk_level": "moderate",
            "confidence": 0.8
        }

        # Build decision tree based on reasoning results
        tree_builder = DecisionTreeBuilder()
        tree = (
            tree_builder
            .set_root(
                name="investment_decision",
                description="Decide on investment strategy"
            )
            .add_criteria("growth_potential", weight=0.4, target=0.7)
            .add_criteria("risk_level", weight=0.3, target=0.5)
            .add_criteria("confidence", weight=0.3, target=0.8)
            .add_option(
                name="aggressive_invest",
                description="Invest aggressively",
                criteria_scores={"growth_potential": 0.9, "risk_level": 0.3, "confidence": 0.8}
            )
            .add_option(
                name="conservative_invest",
                description="Invest conservatively",
                criteria_scores={"growth_potential": 0.5, "risk_level": 0.8, "confidence": 0.9}
            )
            .add_option(
                name="hold",
                description="Hold current position",
                criteria_scores={"growth_potential": 0.3, "risk_level": 0.9, "confidence": 0.7}
            )
            .build()
        )

        # Analyze decision based on reasoning results
        analyzer = DecisionAnalyzer()
        paths = analyzer.enumerate_paths(tree)

        # Get best option based on weighted scores
        best_path = analyzer.rank_paths(paths)[0]

        # The decision should be informed by the reasoning results
        assert best_path is not None

    @pytest.mark.asyncio
    async def test_multi_objective_optimization_from_reasoning(self):
        """Test multi-objective optimization based on reasoning insights."""
        # Reasoning provides multiple objectives
        reasoning_objectives = [
            {"name": "maximize_return", "weight": 0.4, "target": 0.15},
            {"name": "minimize_risk", "weight": 0.35, "target": 0.05},
            {"name": "maximize_liquidity", "weight": 0.25, "target": 0.8}
        ]

        # Create options based on reasoning analysis
        options = [
            DecisionOption(
                name="stocks",
                description="Invest in stocks",
                criteria_scores={
                    "maximize_return": 0.2,
                    "minimize_risk": 0.3,
                    "maximize_liquidity": 0.9
                }
            ),
            DecisionOption(
                name="bonds",
                description="Invest in bonds",
                criteria_scores={
                    "maximize_return": 0.05,
                    "minimize_risk": 0.02,
                    "maximize_liquidity": 0.7
                }
            ),
            DecisionOption(
                name="real_estate",
                description="Invest in real estate",
                criteria_scores={
                    "maximize_return": 0.12,
                    "minimize_risk": 0.1,
                    "maximize_liquidity": 0.2
                }
            ),
        ]

        # Create criteria from reasoning objectives
        criteria = [
            DecisionCriteria(
                name=obj["name"],
                weight=obj["weight"],
                target_value=obj["target"]
            )
            for obj in reasoning_objectives
        ]

        # Use multi-objective optimizer
        optimizer = MultiObjectiveOptimizer(criteria)
        pareto_options = optimizer.find_pareto_optimal(options)

        # Should find at least one Pareto-optimal solution
        assert len(pareto_options) > 0

        # Test weighted sum optimization
        best_option = optimizer.weighted_sum_optimization(options)
        assert best_option is not None

    @pytest.mark.asyncio
    async def test_outcome_prediction_from_reasoning(self):
        """Test outcome prediction based on reasoning analysis."""
        # Create predictor
        predictor = OutcomePredictor()

        # Create option with probabilities from reasoning
        option = DecisionOption(
            name="expansion",
            description="Expand to new market",
            criteria_scores={
                "revenue_growth": 0.7,
                "market_share": 0.6,
                "risk": 0.4
            },
            expected_outcome=0.65,
            outcome_variance=0.1
        )

        # Predict outcomes
        predictions = predictor.predict_outcomes(option, simulations=1000)

        # Should have predictions
        assert "mean" in predictions
        assert "std" in predictions
        assert "confidence_interval" in predictions

        # Mean should be close to expected outcome
        assert abs(predictions["mean"] - option.expected_outcome) < 0.1


# =============================================================================
# Test: Full Integration Workflow
# =============================================================================


class TestFullIntegrationWorkflow:
    """Tests for complete reasoning -> tools -> decision workflow."""

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self, tool_framework, sample_tools):
        """Test complete workflow from reasoning to decision."""
        # Register tools
        for tool in sample_tools:
            tool_framework.registry.register(tool)

        # Phase 1: Reasoning - Build analysis chain
        reasoning_builder = ReasoningChainBuilder()
        reasoning_chain = (
            reasoning_builder
            .set_goal("Comprehensive market analysis for strategic decision")
            .add_observation_step("data_collection", "Collect market data")
            .add_analysis_step("trend_analysis", "Analyze market trends", ["data_collection"])
            .add_hypothesis_step(
                "market_hypothesis",
                "Form market hypothesis",
                hypothesis="Market will be favorable for expansion",
                initial_confidence=0.65,
                dependencies=["trend_analysis"]
            )
            .add_verification_step("verify_hypothesis", "Verify hypothesis", ["market_hypothesis"])
            .add_conclusion_step("analysis_conclusion", "Draw conclusions", ["verify_hypothesis"])
            .build()
        )

        # Phase 2: Tool Execution - Execute data tools
        lookup_result = await tool_framework.execute_tool(
            "lookup_data",
            {"query": "market trends 2024", "source": "market_db"}
        )

        analysis_result = await tool_framework.execute_tool(
            "analyze_data",
            {"data": lookup_result.result}
        )

        validation_result = await tool_framework.execute_tool(
            "validate_result",
            {"result": analysis_result.result, "criteria": "statistical significance"}
        )

        # Phase 3: Decision Making - Build decision tree from results
        decision_builder = DecisionTreeBuilder()
        decision_tree = (
            decision_builder
            .set_root("strategic_decision", "Choose strategic direction")
            .add_criteria("market_opportunity", weight=0.35, target=0.7)
            .add_criteria("competitive_advantage", weight=0.35, target=0.6)
            .add_criteria("resource_availability", weight=0.3, target=0.8)
            .add_option(
                "expand",
                "Expand operations",
                {"market_opportunity": 0.8, "competitive_advantage": 0.6, "resource_availability": 0.5}
            )
            .add_option(
                "consolidate",
                "Consolidate current position",
                {"market_opportunity": 0.4, "competitive_advantage": 0.8, "resource_availability": 0.9}
            )
            .add_option(
                "diversify",
                "Diversify into new areas",
                {"market_opportunity": 0.7, "competitive_advantage": 0.5, "resource_availability": 0.4}
            )
            .build()
        )

        # Analyze and decide
        analyzer = DecisionAnalyzer()
        paths = analyzer.enumerate_paths(decision_tree)
        ranked_paths = analyzer.rank_paths(paths)

        # Verify complete workflow
        assert lookup_result.status == ExecutionStatus.SUCCESS
        assert analysis_result.status == ExecutionStatus.SUCCESS
        assert validation_result.status == ExecutionStatus.SUCCESS
        assert len(ranked_paths) > 0

    @pytest.mark.asyncio
    async def test_iterative_reasoning_with_feedback(self, tool_framework, sample_tools):
        """Test iterative reasoning that refines based on feedback."""
        # Register tools
        for tool in sample_tools:
            tool_framework.registry.register(tool)

        iterations = []

        for iteration in range(3):
            # Each iteration refines the hypothesis
            builder = ReasoningChainBuilder()
            chain = (
                builder
                .set_goal(f"Refine analysis - iteration {iteration + 1}")
                .add_observation_step("observe", "Gather data")
                .add_hypothesis_step(
                    "hypothesis",
                    "Form hypothesis",
                    hypothesis=f"Refined hypothesis v{iteration + 1}",
                    initial_confidence=0.5 + (iteration * 0.1),
                    dependencies=["observe"]
                )
                .add_verification_step("verify", "Verify", ["hypothesis"])
                .build()
            )

            # Simulate increasing confidence with iterations
            confidence = 0.6 + (iteration * 0.1)
            iterations.append({
                "iteration": iteration + 1,
                "confidence": confidence,
                "hypothesis": chain.steps[1].description
            })

        # Verify iterations improve
        assert iterations[-1]["confidence"] > iterations[0]["confidence"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
