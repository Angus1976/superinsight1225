"""
Rule Engine for the Intelligent Routing Layer.

Evaluates data profiles against a set of rules to filter
and recommend processing strategies.
"""

from enum import Enum
from typing import Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from src.toolkit.models.data_profile import DataProfile


class RulePriority(str, Enum):
    """Priority levels for routing rules."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Priority weights for deterministic scoring
_PRIORITY_WEIGHTS: Dict[RulePriority, float] = {
    RulePriority.CRITICAL: 1.0,
    RulePriority.HIGH: 0.75,
    RulePriority.MEDIUM: 0.5,
    RulePriority.LOW: 0.25,
}


class Rule(BaseModel):
    """A single routing rule with condition, action, and explanation."""

    rule_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str = Field(..., description="Human-readable rule name")
    priority: RulePriority = Field(default=RulePriority.MEDIUM)
    explanation: str = Field(default="", description="Why this rule applies")

    # condition and action are stored as string keys; evaluated externally
    condition_key: str = Field(..., description="Key identifying the condition logic")
    action_key: str = Field(..., description="Key identifying the action to take")

    model_config = {"frozen": True}


class RuleMatch(BaseModel):
    """Result of evaluating a rule against a data profile."""

    rule: Rule
    matched: bool = Field(default=False)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    explanation: str = Field(default="")


# Type alias for condition functions: DataProfile -> bool
ConditionFn = Callable[[DataProfile], bool]


class RuleEngine:
    """
    Evaluates data profiles against registered rules.

    Rules are registered with condition functions that inspect
    a DataProfile and return True/False. The engine evaluates
    all rules deterministically and returns sorted matches.
    """

    def __init__(self) -> None:
        self._rules: Dict[str, Rule] = {}
        self._conditions: Dict[str, ConditionFn] = {}

    def register_rule(self, rule: Rule, condition: ConditionFn) -> str:
        """Register a rule with its condition function. Returns rule_id."""
        if not rule.name:
            raise ValueError("Rule must have a non-empty name")

        self._rules[rule.rule_id] = rule
        self._conditions[rule.rule_id] = condition
        return rule.rule_id

    def unregister_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID. Returns True if found and removed."""
        if rule_id not in self._rules:
            return False

        del self._rules[rule_id]
        del self._conditions[rule_id]
        return True

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def evaluate_rules(self, profile: DataProfile) -> List[RuleMatch]:
        """
        Evaluate all registered rules against a profile.

        Returns a deterministically sorted list of RuleMatch objects,
        ordered by priority weight (descending), then rule name.
        """
        matches: List[RuleMatch] = []

        # Sort rules by (priority_weight desc, name asc) for determinism
        sorted_rules = sorted(
            self._rules.values(),
            key=lambda r: (-_PRIORITY_WEIGHTS[r.priority], r.name),
        )

        for rule in sorted_rules:
            match = self._evaluate_single(rule, profile)
            matches.append(match)

        return matches

    def get_matching_rules(self, profile: DataProfile) -> List[RuleMatch]:
        """Return only rules that matched the profile, sorted by score."""
        all_matches = self.evaluate_rules(profile)
        return [m for m in all_matches if m.matched]

    def _evaluate_single(self, rule: Rule, profile: DataProfile) -> RuleMatch:
        """Evaluate a single rule against a profile."""
        condition = self._conditions.get(rule.rule_id)
        if condition is None:
            return RuleMatch(rule=rule, matched=False, explanation="No condition registered")

        try:
            matched = condition(profile)
        except Exception:
            return RuleMatch(rule=rule, matched=False, explanation="Condition evaluation failed")

        score = _PRIORITY_WEIGHTS[rule.priority] if matched else 0.0
        explanation = rule.explanation if matched else ""

        return RuleMatch(rule=rule, matched=matched, score=score, explanation=explanation)
