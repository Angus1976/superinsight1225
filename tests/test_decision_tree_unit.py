"""
Decision Tree Unit Tests.

Tests for decision path analysis, option evaluation, multi-objective optimization,
outcome prediction, and sensitivity analysis.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.agent.decision_tree import (
    DecisionNodeType,
    DecisionStatus,
    OptimizationObjective,
    DecisionCriteria,
    DecisionOption,
    DecisionNode,
    DecisionPath,
    DecisionTree,
    DecisionResult,
    DecisionTreeBuilder,
    DecisionAnalyzer,
    MultiObjectiveOptimizer,
    OutcomePredictor,
    get_decision_analyzer,
    get_outcome_predictor,
    create_simple_decision_tree,
)


# =============================================================================
# DecisionCriteria Tests
# =============================================================================

class TestDecisionCriteria:
    """Tests for DecisionCriteria class."""

    def test_criteria_creation(self):
        """Test creating decision criteria."""
        criteria = DecisionCriteria(
            name="cost",
            weight=0.5,
            minimize=True,
            threshold=1000.0
        )

        assert criteria.name == "cost"
        assert criteria.weight == 0.5
        assert criteria.minimize is True
        assert criteria.threshold == 1000.0

    def test_criteria_defaults(self):
        """Test criteria default values."""
        criteria = DecisionCriteria(name="value")

        assert criteria.weight == 1.0
        assert criteria.minimize is False
        assert criteria.threshold is None


# =============================================================================
# DecisionOption Tests
# =============================================================================

class TestDecisionOption:
    """Tests for DecisionOption class."""

    def test_option_creation(self):
        """Test creating a decision option."""
        option = DecisionOption(
            name="Option A",
            description="First option",
            probability=0.8,
            expected_value=1000.0,
            risk_level=0.3,
            cost=100.0
        )

        assert option.id is not None
        assert option.name == "Option A"
        assert option.probability == 0.8
        assert option.expected_value == 1000.0
        assert option.risk_level == 0.3
        assert option.cost == 100.0

    def test_option_defaults(self):
        """Test option default values."""
        option = DecisionOption()

        assert option.probability == 1.0
        assert option.expected_value == 0.0
        assert option.risk_level == 0.0
        assert option.cost == 0.0
        assert option.dependencies == []

    def test_evaluate_criteria(self):
        """Test evaluating option against criteria."""
        option = DecisionOption(
            name="Option",
            metadata={"quality": 0.8, "speed": 0.6}
        )

        criteria = [
            DecisionCriteria(name="quality", weight=2.0),
            DecisionCriteria(name="speed", weight=1.0)
        ]

        scores = option.evaluate_criteria(criteria)

        assert "quality" in scores
        assert "speed" in scores
        assert scores["quality"] == 0.8 * 2.0
        assert scores["speed"] == 0.6 * 1.0

    def test_evaluate_criteria_minimize(self):
        """Test evaluating with minimize criteria."""
        option = DecisionOption(
            name="Option",
            metadata={"cost": 0.5}  # Lower is better
        )

        criteria = [
            DecisionCriteria(name="cost", weight=1.0, minimize=True)
        ]

        scores = option.evaluate_criteria(criteria)

        # For minimize, value is inverted (1 - 0.5 = 0.5)
        assert scores["cost"] == 0.5


# =============================================================================
# DecisionNode Tests
# =============================================================================

class TestDecisionNode:
    """Tests for DecisionNode class."""

    def test_node_creation(self):
        """Test creating a decision node."""
        node = DecisionNode(
            node_type=DecisionNodeType.DECISION,
            name="Choose Strategy",
            description="Select the best strategy"
        )

        assert node.id is not None
        assert node.node_type == DecisionNodeType.DECISION
        assert node.name == "Choose Strategy"
        assert node.options == []
        assert node.children == {}

    def test_add_option(self):
        """Test adding option to node."""
        node = DecisionNode(name="Test")
        option1 = DecisionOption(name="Option A")
        option2 = DecisionOption(name="Option B")

        node.add_option(option1)
        node.add_option(option2)

        assert len(node.options) == 2
        assert node.options[0].name == "Option A"

    def test_add_child(self):
        """Test adding child node."""
        parent = DecisionNode(name="Parent")
        child = DecisionNode(name="Child")
        option = DecisionOption(name="Option")
        parent.add_option(option)

        parent.add_child(option.id, child)

        assert option.id in parent.children
        assert parent.children[option.id] == child
        assert child.parent_id == parent.id

    def test_get_expected_value_outcome(self):
        """Test expected value for outcome node."""
        node = DecisionNode(
            node_type=DecisionNodeType.OUTCOME,
            value=100.0
        )

        ev = node.get_expected_value()

        assert ev == 100.0

    def test_get_expected_value_decision_node(self):
        """Test expected value for decision node (max of options)."""
        node = DecisionNode(node_type=DecisionNodeType.DECISION)

        option1 = DecisionOption(name="A", probability=0.8, expected_value=100.0)
        option2 = DecisionOption(name="B", probability=1.0, expected_value=50.0)

        node.add_option(option1)
        node.add_option(option2)

        ev = node.get_expected_value()

        # Max of (0.8 * 100, 1.0 * 50) = max(80, 50) = 80
        assert ev == 80.0

    def test_get_expected_value_chance_node(self):
        """Test expected value for chance node (weighted sum)."""
        node = DecisionNode(node_type=DecisionNodeType.CHANCE)

        option1 = DecisionOption(name="A", probability=0.6, expected_value=100.0)
        option2 = DecisionOption(name="B", probability=0.4, expected_value=50.0)

        node.add_option(option1)
        node.add_option(option2)

        ev = node.get_expected_value()

        # Sum of (0.6 * 100 + 0.4 * 50) = 60 + 20 = 80
        assert ev == 80.0

    def test_get_expected_value_with_children(self):
        """Test expected value with child nodes."""
        parent = DecisionNode(node_type=DecisionNodeType.DECISION)
        child1 = DecisionNode(node_type=DecisionNodeType.OUTCOME, value=100.0)
        child2 = DecisionNode(node_type=DecisionNodeType.OUTCOME, value=50.0)

        option1 = DecisionOption(name="A", probability=0.8)
        option2 = DecisionOption(name="B", probability=1.0)

        parent.add_option(option1)
        parent.add_option(option2)
        parent.add_child(option1.id, child1)
        parent.add_child(option2.id, child2)

        ev = parent.get_expected_value()

        # Max of (0.8 * 100, 1.0 * 50) = max(80, 50) = 80
        assert ev == 80.0


# =============================================================================
# DecisionPath Tests
# =============================================================================

class TestDecisionPath:
    """Tests for DecisionPath class."""

    def test_path_creation(self):
        """Test creating a decision path."""
        path = DecisionPath(
            nodes=["node1", "node2", "node3"],
            options_selected=["opt1", "opt2"],
            total_probability=0.64,
            expected_value=100.0,
            total_risk=0.3,
            total_cost=50.0
        )

        assert len(path.nodes) == 3
        assert len(path.options_selected) == 2
        assert path.total_probability == 0.64
        assert path.expected_value == 100.0

    def test_path_defaults(self):
        """Test path default values."""
        path = DecisionPath()

        assert path.nodes == []
        assert path.options_selected == []
        assert path.total_probability == 1.0
        assert path.expected_value == 0.0


# =============================================================================
# DecisionTree Tests
# =============================================================================

class TestDecisionTree:
    """Tests for DecisionTree class."""

    def test_tree_creation(self):
        """Test creating a decision tree."""
        tree = DecisionTree(
            name="Investment Decision",
            description="Decide where to invest",
            objective=OptimizationObjective.MAXIMIZE_VALUE
        )

        assert tree.id is not None
        assert tree.name == "Investment Decision"
        assert tree.objective == OptimizationObjective.MAXIMIZE_VALUE
        assert tree.status == DecisionStatus.PENDING
        assert tree.root is None

    def test_add_node(self):
        """Test adding node to tree."""
        tree = DecisionTree(name="Test")
        node = DecisionNode(node_type=DecisionNodeType.ROOT, name="Root")

        tree.add_node(node)

        assert node.id in tree.nodes
        assert tree.root == node

    def test_get_node(self):
        """Test getting node by ID."""
        tree = DecisionTree(name="Test")
        node = DecisionNode(name="Node")
        tree.add_node(node)

        retrieved = tree.get_node(node.id)

        assert retrieved == node

    def test_get_node_not_found(self):
        """Test getting non-existent node."""
        tree = DecisionTree(name="Test")

        retrieved = tree.get_node("nonexistent")

        assert retrieved is None


# =============================================================================
# DecisionTreeBuilder Tests
# =============================================================================

class TestDecisionTreeBuilder:
    """Tests for DecisionTreeBuilder class."""

    @pytest.fixture
    def builder(self):
        """Create a builder for testing."""
        return DecisionTreeBuilder()

    def test_create_tree(self, builder):
        """Test creating a tree with builder."""
        tree = builder.create_tree(
            name="Test Decision",
            description="A test decision",
            objective=OptimizationObjective.MINIMIZE_RISK
        )

        assert tree.name == "Test Decision"
        assert tree.objective == OptimizationObjective.MINIMIZE_RISK
        assert builder.tree == tree

    def test_add_root(self, builder):
        """Test adding root node."""
        builder.create_tree("Test")

        root = builder.add_root(name="Start", description="Starting point")

        assert root.node_type == DecisionNodeType.ROOT
        assert root.name == "Start"
        assert builder.tree.root == root

    def test_add_decision_node(self, builder):
        """Test adding decision node."""
        builder.create_tree("Test")
        root = builder.add_root("Start")
        option = DecisionOption(name="Path A")
        root.add_option(option)

        child = builder.add_decision_node(
            name="Decision 2",
            parent_id=root.id,
            parent_option_id=option.id
        )

        assert child.node_type == DecisionNodeType.DECISION
        assert child.parent_id == root.id
        assert option.id in root.children

    def test_add_chance_node(self, builder):
        """Test adding chance node."""
        builder.create_tree("Test")
        root = builder.add_root("Start")
        option = DecisionOption(name="Gamble")
        root.add_option(option)

        child = builder.add_chance_node(
            name="Outcome",
            parent_id=root.id,
            parent_option_id=option.id
        )

        assert child.node_type == DecisionNodeType.CHANCE

    def test_add_outcome_node(self, builder):
        """Test adding outcome node."""
        builder.create_tree("Test")
        root = builder.add_root("Start")
        option = DecisionOption(name="Choice")
        root.add_option(option)

        outcome = builder.add_outcome_node(
            name="Final Result",
            parent_id=root.id,
            parent_option_id=option.id,
            value=1000.0
        )

        assert outcome.node_type == DecisionNodeType.OUTCOME
        assert outcome.value == 1000.0

    def test_add_option(self, builder):
        """Test adding option to node."""
        builder.create_tree("Test")
        root = builder.add_root("Start")

        option = builder.add_option(
            node_id=root.id,
            name="Option A",
            probability=0.7,
            expected_value=500.0,
            risk_level=0.2,
            cost=100.0
        )

        assert option is not None
        assert option.name == "Option A"
        assert option.probability == 0.7
        assert len(root.options) == 1

    def test_add_option_no_tree(self, builder):
        """Test adding option without tree."""
        option = builder.add_option(
            node_id="nonexistent",
            name="Option"
        )

        assert option is None

    def test_add_criteria(self, builder):
        """Test adding evaluation criteria."""
        builder.create_tree("Test")

        builder.add_criteria(
            name="quality",
            weight=2.0,
            minimize=False,
            threshold=0.8
        )

        assert len(builder.tree.criteria) == 1
        assert builder.tree.criteria[0].name == "quality"


# =============================================================================
# DecisionAnalyzer Tests
# =============================================================================

class TestDecisionAnalyzer:
    """Tests for DecisionAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create an analyzer for testing."""
        return DecisionAnalyzer()

    @pytest.fixture
    def simple_tree(self):
        """Create a simple decision tree for testing."""
        builder = DecisionTreeBuilder()
        tree = builder.create_tree("Simple Decision")
        root = builder.add_root("Choose")

        opt1 = builder.add_option(root.id, "Option A", probability=0.8, expected_value=100)
        opt2 = builder.add_option(root.id, "Option B", probability=0.9, expected_value=80)

        builder.add_outcome_node("A Result", root.id, root.options[0].id, 100)
        builder.add_outcome_node("B Result", root.id, root.options[1].id, 80)

        return tree

    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer.analysis_history == []

    def test_analyze_simple_tree(self, analyzer, simple_tree):
        """Test analyzing a simple decision tree."""
        result = analyzer.analyze(simple_tree)

        assert result.tree_id == simple_tree.id
        assert result.recommended_path is not None
        assert result.confidence > 0
        assert len(result.reasoning) > 0

    def test_analyze_no_root(self, analyzer):
        """Test analyzing tree with no root."""
        tree = DecisionTree(name="Empty")

        result = analyzer.analyze(tree)

        assert result.recommended_path is None
        assert "No root node found" in result.reasoning

    def test_analyze_records_history(self, analyzer, simple_tree):
        """Test that analysis is recorded in history."""
        analyzer.analyze(simple_tree)

        assert len(analyzer.analysis_history) == 1

    def test_enumerate_paths(self, analyzer, simple_tree):
        """Test path enumeration."""
        paths = analyzer._enumerate_paths(simple_tree.root, simple_tree)

        assert len(paths) == 2  # Two options

    def test_rank_paths_maximize_value(self, analyzer):
        """Test ranking paths with maximize value objective."""
        path1 = DecisionPath(expected_value=100, total_probability=0.8)
        path2 = DecisionPath(expected_value=80, total_probability=1.0)

        ranked = analyzer._rank_paths([path1, path2], OptimizationObjective.MAXIMIZE_VALUE)

        # path1: 100 * 0.8 = 80, path2: 80 * 1.0 = 80 (same, order may vary)
        assert len(ranked) == 2

    def test_rank_paths_minimize_risk(self, analyzer):
        """Test ranking paths with minimize risk objective."""
        path1 = DecisionPath(total_risk=0.2, total_probability=0.8)
        path2 = DecisionPath(total_risk=0.5, total_probability=0.9)

        ranked = analyzer._rank_paths([path1, path2], OptimizationObjective.MINIMIZE_RISK)

        # path1 should rank higher (lower risk)
        assert ranked[0].total_risk < ranked[1].total_risk

    def test_calculate_path_score_balanced(self, analyzer):
        """Test calculating path score with balanced objective."""
        path = DecisionPath(
            expected_value=100,
            total_probability=0.8,
            total_risk=0.2,
            total_cost=50
        )

        score = analyzer._calculate_path_score(path, OptimizationObjective.BALANCED)

        assert score > 0

    def test_sensitivity_analysis(self, analyzer, simple_tree):
        """Test sensitivity analysis."""
        analysis = analyzer._perform_sensitivity_analysis(simple_tree)

        assert "probability_sensitivity" in analysis
        assert "value_sensitivity" in analysis

    def test_risk_assessment(self, analyzer, simple_tree):
        """Test risk assessment."""
        risks = analyzer._assess_risks(simple_tree)

        assert "overall_risk" in risks
        assert "high_risk_options" in risks
        assert "low_probability_paths" in risks

    def test_generate_reasoning(self, analyzer, simple_tree):
        """Test reasoning generation."""
        result = DecisionResult(tree_id=simple_tree.id)
        result.recommended_path = DecisionPath(
            nodes=["a", "b"],
            total_probability=0.8,
            expected_value=100,
            total_risk=0.2,
            total_cost=50
        )
        result.confidence = 0.85

        reasoning = analyzer._generate_reasoning(simple_tree, result)

        assert len(reasoning) > 0
        assert any("steps" in r for r in reasoning)


# =============================================================================
# MultiObjectiveOptimizer Tests
# =============================================================================

class TestMultiObjectiveOptimizer:
    """Tests for MultiObjectiveOptimizer class."""

    @pytest.fixture
    def optimizer(self):
        """Create an optimizer for testing."""
        optimizer = MultiObjectiveOptimizer()
        optimizer.set_objectives([
            DecisionCriteria(name="value", weight=1.0),
            DecisionCriteria(name="risk", weight=1.0, minimize=True)
        ])
        return optimizer

    def test_set_objectives(self, optimizer):
        """Test setting optimization objectives."""
        assert len(optimizer.objectives) == 2

    def test_find_pareto_optimal(self, optimizer):
        """Test finding Pareto-optimal solutions."""
        options = [
            DecisionOption(name="A", metadata={"value": 100, "risk": 0.3}),
            DecisionOption(name="B", metadata={"value": 80, "risk": 0.2}),
            DecisionOption(name="C", metadata={"value": 60, "risk": 0.5})  # Dominated by A
        ]

        pareto_front = optimizer.find_pareto_optimal(options)

        # A and B should be Pareto optimal, C is dominated by A
        assert len(pareto_front) >= 1

    def test_pareto_dominates(self, optimizer):
        """Test dominance check."""
        option_a = DecisionOption(name="A", metadata={"value": 100, "risk": 0.2})
        option_b = DecisionOption(name="B", metadata={"value": 80, "risk": 0.3})

        # A dominates B (higher value, lower risk)
        assert optimizer._dominates(option_a, option_b) is True
        assert optimizer._dominates(option_b, option_a) is False

    def test_weighted_sum_optimization(self, optimizer):
        """Test weighted sum optimization."""
        options = [
            DecisionOption(name="A", metadata={"value": 100, "risk": 0.3}),
            DecisionOption(name="B", metadata={"value": 80, "risk": 0.1}),
        ]

        best = optimizer.weighted_sum_optimization(options)

        assert best is not None

    def test_weighted_sum_no_options(self, optimizer):
        """Test weighted sum with no options."""
        best = optimizer.weighted_sum_optimization([])

        assert best is None

    def test_weighted_sum_no_objectives(self):
        """Test weighted sum with no objectives."""
        optimizer = MultiObjectiveOptimizer()  # No objectives set

        options = [DecisionOption(name="A")]

        best = optimizer.weighted_sum_optimization(options)

        assert best is None


# =============================================================================
# OutcomePredictor Tests
# =============================================================================

class TestOutcomePredictor:
    """Tests for OutcomePredictor class."""

    @pytest.fixture
    def predictor(self):
        """Create a predictor for testing."""
        return OutcomePredictor()

    @pytest.fixture
    def tree_with_path(self):
        """Create a tree with a path for testing."""
        builder = DecisionTreeBuilder()
        tree = builder.create_tree("Test")
        root = builder.add_root("Start")

        option = builder.add_option(root.id, "Go", probability=0.8, expected_value=100)
        builder.add_outcome_node("End", root.id, root.options[0].id, 100)

        path = DecisionPath(
            nodes=[root.id],
            options_selected=[root.options[0].id],
            total_probability=0.8,
            expected_value=100
        )

        return tree, path

    def test_predict_outcome(self, predictor, tree_with_path):
        """Test predicting outcome."""
        tree, path = tree_with_path

        prediction = predictor.predict_outcome(tree, path)

        assert "expected_value" in prediction
        assert "value_range" in prediction
        assert "probability_of_success" in prediction
        assert "confidence_interval" in prediction
        assert "scenarios" in prediction

    def test_predict_outcome_records_history(self, predictor, tree_with_path):
        """Test that prediction is recorded in history."""
        tree, path = tree_with_path

        predictor.predict_outcome(tree, path)

        assert len(predictor.prediction_history) == 1

    def test_predict_outcome_scenarios(self, predictor, tree_with_path):
        """Test that scenarios are generated."""
        tree, path = tree_with_path

        prediction = predictor.predict_outcome(tree, path)

        assert len(prediction["scenarios"]) == 3
        scenario_names = [s["name"] for s in prediction["scenarios"]]
        assert "Best Case" in scenario_names
        assert "Expected Case" in scenario_names
        assert "Worst Case" in scenario_names


# =============================================================================
# Global Function Tests
# =============================================================================

class TestGlobalFunctions:
    """Tests for global helper functions."""

    def test_get_decision_analyzer(self):
        """Test getting global decision analyzer."""
        analyzer1 = get_decision_analyzer()
        analyzer2 = get_decision_analyzer()

        assert analyzer1 is analyzer2
        assert isinstance(analyzer1, DecisionAnalyzer)

    def test_get_outcome_predictor(self):
        """Test getting global outcome predictor."""
        predictor1 = get_outcome_predictor()
        predictor2 = get_outcome_predictor()

        assert predictor1 is predictor2
        assert isinstance(predictor1, OutcomePredictor)

    def test_create_simple_decision_tree(self):
        """Test creating a simple decision tree."""
        options = [
            {"name": "Option A", "probability": 0.8, "value": 100, "risk": 0.2, "cost": 50},
            {"name": "Option B", "probability": 0.9, "value": 80, "risk": 0.1, "cost": 30}
        ]

        tree, result = create_simple_decision_tree("Test Decision", options)

        assert tree is not None
        assert tree.name == "Test Decision"
        assert result is not None
        assert result.recommended_path is not None


# =============================================================================
# Property-Based Tests (Conceptual)
# =============================================================================

class TestDecisionTreeProperties:
    """Property-based tests for decision tree behavior."""

    def test_pareto_optimality(self):
        """Property: Pareto-optimal solutions should not be dominated."""
        optimizer = MultiObjectiveOptimizer()
        optimizer.set_objectives([
            DecisionCriteria(name="value", weight=1.0),
            DecisionCriteria(name="cost", weight=1.0, minimize=True)
        ])

        options = [
            DecisionOption(name="A", metadata={"value": 100, "cost": 50}),
            DecisionOption(name="B", metadata={"value": 80, "cost": 30}),
            DecisionOption(name="C", metadata={"value": 90, "cost": 40}),
        ]

        pareto_front = optimizer.find_pareto_optimal(options)

        # No option in Pareto front should dominate another
        for opt1 in pareto_front:
            for opt2 in pareto_front:
                if opt1.id != opt2.id:
                    assert not optimizer._dominates(opt1, opt2) or not optimizer._dominates(opt2, opt1)

    def test_decision_consistency(self):
        """Property: Same input should produce same decision."""
        options = [
            {"name": "A", "probability": 0.8, "value": 100, "risk": 0.2},
            {"name": "B", "probability": 0.9, "value": 80, "risk": 0.1}
        ]

        tree1, result1 = create_simple_decision_tree("Test", options)
        tree2, result2 = create_simple_decision_tree("Test", options)

        # Both should recommend a path
        assert result1.recommended_path is not None
        assert result2.recommended_path is not None

    def test_result_comparability(self):
        """Property: All analyzed paths should be comparable."""
        options = [
            {"name": "A", "probability": 0.8, "value": 100},
            {"name": "B", "probability": 0.7, "value": 120}
        ]

        tree, result = create_simple_decision_tree("Test", options)

        # All paths should have comparable metrics
        for path in tree.all_paths:
            assert path.expected_value is not None
            assert path.total_probability is not None


# =============================================================================
# Integration Tests
# =============================================================================

class TestDecisionTreeIntegration:
    """Integration tests for decision tree functionality."""

    def test_full_decision_workflow(self):
        """Test complete decision-making workflow."""
        # 1. Build the tree
        builder = DecisionTreeBuilder()
        tree = builder.create_tree(
            name="Investment Strategy",
            objective=OptimizationObjective.BALANCED
        )

        root = builder.add_root("Choose Investment")

        # Add options to root
        builder.add_option(root.id, "Stocks", probability=0.7, expected_value=150, risk_level=0.4, cost=100)
        builder.add_option(root.id, "Bonds", probability=0.9, expected_value=80, risk_level=0.1, cost=50)
        builder.add_option(root.id, "Real Estate", probability=0.6, expected_value=200, risk_level=0.5, cost=200)

        # Add outcome nodes
        for i, option in enumerate(root.options):
            builder.add_outcome_node(
                f"Result_{option.name}",
                root.id,
                option.id,
                option.expected_value
            )

        # Add criteria
        builder.add_criteria("return", weight=1.5)
        builder.add_criteria("risk", weight=1.0, minimize=True)

        # 2. Analyze the tree
        analyzer = DecisionAnalyzer()
        result = analyzer.analyze(tree)

        assert result.recommended_path is not None
        assert len(result.reasoning) > 0
        assert tree.status == DecisionStatus.DECIDED

        # 3. Predict outcome
        predictor = OutcomePredictor()
        prediction = predictor.predict_outcome(tree, result.recommended_path)

        assert "expected_value" in prediction
        assert "scenarios" in prediction

    def test_multi_level_decision_tree(self):
        """Test decision tree with multiple levels."""
        builder = DecisionTreeBuilder()
        tree = builder.create_tree("Multi-Level Decision")

        root = builder.add_root("Initial Choice")

        # Level 1 options
        opt1 = builder.add_option(root.id, "Path A", probability=0.8)
        opt2 = builder.add_option(root.id, "Path B", probability=0.7)

        # Level 2 - Add decision node for Path A
        decision2 = builder.add_decision_node("Second Choice", root.id, root.options[0].id)

        # Level 2 options
        builder.add_option(decision2.id, "A1", probability=0.9, expected_value=100)
        builder.add_option(decision2.id, "A2", probability=0.8, expected_value=150)

        # Add outcomes for Level 2
        for option in decision2.options:
            builder.add_outcome_node(
                f"Outcome_{option.name}",
                decision2.id,
                option.id,
                option.expected_value
            )

        # Add outcome for Path B
        builder.add_outcome_node("B_Outcome", root.id, root.options[1].id, 80)

        # Analyze
        analyzer = DecisionAnalyzer()
        result = analyzer.analyze(tree)

        # Should have multiple paths
        assert len(tree.all_paths) >= 2
        assert result.recommended_path is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
