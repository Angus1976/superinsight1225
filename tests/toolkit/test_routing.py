"""
Unit tests for the Intelligent Routing Layer.

Tests StrategyRouter, RuleEngine, and CostEstimator against
Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 7.1.
"""

import pytest

from src.toolkit.models.data_profile import (
    BasicInfo,
    CostEstimate,
    DataProfile,
    QualityMetrics,
    SemanticInfo,
    StructureInfo,
)
from src.toolkit.models.enums import DataStructure, Domain, FileType, Language
from src.toolkit.models.processing_plan import (
    Constraints,
    Priority,
    ProcessingPlan,
    ProcessingStage,
    Requirements,
    StorageStrategy,
    StorageType,
)
from src.toolkit.routing.cost_estimator import CostEstimator
from src.toolkit.routing.rule_engine import Rule, RuleEngine, RulePriority
from src.toolkit.routing.strategy_router import StrategyRouter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_csv_profile() -> DataProfile:
    """A small CSV file profile."""
    return DataProfile(
        basic_info=BasicInfo(file_type=FileType.CSV, file_size=1024, record_count=100, column_count=5),
        quality_metrics=QualityMetrics(completeness_score=0.95, consistency_score=0.9),
        structure_info=StructureInfo(data_structure=DataStructure.TABULAR),
    )


@pytest.fixture
def large_excel_profile() -> DataProfile:
    """A large Excel file profile (>50MB)."""
    return DataProfile(
        basic_info=BasicInfo(file_type=FileType.EXCEL, file_size=60 * 1024 * 1024, record_count=500000),
        quality_metrics=QualityMetrics(completeness_score=0.85),
        structure_info=StructureInfo(data_structure=DataStructure.TABULAR),
    )


@pytest.fixture
def text_pdf_profile() -> DataProfile:
    """A PDF text document profile."""
    return DataProfile(
        basic_info=BasicInfo(file_type=FileType.PDF, file_size=2 * 1024 * 1024),
        quality_metrics=QualityMetrics(completeness_score=0.9),
        structure_info=StructureInfo(data_structure=DataStructure.TEXT),
        semantic_info=SemanticInfo(language=Language.ENGLISH, domain=Domain.TECHNOLOGY),
    )


@pytest.fixture
def low_quality_profile() -> DataProfile:
    """A profile with low data quality."""
    return DataProfile(
        basic_info=BasicInfo(file_type=FileType.CSV, file_size=5 * 1024 * 1024),
        quality_metrics=QualityMetrics(completeness_score=0.4, anomaly_count=50),
        structure_info=StructureInfo(data_structure=DataStructure.TABULAR),
    )


@pytest.fixture
def graph_profile() -> DataProfile:
    """A profile with dense relationships."""
    return DataProfile(
        basic_info=BasicInfo(file_type=FileType.JSON, file_size=3 * 1024 * 1024),
        quality_metrics=QualityMetrics(completeness_score=0.9),
        structure_info=StructureInfo(
            data_structure=DataStructure.GRAPH,
            relationships=[{"from": "A", "to": "B"}] * 10,
        ),
    )


@pytest.fixture
def default_requirements() -> Requirements:
    return Requirements()


@pytest.fixture
def router() -> StrategyRouter:
    return StrategyRouter()


@pytest.fixture
def cost_estimator() -> CostEstimator:
    return CostEstimator()


# ---------------------------------------------------------------------------
# RuleEngine Tests
# ---------------------------------------------------------------------------

class TestRuleEngine:
    def test_register_and_count(self):
        engine = RuleEngine()
        rule = Rule(name="test_rule", condition_key="test", action_key="act")
        rid = engine.register_rule(rule, lambda p: True)
        assert engine.rule_count == 1
        assert rid == rule.rule_id

    def test_register_empty_name_raises(self):
        engine = RuleEngine()
        rule = Rule(name="", condition_key="test", action_key="act")
        with pytest.raises(ValueError, match="non-empty name"):
            engine.register_rule(rule, lambda p: True)

    def test_unregister_existing(self):
        engine = RuleEngine()
        rule = Rule(name="test_rule", condition_key="test", action_key="act")
        rid = engine.register_rule(rule, lambda p: True)
        assert engine.unregister_rule(rid) is True
        assert engine.rule_count == 0

    def test_unregister_nonexistent(self):
        engine = RuleEngine()
        assert engine.unregister_rule("nonexistent") is False

    def test_evaluate_matching_rule(self, small_csv_profile):
        engine = RuleEngine()
        rule = Rule(
            name="always_match",
            priority=RulePriority.HIGH,
            condition_key="always",
            action_key="act",
            explanation="Always matches",
        )
        engine.register_rule(rule, lambda p: True)

        matches = engine.evaluate_rules(small_csv_profile)
        assert len(matches) == 1
        assert matches[0].matched is True
        assert matches[0].score == 0.75  # HIGH priority weight

    def test_evaluate_non_matching_rule(self, small_csv_profile):
        engine = RuleEngine()
        rule = Rule(name="never_match", condition_key="never", action_key="act")
        engine.register_rule(rule, lambda p: False)

        matches = engine.evaluate_rules(small_csv_profile)
        assert len(matches) == 1
        assert matches[0].matched is False
        assert matches[0].score == 0.0

    def test_get_matching_rules_filters(self, small_csv_profile):
        engine = RuleEngine()
        engine.register_rule(
            Rule(name="yes", condition_key="y", action_key="a"), lambda p: True
        )
        engine.register_rule(
            Rule(name="no", condition_key="n", action_key="b"), lambda p: False
        )

        matching = engine.get_matching_rules(small_csv_profile)
        assert len(matching) == 1
        assert matching[0].rule.name == "yes"

    def test_condition_exception_handled(self, small_csv_profile):
        engine = RuleEngine()
        rule = Rule(name="error_rule", condition_key="err", action_key="act")

        def bad_condition(p):
            raise RuntimeError("boom")

        engine.register_rule(rule, bad_condition)
        matches = engine.evaluate_rules(small_csv_profile)
        assert matches[0].matched is False

    def test_deterministic_ordering(self, small_csv_profile):
        engine = RuleEngine()
        engine.register_rule(
            Rule(name="b_rule", priority=RulePriority.MEDIUM, condition_key="b", action_key="b"),
            lambda p: True,
        )
        engine.register_rule(
            Rule(name="a_rule", priority=RulePriority.HIGH, condition_key="a", action_key="a"),
            lambda p: True,
        )

        matches = engine.evaluate_rules(small_csv_profile)
        # HIGH priority first, then alphabetical within same priority
        assert matches[0].rule.name == "a_rule"
        assert matches[1].rule.name == "b_rule"


# ---------------------------------------------------------------------------
# CostEstimator Tests
# ---------------------------------------------------------------------------

class TestCostEstimator:
    def test_empty_plan_zero_cost(self, cost_estimator, small_csv_profile):
        plan = ProcessingPlan(stages=[])
        assert cost_estimator.estimate_time(plan, small_csv_profile) == 0.0
        assert cost_estimator.estimate_memory(plan, small_csv_profile) == 0
        assert cost_estimator.estimate_monetary(plan, small_csv_profile) == 0.0

    def test_single_stage_small_file(self, cost_estimator, small_csv_profile):
        stage = ProcessingStage(
            stage_id="s1", stage_name="Test", tool_chain=["tool-a"]
        )
        plan = ProcessingPlan(stages=[stage])

        cost = cost_estimator.estimate_total(plan, small_csv_profile)
        assert cost.time_seconds > 0
        assert cost.memory_bytes > 0
        assert cost.monetary_cost > 0

    def test_large_file_costs_more(self, cost_estimator, small_csv_profile, large_excel_profile):
        stage = ProcessingStage(
            stage_id="s1", stage_name="Test", tool_chain=["tool-a"]
        )
        plan = ProcessingPlan(stages=[stage])

        small_cost = cost_estimator.estimate_total(plan, small_csv_profile)
        large_cost = cost_estimator.estimate_total(plan, large_excel_profile)

        assert large_cost.time_seconds > small_cost.time_seconds
        assert large_cost.memory_bytes > small_cost.memory_bytes
        assert large_cost.monetary_cost > small_cost.monetary_cost

    def test_more_stages_cost_more_time(self, cost_estimator, small_csv_profile):
        one_stage = ProcessingPlan(stages=[
            ProcessingStage(stage_id="s1", stage_name="A", tool_chain=["t1"]),
        ])
        two_stages = ProcessingPlan(stages=[
            ProcessingStage(stage_id="s1", stage_name="A", tool_chain=["t1"]),
            ProcessingStage(stage_id="s2", stage_name="B", tool_chain=["t2"]),
        ])

        cost1 = cost_estimator.estimate_time(one_stage, small_csv_profile)
        cost2 = cost_estimator.estimate_time(two_stages, small_csv_profile)
        assert cost2 > cost1

    def test_exceeds_constraints_time(self, cost_estimator):
        cost = CostEstimate(time_seconds=5000.0, memory_bytes=100, monetary_cost=0.01)
        constraints = Constraints(max_time_seconds=3600.0)
        assert cost_estimator.exceeds_constraints(cost, constraints) is True

    def test_within_constraints(self, cost_estimator):
        cost = CostEstimate(time_seconds=10.0, memory_bytes=100, monetary_cost=0.01)
        constraints = Constraints()
        assert cost_estimator.exceeds_constraints(cost, constraints) is False

    def test_compare_strategies(self, cost_estimator, small_csv_profile):
        plan_a = ProcessingPlan(
            strategy_name="a",
            stages=[ProcessingStage(stage_id="s1", stage_name="A", tool_chain=["t1"])],
        )
        plan_b = ProcessingPlan(
            strategy_name="b",
            stages=[
                ProcessingStage(stage_id="s1", stage_name="B1", tool_chain=["t1"]),
                ProcessingStage(stage_id="s2", stage_name="B2", tool_chain=["t2", "t3"]),
            ],
        )

        comparison = cost_estimator.compare_strategies(
            {"a": plan_a, "b": plan_b}, small_csv_profile
        )
        assert comparison.recommended == "a"  # fewer stages = cheaper
        assert "a" in comparison.strategy_costs
        assert "b" in comparison.strategy_costs

    def test_deterministic_estimates(self, cost_estimator, small_csv_profile):
        """Same inputs produce same outputs (Req 2.2 support)."""
        stage = ProcessingStage(stage_id="s1", stage_name="T", tool_chain=["t1"])
        plan = ProcessingPlan(stages=[stage])

        cost1 = cost_estimator.estimate_total(plan, small_csv_profile)
        cost2 = cost_estimator.estimate_total(plan, small_csv_profile)

        assert cost1.time_seconds == cost2.time_seconds
        assert cost1.memory_bytes == cost2.memory_bytes
        assert cost1.monetary_cost == cost2.monetary_cost


# ---------------------------------------------------------------------------
# StrategyRouter Tests
# ---------------------------------------------------------------------------

class TestStrategyRouter:
    """Tests for StrategyRouter covering Req 2.1–2.5, 7.1."""

    def test_select_strategy_returns_plan(self, router, small_csv_profile, default_requirements):
        """Req 2.1: generates a ProcessingPlan for valid inputs."""
        plan = router.select_strategy(small_csv_profile, default_requirements)
        assert isinstance(plan, ProcessingPlan)
        assert len(plan.stages) > 0
        assert plan.strategy_name != ""

    def test_determinism_same_inputs_same_plan(self, router, small_csv_profile, default_requirements):
        """Req 2.2: same inputs produce same ProcessingPlan."""
        plan1 = router.select_strategy(small_csv_profile, default_requirements)
        plan2 = router.select_strategy(small_csv_profile, default_requirements)

        assert plan1.strategy_name == plan2.strategy_name
        assert len(plan1.stages) == len(plan2.stages)
        assert plan1.explanation == plan2.explanation
        assert plan1.estimated_cost.time_seconds == plan2.estimated_cost.time_seconds
        assert plan1.estimated_cost.monetary_cost == plan2.estimated_cost.monetary_cost

    def test_explanation_non_empty(self, router, small_csv_profile, default_requirements):
        """Req 2.3: provides human-readable explanation."""
        plan = router.select_strategy(small_csv_profile, default_requirements)
        assert plan.explanation != ""
        assert len(plan.explanation) > 10

    def test_default_fallback_on_tight_constraints(self, router, large_excel_profile, default_requirements):
        """Req 2.4: falls back to default when constraints are too tight."""
        tight = Constraints(max_time_seconds=0.001, max_memory_bytes=1, max_monetary_cost=0.0001)
        plan = router.select_strategy(large_excel_profile, default_requirements, tight)

        assert plan.is_default_fallback is True
        assert plan.strategy_name == "default"
        assert "fallback" in plan.explanation.lower() or "default" in plan.explanation.lower()

    def test_cost_estimate_present(self, router, small_csv_profile, default_requirements):
        """Req 2.5 & 7.1: cost estimate has time, memory, monetary."""
        plan = router.select_strategy(small_csv_profile, default_requirements)

        assert plan.estimated_cost.time_seconds >= 0
        assert plan.estimated_cost.memory_bytes >= 0
        assert plan.estimated_cost.monetary_cost >= 0

    def test_large_file_selects_streaming(self, router, large_excel_profile, default_requirements):
        """Large files should trigger streaming strategy."""
        plan = router.select_strategy(large_excel_profile, default_requirements)
        assert plan.strategy_name == "streaming"

    def test_text_pdf_selects_embedding(self, router, text_pdf_profile):
        """Text/PDF files should trigger text embedding strategy."""
        reqs = Requirements(needs_semantic_search=True)
        plan = router.select_strategy(text_pdf_profile, reqs)
        assert plan.strategy_name == "text_embedding"

    def test_low_quality_selects_cleaning(self, router, low_quality_profile, default_requirements):
        """Low quality data should trigger cleaning strategy."""
        plan = router.select_strategy(low_quality_profile, default_requirements)
        assert plan.strategy_name == "data_cleaning"

    def test_graph_data_selects_graph(self, router, graph_profile, default_requirements):
        """Graph data should trigger graph processing strategy."""
        plan = router.select_strategy(graph_profile, default_requirements)
        assert plan.strategy_name == "graph_processing"

    def test_evaluate_strategies_returns_list(self, router, small_csv_profile, default_requirements):
        """evaluate_strategies returns ranked tuples."""
        results = router.evaluate_strategies(small_csv_profile, default_requirements)
        assert isinstance(results, list)
        for name, score, explanation in results:
            assert isinstance(name, str)
            assert isinstance(score, float)
            assert isinstance(explanation, str)

    def test_optimize_plan(self, router, small_csv_profile, default_requirements):
        """optimize_plan re-estimates costs."""
        plan = router.select_strategy(small_csv_profile, default_requirements)
        optimized = router.optimize_plan(plan, small_csv_profile, Constraints())
        assert optimized.estimated_cost.time_seconds >= 0


# ---------------------------------------------------------------------------
# ProcessingPlan Model Tests
# ---------------------------------------------------------------------------

class TestProcessingPlanModel:
    def test_default_plan(self):
        plan = ProcessingPlan()
        assert plan.strategy_name == "default"
        assert plan.stages == []
        assert plan.is_default_fallback is False

    def test_plan_with_stages(self):
        stages = [
            ProcessingStage(stage_id="s1", stage_name="Load"),
            ProcessingStage(stage_id="s2", stage_name="Transform", dependencies=["s1"]),
        ]
        plan = ProcessingPlan(strategy_name="test", stages=stages)
        assert len(plan.stages) == 2
        assert plan.stages[1].dependencies == ["s1"]

    def test_storage_strategy_defaults(self):
        ss = StorageStrategy()
        assert ss.primary_storage == StorageType.POSTGRESQL
        assert ss.secondary_storages == []

    def test_requirements_defaults(self):
        reqs = Requirements()
        assert reqs.priority == Priority.QUALITY
        assert reqs.needs_semantic_search is False

    def test_constraints_defaults(self):
        c = Constraints()
        assert c.max_time_seconds == 3600.0
        assert c.max_monetary_cost == 100.0
