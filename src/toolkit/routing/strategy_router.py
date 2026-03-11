"""
Strategy Router for the Intelligent Routing Layer.

Combines rule-based filtering, score-based ranking, and cost optimization
to select the optimal processing strategy for a given data profile.
"""

from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from src.toolkit.models.data_profile import CostEstimate, DataProfile
from src.toolkit.models.enums import DataStructure, FileType
from src.toolkit.models.processing_plan import (
    Constraints,
    Priority,
    ProcessingPlan,
    ProcessingStage,
    Requirements,
    StorageStrategy,
    StorageType,
)
from .cost_estimator import CostEstimator
from .rule_engine import Rule, RuleEngine, RuleMatch, RulePriority


class _StrategyCandidate:
    """Internal scored strategy candidate."""

    __slots__ = ("name", "stages", "storage", "score", "explanations")

    def __init__(self, name: str, stages: List[ProcessingStage], storage: StorageStrategy):
        self.name = name
        self.stages = stages
        self.storage = storage
        self.score: float = 0.0
        self.explanations: List[str] = []


# ---------------------------------------------------------------------------
# Built-in strategy definitions (deterministic, no randomness)
# ---------------------------------------------------------------------------

def _build_streaming_strategy() -> _StrategyCandidate:
    """Strategy for large files: streaming processing."""
    stages = [
        ProcessingStage(
            stage_id="stream-read",
            stage_name="Streaming Read",
            tool_chain=["streaming-processor"],
            input_format="raw",
            output_format="chunks",
        ),
        ProcessingStage(
            stage_id="stream-transform",
            stage_name="Chunk Transform",
            tool_chain=["chunk-transformer"],
            input_format="chunks",
            output_format="structured",
            dependencies=["stream-read"],
        ),
    ]
    storage = StorageStrategy(primary_storage=StorageType.POSTGRESQL)
    return _StrategyCandidate("streaming", stages, storage)


def _build_in_memory_strategy() -> _StrategyCandidate:
    """Strategy for small files: in-memory processing."""
    stages = [
        ProcessingStage(
            stage_id="mem-load",
            stage_name="In-Memory Load",
            tool_chain=["in-memory-processor"],
            input_format="raw",
            output_format="structured",
        ),
    ]
    storage = StorageStrategy(primary_storage=StorageType.POSTGRESQL)
    return _StrategyCandidate("in_memory", stages, storage)


def _build_text_embedding_strategy() -> _StrategyCandidate:
    """Strategy for text data needing semantic search."""
    stages = [
        ProcessingStage(
            stage_id="text-chunk",
            stage_name="Text Chunking",
            tool_chain=["text-chunker"],
            input_format="text",
            output_format="chunks",
        ),
        ProcessingStage(
            stage_id="embed-gen",
            stage_name="Embedding Generation",
            tool_chain=["embedding-generator"],
            input_format="chunks",
            output_format="vectors",
            dependencies=["text-chunk"],
        ),
    ]
    storage = StorageStrategy(primary_storage=StorageType.VECTOR_DB)
    return _StrategyCandidate("text_embedding", stages, storage)


def _build_graph_strategy() -> _StrategyCandidate:
    """Strategy for data with dense relationships."""
    stages = [
        ProcessingStage(
            stage_id="graph-extract",
            stage_name="Relationship Extraction",
            tool_chain=["relationship-extractor"],
            input_format="structured",
            output_format="graph",
        ),
    ]
    storage = StorageStrategy(primary_storage=StorageType.GRAPH_DB)
    return _StrategyCandidate("graph_processing", stages, storage)


def _build_cleaning_strategy() -> _StrategyCandidate:
    """Strategy for low-quality data: cleaning first."""
    stages = [
        ProcessingStage(
            stage_id="clean",
            stage_name="Data Cleaning",
            tool_chain=["data-cleaning-tool"],
            input_format="raw",
            output_format="cleaned",
        ),
        ProcessingStage(
            stage_id="process",
            stage_name="Standard Processing",
            tool_chain=["in-memory-processor"],
            input_format="cleaned",
            output_format="structured",
            dependencies=["clean"],
        ),
    ]
    storage = StorageStrategy(primary_storage=StorageType.POSTGRESQL)
    return _StrategyCandidate("data_cleaning", stages, storage)


def _build_default_strategy() -> _StrategyCandidate:
    """Fallback default strategy for any data."""
    stages = [
        ProcessingStage(
            stage_id="default-process",
            stage_name="Default Processing",
            tool_chain=["generic-processor"],
            input_format="any",
            output_format="structured",
        ),
    ]
    storage = StorageStrategy(primary_storage=StorageType.POSTGRESQL)
    return _StrategyCandidate("default", stages, storage)


# All built-in strategies in deterministic order
_STRATEGY_BUILDERS = [
    _build_streaming_strategy,
    _build_in_memory_strategy,
    _build_text_embedding_strategy,
    _build_graph_strategy,
    _build_cleaning_strategy,
]


class StrategyRouter:
    """
    Selects optimal processing strategies using rule-based filtering,
    score-based ranking, and cost optimization.

    Deterministic: same DataProfile + Requirements → same ProcessingPlan.
    Falls back to a default strategy when no candidates pass constraints.
    """

    def __init__(self) -> None:
        self._rule_engine = RuleEngine()
        self._cost_estimator = CostEstimator()
        self._register_default_rules()

    @property
    def rule_engine(self) -> RuleEngine:
        return self._rule_engine

    @property
    def cost_estimator(self) -> CostEstimator:
        return self._cost_estimator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_strategy(
        self,
        profile: DataProfile,
        requirements: Requirements,
        constraints: Optional[Constraints] = None,
    ) -> ProcessingPlan:
        """
        Select the optimal strategy for the given profile and requirements.

        Algorithm:
        1. Rule-based filtering of candidate strategies
        2. Score-based ranking
        3. Cost-based optimization (filter by constraints)
        4. Generate plan with explanation

        Returns a ProcessingPlan (falls back to default if needed).
        """
        if constraints is None:
            constraints = Constraints()

        # Step 1 & 2: Get ranked candidates
        ranked = self._rank_candidates(profile, requirements)

        # Step 3: Cost-based filtering
        best = self._select_best_within_constraints(ranked, profile, constraints)

        # Step 4: Build plan
        if best is None:
            return self._create_default_plan(profile, constraints)

        return self._build_plan(best, profile)

    def evaluate_strategies(
        self, profile: DataProfile, requirements: Requirements
    ) -> List[Tuple[str, float, str]]:
        """
        Evaluate all strategies and return ranked list of (name, score, explanation).
        Useful for UI display of all options.
        """
        ranked = self._rank_candidates(profile, requirements)
        return [
            (c.name, c.score, "; ".join(c.explanations) if c.explanations else "No rules matched")
            for c in ranked
        ]

    def optimize_plan(
        self, plan: ProcessingPlan, profile: DataProfile, constraints: Constraints
    ) -> ProcessingPlan:
        """Re-estimate costs for an existing plan against new constraints."""
        cost = self._cost_estimator.estimate_total(plan, profile)
        return plan.model_copy(update={"estimated_cost": cost})


    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _register_default_rules(self) -> None:
        """Register built-in routing rules."""
        rules_and_conditions = [
            (
                Rule(
                    name="large_file_streaming",
                    priority=RulePriority.HIGH,
                    explanation="Large files (>50MB) require streaming to avoid memory issues",
                    condition_key="large_file",
                    action_key="streaming",
                ),
                lambda p: p.basic_info.file_size > 50 * 1024 * 1024,
            ),
            (
                Rule(
                    name="small_file_in_memory",
                    priority=RulePriority.MEDIUM,
                    explanation="Small files (<10MB) can be processed entirely in memory",
                    condition_key="small_file",
                    action_key="in_memory",
                ),
                lambda p: p.basic_info.file_size < 10 * 1024 * 1024,
            ),
            (
                Rule(
                    name="text_embedding_for_search",
                    priority=RulePriority.HIGH,
                    explanation="Text data for semantic search requires embedding generation",
                    condition_key="text_semantic",
                    action_key="text_embedding",
                ),
                lambda p: (
                    p.structure_info.data_structure == DataStructure.TEXT
                    or p.basic_info.file_type in (FileType.TEXT, FileType.PDF)
                ),
            ),
            (
                Rule(
                    name="graph_for_relationships",
                    priority=RulePriority.HIGH,
                    explanation="Data with dense relationships benefits from graph processing",
                    condition_key="graph_data",
                    action_key="graph_processing",
                ),
                lambda p: (
                    p.structure_info.data_structure == DataStructure.GRAPH
                    or len(p.structure_info.relationships) > 5
                ),
            ),
            (
                Rule(
                    name="low_quality_cleaning",
                    priority=RulePriority.CRITICAL,
                    explanation="Low quality data needs cleaning before processing",
                    condition_key="low_quality",
                    action_key="data_cleaning",
                ),
                lambda p: p.quality_metrics.completeness_score < 0.7,
            ),
        ]

        for rule, condition in rules_and_conditions:
            self._rule_engine.register_rule(rule, condition)

    def _get_all_candidates(self) -> List[_StrategyCandidate]:
        """Build all candidate strategies in deterministic order."""
        return [builder() for builder in _STRATEGY_BUILDERS]

    def _rank_candidates(
        self, profile: DataProfile, requirements: Requirements
    ) -> List[_StrategyCandidate]:
        """Filter and rank candidates using rules + requirements scoring."""
        matches = self._rule_engine.get_matching_rules(profile)
        matched_actions = {m.rule.action_key: m for m in matches}

        candidates = self._get_all_candidates()
        scored: List[_StrategyCandidate] = []

        for candidate in candidates:
            match = matched_actions.get(candidate.name)
            if match is None:
                continue

            candidate.score = match.score
            candidate.explanations.append(match.explanation)

            # Boost score based on requirements alignment
            candidate.score += self._requirements_bonus(candidate, requirements)
            scored.append(candidate)

        # Deterministic sort: score desc, then name asc
        scored.sort(key=lambda c: (-c.score, c.name))
        return scored

    def _requirements_bonus(
        self, candidate: _StrategyCandidate, requirements: Requirements
    ) -> float:
        """Add bonus score based on how well candidate matches requirements."""
        bonus = 0.0

        if requirements.needs_semantic_search and candidate.name == "text_embedding":
            bonus += 0.3
        if requirements.needs_graph_traversal and candidate.name == "graph_processing":
            bonus += 0.3
        if requirements.priority == Priority.SPEED and candidate.name == "in_memory":
            bonus += 0.2
        if requirements.priority == Priority.COST and candidate.name == "in_memory":
            bonus += 0.1

        return bonus

    def _select_best_within_constraints(
        self,
        ranked: List[_StrategyCandidate],
        profile: DataProfile,
        constraints: Constraints,
    ) -> Optional[_StrategyCandidate]:
        """Return the highest-ranked candidate that fits within constraints."""
        for candidate in ranked:
            plan = self._candidate_to_plan(candidate, profile)
            cost = self._cost_estimator.estimate_total(plan, profile)

            if not self._cost_estimator.exceeds_constraints(cost, constraints):
                return candidate

        return None

    def _candidate_to_plan(
        self, candidate: _StrategyCandidate, profile: DataProfile
    ) -> ProcessingPlan:
        """Convert a candidate to a ProcessingPlan (without final cost/explanation)."""
        return ProcessingPlan(
            strategy_name=candidate.name,
            stages=candidate.stages,
            storage_strategy=candidate.storage,
        )

    def _build_plan(
        self, candidate: _StrategyCandidate, profile: DataProfile
    ) -> ProcessingPlan:
        """Build the final ProcessingPlan with cost estimate and explanation."""
        plan = self._candidate_to_plan(candidate, profile)
        cost = self._cost_estimator.estimate_total(plan, profile)
        explanation = self._generate_explanation(candidate, profile, cost)

        return plan.model_copy(
            update={
                "estimated_cost": cost,
                "explanation": explanation,
                "is_default_fallback": False,
            }
        )

    def _create_default_plan(
        self, profile: DataProfile, constraints: Constraints
    ) -> ProcessingPlan:
        """Create a default fallback plan when no candidates pass constraints."""
        default = _build_default_strategy()
        plan = self._candidate_to_plan(default, profile)
        cost = self._cost_estimator.estimate_total(plan, profile)

        explanation = (
            "All candidate strategies exceeded resource constraints. "
            "Falling back to default processing strategy."
        )

        return plan.model_copy(
            update={
                "estimated_cost": cost,
                "explanation": explanation,
                "is_default_fallback": True,
            }
        )

    def _generate_explanation(
        self,
        candidate: _StrategyCandidate,
        profile: DataProfile,
        cost: CostEstimate,
    ) -> str:
        """Generate a human-readable explanation for the routing decision."""
        parts = [f"Selected strategy: {candidate.name}."]

        if candidate.explanations:
            parts.append("Reasons: " + "; ".join(candidate.explanations) + ".")

        parts.append(
            f"Estimated cost: {cost.time_seconds:.1f}s processing time, "
            f"{cost.memory_bytes / (1024 * 1024):.0f}MB memory, "
            f"${cost.monetary_cost:.4f}."
        )

        return " ".join(parts)
