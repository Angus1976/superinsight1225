"""
Property-based tests for the Intelligent Routing Layer.

Validates: Requirements 2.1, 2.2, 2.3, 2.5, 7.1, 7.2
"""

import pytest
from hypothesis import given, settings, strategies as st

from src.toolkit.models.data_profile import BasicInfo, DataProfile, QualityMetrics, StructureInfo
from src.toolkit.models.enums import DataStructure, FileType
from src.toolkit.models.processing_plan import (
    Constraints,
    Priority,
    ProcessingPlan,
    ProcessingStage,
    Requirements,
)
from src.toolkit.routing.cost_estimator import CostEstimator
from src.toolkit.routing.strategy_router import StrategyRouter


# ---------------------------------------------------------------------------
# Hypothesis Strategies
# ---------------------------------------------------------------------------

@st.composite
def data_profiles(draw):
    """Generate random DataProfile objects with varying characteristics."""
    file_size = draw(st.integers(min_value=0, max_value=100 * 1024 * 1024))
    file_type = draw(st.sampled_from(list(FileType)))
    completeness = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    consistency = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    data_structure = draw(st.sampled_from(list(DataStructure)))

    return DataProfile(
        basic_info=BasicInfo(file_type=file_type, file_size=file_size),
        quality_metrics=QualityMetrics(
            completeness_score=completeness,
            consistency_score=consistency,
        ),
        structure_info=StructureInfo(data_structure=data_structure),
    )


@st.composite
def requirements_strategy(draw):
    """Generate random Requirements objects."""
    priority = draw(st.sampled_from(list(Priority)))
    semantic = draw(st.booleans())
    graph = draw(st.booleans())

    return Requirements(
        priority=priority,
        needs_semantic_search=semantic,
        needs_graph_traversal=graph,
    )


# ---------------------------------------------------------------------------
# Property 4: Processing Plan Completeness
# Validates: Requirements 2.1, 2.3, 2.5, 7.1
#
# For any valid DataProfile, select_strategy returns a ProcessingPlan
# with non-empty stages, non-empty explanation, and cost estimates >= 0.
# ---------------------------------------------------------------------------

class TestProcessingPlanCompleteness:
    """**Validates: Requirements 2.1, 2.3, 2.5, 7.1**"""

    @given(profile=data_profiles())
    @settings(deadline=5000)
    def test_plan_has_stages_explanation_and_costs(self, profile: DataProfile):
        router = StrategyRouter()
        plan = router.select_strategy(profile, Requirements())

        assert isinstance(plan, ProcessingPlan)
        assert len(plan.stages) > 0, "Plan must have at least one stage"
        assert plan.explanation != "", "Plan must have a non-empty explanation"
        assert plan.estimated_cost.time_seconds >= 0, "Time cost must be >= 0"
        assert plan.estimated_cost.memory_bytes >= 0, "Memory cost must be >= 0"
        assert plan.estimated_cost.monetary_cost >= 0, "Monetary cost must be >= 0"


# ---------------------------------------------------------------------------
# Property 5: Strategy Determinism
# Validates: Requirement 2.2
#
# For any DataProfile + Requirements, calling select_strategy twice
# with the same inputs produces the same ProcessingPlan.
# ---------------------------------------------------------------------------

class TestStrategyDeterminism:
    """**Validates: Requirement 2.2**"""

    @given(profile=data_profiles(), reqs=requirements_strategy())
    @settings(deadline=5000)
    def test_same_inputs_produce_same_plan(
        self, profile: DataProfile, reqs: Requirements
    ):
        router = StrategyRouter()
        plan1 = router.select_strategy(profile, reqs)
        plan2 = router.select_strategy(profile, reqs)

        assert plan1.strategy_name == plan2.strategy_name, "Strategy name must be deterministic"
        assert len(plan1.stages) == len(plan2.stages), "Stage count must be deterministic"
        assert plan1.explanation == plan2.explanation, "Explanation must be deterministic"
        assert plan1.estimated_cost.time_seconds == plan2.estimated_cost.time_seconds
        assert plan1.estimated_cost.memory_bytes == plan2.estimated_cost.memory_bytes
        assert plan1.estimated_cost.monetary_cost == plan2.estimated_cost.monetary_cost


# ---------------------------------------------------------------------------
# Property 12: Cost Estimation Accuracy (Internal Consistency)
# Validates: Requirements 7.1, 7.2
#
# Since we can't measure "actual" cost in a property test, we verify:
# a) Re-estimating the same plan yields the same cost (determinism)
# b) More stages → higher total time cost
# c) Larger file → higher cost than smaller file
# ---------------------------------------------------------------------------

class TestCostEstimationAccuracy:
    """**Validates: Requirements 7.1, 7.2**"""

    @given(profile=data_profiles())
    @settings(deadline=5000)
    def test_cost_estimation_determinism(self, profile: DataProfile):
        """Re-estimating the same plan yields identical costs."""
        estimator = CostEstimator()
        stage = ProcessingStage(
            stage_id="s1", stage_name="Test", tool_chain=["tool-a"]
        )
        plan = ProcessingPlan(stages=[stage])

        cost1 = estimator.estimate_total(plan, profile)
        cost2 = estimator.estimate_total(plan, profile)

        assert cost1.time_seconds == cost2.time_seconds
        assert cost1.memory_bytes == cost2.memory_bytes
        assert cost1.monetary_cost == cost2.monetary_cost

    @given(profile=data_profiles())
    @settings(deadline=5000)
    def test_more_stages_higher_time_cost(self, profile: DataProfile):
        """A plan with more stages should have higher total time cost."""
        estimator = CostEstimator()

        one_stage = ProcessingPlan(stages=[
            ProcessingStage(stage_id="s1", stage_name="A", tool_chain=["t1"]),
        ])
        two_stages = ProcessingPlan(stages=[
            ProcessingStage(stage_id="s1", stage_name="A", tool_chain=["t1"]),
            ProcessingStage(stage_id="s2", stage_name="B", tool_chain=["t2"]),
        ])

        cost1 = estimator.estimate_time(one_stage, profile)
        cost2 = estimator.estimate_time(two_stages, profile)

        assert cost2 > cost1, "More stages must result in higher time cost"

    @given(
        small_size=st.integers(min_value=0, max_value=9 * 1024 * 1024),
        large_size=st.integers(min_value=101 * 1024 * 1024, max_value=500 * 1024 * 1024),
    )
    @settings(deadline=5000)
    def test_larger_file_higher_cost(self, small_size: int, large_size: int):
        """A larger file should cost more than a smaller file."""
        estimator = CostEstimator()

        small_profile = DataProfile(
            basic_info=BasicInfo(file_size=small_size),
        )
        large_profile = DataProfile(
            basic_info=BasicInfo(file_size=large_size),
        )

        stage = ProcessingStage(
            stage_id="s1", stage_name="Test", tool_chain=["tool-a"]
        )
        plan = ProcessingPlan(stages=[stage])

        small_cost = estimator.estimate_total(plan, small_profile)
        large_cost = estimator.estimate_total(plan, large_profile)

        assert large_cost.time_seconds >= small_cost.time_seconds
        assert large_cost.memory_bytes >= small_cost.memory_bytes
        assert large_cost.monetary_cost >= small_cost.monetary_cost
