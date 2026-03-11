"""
Cost Estimator for the Intelligent Routing Layer.

Provides time, memory, and monetary cost estimates for
processing plans based on data profiles.
"""

from typing import Dict, List

from pydantic import BaseModel, Field

from src.toolkit.models.data_profile import CostEstimate, DataProfile
from src.toolkit.models.processing_plan import Constraints, ProcessingPlan, ProcessingStage


# Base cost factors per stage (deterministic constants)
_BASE_TIME_PER_STAGE = 10.0  # seconds
_BASE_MEMORY_PER_STAGE = 50 * 1024 * 1024  # 50 MB
_BASE_MONETARY_PER_STAGE = 0.01  # dollars

# Scale factors based on data size
_SIZE_THRESHOLDS = {
    "small": 10 * 1024 * 1024,       # < 10 MB
    "medium": 100 * 1024 * 1024,     # < 100 MB
}

_SIZE_MULTIPLIERS = {
    "small": 1.0,
    "medium": 3.0,
    "large": 10.0,
}


class CostBreakdown(BaseModel):
    """Detailed cost breakdown per stage."""

    stage_id: str
    stage_name: str
    time_seconds: float = Field(default=0.0, ge=0.0)
    memory_bytes: int = Field(default=0, ge=0)
    monetary_cost: float = Field(default=0.0, ge=0.0)


class CostComparison(BaseModel):
    """Side-by-side cost comparison of multiple strategies."""

    strategy_costs: Dict[str, CostEstimate] = Field(default_factory=dict)
    recommended: str = Field(default="", description="Name of the cheapest strategy")


class CostEstimator:
    """
    Estimates processing costs based on plan stages and data profile.

    All estimates are deterministic: same inputs produce same outputs.
    Cost = base_cost × size_multiplier × stage_count, with per-stage breakdowns.
    """

    def _get_size_multiplier(self, profile: DataProfile) -> float:
        """Determine cost multiplier based on file size."""
        file_size = profile.basic_info.file_size

        if file_size < _SIZE_THRESHOLDS["small"]:
            return _SIZE_MULTIPLIERS["small"]
        if file_size < _SIZE_THRESHOLDS["medium"]:
            return _SIZE_MULTIPLIERS["medium"]
        return _SIZE_MULTIPLIERS["large"]

    def estimate_stage_cost(
        self, stage: ProcessingStage, profile: DataProfile
    ) -> CostBreakdown:
        """Estimate cost for a single processing stage."""
        multiplier = self._get_size_multiplier(profile)
        tool_count = max(len(stage.tool_chain), 1)

        return CostBreakdown(
            stage_id=stage.stage_id,
            stage_name=stage.stage_name,
            time_seconds=_BASE_TIME_PER_STAGE * multiplier * tool_count,
            memory_bytes=int(_BASE_MEMORY_PER_STAGE * multiplier),
            monetary_cost=_BASE_MONETARY_PER_STAGE * multiplier * tool_count,
        )

    def estimate_time(self, plan: ProcessingPlan, profile: DataProfile) -> float:
        """Estimate total processing time in seconds."""
        if not plan.stages:
            return 0.0

        return sum(
            self.estimate_stage_cost(s, profile).time_seconds
            for s in plan.stages
        )

    def estimate_memory(self, plan: ProcessingPlan, profile: DataProfile) -> int:
        """Estimate peak memory usage in bytes (max across stages)."""
        if not plan.stages:
            return 0

        return max(
            self.estimate_stage_cost(s, profile).memory_bytes
            for s in plan.stages
        )

    def estimate_monetary(self, plan: ProcessingPlan, profile: DataProfile) -> float:
        """Estimate total monetary cost in dollars."""
        if not plan.stages:
            return 0.0

        return sum(
            self.estimate_stage_cost(s, profile).monetary_cost
            for s in plan.stages
        )

    def estimate_total(self, plan: ProcessingPlan, profile: DataProfile) -> CostEstimate:
        """Compute full cost estimate with time, memory, and monetary breakdown."""
        return CostEstimate(
            time_seconds=self.estimate_time(plan, profile),
            memory_bytes=self.estimate_memory(plan, profile),
            monetary_cost=self.estimate_monetary(plan, profile),
        )

    def exceeds_constraints(
        self, cost: CostEstimate, constraints: Constraints
    ) -> bool:
        """Check if a cost estimate exceeds the given constraints."""
        if cost.time_seconds > constraints.max_time_seconds:
            return True
        if cost.memory_bytes > constraints.max_memory_bytes:
            return True
        if cost.monetary_cost > constraints.max_monetary_cost:
            return True
        return False

    def compare_strategies(
        self,
        strategy_plans: Dict[str, ProcessingPlan],
        profile: DataProfile,
    ) -> CostComparison:
        """Compare costs across multiple strategy plans."""
        costs: Dict[str, CostEstimate] = {}
        best_name = ""
        best_monetary = float("inf")

        for name in sorted(strategy_plans.keys()):
            plan = strategy_plans[name]
            estimate = self.estimate_total(plan, profile)
            costs[name] = estimate

            if estimate.monetary_cost < best_monetary:
                best_monetary = estimate.monetary_cost
                best_name = name

        return CostComparison(strategy_costs=costs, recommended=best_name)
