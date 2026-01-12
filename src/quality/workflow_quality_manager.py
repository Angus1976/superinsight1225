"""
Workflow Quality Manager for SuperInsight Platform.

Extends the base QualityManager with workflow-specific features:
- Consensus mechanism for multi-annotator agreement
- Enhanced anomaly detection
- Workflow state management
- Quality gate enforcement
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
from collections import defaultdict
import statistics

from src.quality.manager import QualityManager, QualityRule, QualityReport, QualityRuleType
from src.models.quality_issue import QualityIssue, IssueSeverity, IssueStatus

logger = logging.getLogger(__name__)


class ConsensusMethod(str, Enum):
    """Methods for calculating annotator consensus."""
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_VOTE = "weighted_vote"
    UNANIMOUS = "unanimous"
    FLEISS_KAPPA = "fleiss_kappa"
    COHENS_KAPPA = "cohens_kappa"


class QualityGateStatus(str, Enum):
    """Status of quality gates."""
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    BYPASSED = "bypassed"


@dataclass
class AnnotatorProfile:
    """Profile for tracking annotator performance."""
    annotator_id: str
    total_annotations: int = 0
    quality_score: float = 1.0
    agreement_rate: float = 1.0
    expertise_areas: List[str] = field(default_factory=list)
    recent_scores: List[float] = field(default_factory=list)
    last_active: Optional[datetime] = None

    def update_score(self, score: float):
        """Update annotator's quality score."""
        self.recent_scores.append(score)
        if len(self.recent_scores) > 100:
            self.recent_scores = self.recent_scores[-100:]
        self.quality_score = statistics.mean(self.recent_scores)
        self.total_annotations += 1
        self.last_active = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "annotator_id": self.annotator_id,
            "total_annotations": self.total_annotations,
            "quality_score": self.quality_score,
            "agreement_rate": self.agreement_rate,
            "expertise_areas": self.expertise_areas,
            "last_active": self.last_active.isoformat() if self.last_active else None
        }


@dataclass
class ConsensusResult:
    """Result of consensus calculation."""
    task_id: str
    consensus_value: Any
    agreement_score: float
    method_used: ConsensusMethod
    annotator_votes: Dict[str, Any] = field(default_factory=dict)
    disagreements: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "consensus_value": self.consensus_value,
            "agreement_score": self.agreement_score,
            "method_used": self.method_used.value,
            "annotator_votes": self.annotator_votes,
            "disagreements": self.disagreements,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class QualityGate:
    """Defines a quality gate checkpoint."""
    gate_id: str
    name: str
    description: str
    rules: List[str]  # Rule IDs to check
    threshold: float = 0.8
    required: bool = True
    auto_bypass: bool = False
    bypass_conditions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "name": self.name,
            "description": self.description,
            "rules": self.rules,
            "threshold": self.threshold,
            "required": self.required,
            "auto_bypass": self.auto_bypass
        }


@dataclass
class QualityGateResult:
    """Result of quality gate evaluation."""
    gate_id: str
    status: QualityGateStatus
    score: float
    rule_results: List[Dict[str, Any]] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    evaluated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "status": self.status.value,
            "score": self.score,
            "rule_results": self.rule_results,
            "issues": self.issues,
            "evaluated_at": self.evaluated_at.isoformat()
        }


class ConsensusEngine:
    """
    Engine for calculating annotator consensus.
    
    Supports multiple consensus methods and weighted voting.
    """

    def __init__(self):
        self.annotator_profiles: Dict[str, AnnotatorProfile] = {}
        self.consensus_history: List[ConsensusResult] = []

    def get_or_create_profile(self, annotator_id: str) -> AnnotatorProfile:
        """Get or create annotator profile."""
        if annotator_id not in self.annotator_profiles:
            self.annotator_profiles[annotator_id] = AnnotatorProfile(
                annotator_id=annotator_id
            )
        return self.annotator_profiles[annotator_id]

    def calculate_consensus(
        self,
        task_id: str,
        annotations: List[Dict[str, Any]],
        method: ConsensusMethod = ConsensusMethod.WEIGHTED_VOTE,
        label_field: str = "label"
    ) -> ConsensusResult:
        """
        Calculate consensus from multiple annotations.
        
        Args:
            task_id: Task identifier
            annotations: List of annotation dictionaries with annotator_id and label
            method: Consensus calculation method
            label_field: Field name containing the label
            
        Returns:
            ConsensusResult with agreement score and consensus value
        """
        if not annotations:
            return ConsensusResult(
                task_id=task_id,
                consensus_value=None,
                agreement_score=0.0,
                method_used=method
            )

        # Extract votes
        votes = {}
        for ann in annotations:
            annotator_id = ann.get("annotator_id", "unknown")
            label = ann.get(label_field) or ann.get("result", {}).get(label_field)
            if label is not None:
                votes[annotator_id] = label

        if not votes:
            return ConsensusResult(
                task_id=task_id,
                consensus_value=None,
                agreement_score=0.0,
                method_used=method,
                annotator_votes=votes
            )

        # Calculate consensus based on method
        if method == ConsensusMethod.MAJORITY_VOTE:
            result = self._majority_vote(task_id, votes)
        elif method == ConsensusMethod.WEIGHTED_VOTE:
            result = self._weighted_vote(task_id, votes)
        elif method == ConsensusMethod.UNANIMOUS:
            result = self._unanimous_vote(task_id, votes)
        elif method == ConsensusMethod.FLEISS_KAPPA:
            result = self._fleiss_kappa(task_id, votes)
        else:
            result = self._majority_vote(task_id, votes)

        # Store in history
        self.consensus_history.append(result)
        if len(self.consensus_history) > 10000:
            self.consensus_history = self.consensus_history[-10000:]

        return result

    def _majority_vote(self, task_id: str, votes: Dict[str, Any]) -> ConsensusResult:
        """Simple majority voting."""
        vote_counts = defaultdict(int)
        for label in votes.values():
            vote_counts[str(label)] += 1

        total_votes = len(votes)
        max_count = max(vote_counts.values())
        consensus_value = max(vote_counts.keys(), key=lambda k: vote_counts[k])
        agreement_score = max_count / total_votes

        # Find disagreements
        disagreements = []
        for annotator_id, label in votes.items():
            if str(label) != consensus_value:
                disagreements.append({
                    "annotator_id": annotator_id,
                    "voted": label,
                    "consensus": consensus_value
                })

        return ConsensusResult(
            task_id=task_id,
            consensus_value=consensus_value,
            agreement_score=agreement_score,
            method_used=ConsensusMethod.MAJORITY_VOTE,
            annotator_votes=votes,
            disagreements=disagreements,
            confidence=agreement_score
        )

    def _weighted_vote(self, task_id: str, votes: Dict[str, Any]) -> ConsensusResult:
        """Weighted voting based on annotator quality scores."""
        weighted_votes = defaultdict(float)
        total_weight = 0.0

        for annotator_id, label in votes.items():
            profile = self.get_or_create_profile(annotator_id)
            weight = profile.quality_score
            weighted_votes[str(label)] += weight
            total_weight += weight

        if total_weight == 0:
            return self._majority_vote(task_id, votes)

        # Normalize and find consensus
        max_weight = max(weighted_votes.values())
        consensus_value = max(weighted_votes.keys(), key=lambda k: weighted_votes[k])
        agreement_score = max_weight / total_weight

        # Find disagreements
        disagreements = []
        for annotator_id, label in votes.items():
            if str(label) != consensus_value:
                profile = self.get_or_create_profile(annotator_id)
                disagreements.append({
                    "annotator_id": annotator_id,
                    "voted": label,
                    "consensus": consensus_value,
                    "annotator_weight": profile.quality_score
                })

        return ConsensusResult(
            task_id=task_id,
            consensus_value=consensus_value,
            agreement_score=agreement_score,
            method_used=ConsensusMethod.WEIGHTED_VOTE,
            annotator_votes=votes,
            disagreements=disagreements,
            confidence=agreement_score * 0.9 + 0.1  # Slight boost for weighted
        )

    def _unanimous_vote(self, task_id: str, votes: Dict[str, Any]) -> ConsensusResult:
        """Require unanimous agreement."""
        unique_votes = set(str(v) for v in votes.values())
        
        if len(unique_votes) == 1:
            consensus_value = list(votes.values())[0]
            agreement_score = 1.0
            disagreements = []
        else:
            # Fall back to majority for consensus value
            vote_counts = defaultdict(int)
            for label in votes.values():
                vote_counts[str(label)] += 1
            consensus_value = max(vote_counts.keys(), key=lambda k: vote_counts[k])
            agreement_score = 0.0  # No unanimous agreement
            
            disagreements = [
                {"annotator_id": aid, "voted": label, "consensus": consensus_value}
                for aid, label in votes.items()
                if str(label) != consensus_value
            ]

        return ConsensusResult(
            task_id=task_id,
            consensus_value=consensus_value,
            agreement_score=agreement_score,
            method_used=ConsensusMethod.UNANIMOUS,
            annotator_votes=votes,
            disagreements=disagreements,
            confidence=agreement_score
        )

    def _fleiss_kappa(self, task_id: str, votes: Dict[str, Any]) -> ConsensusResult:
        """Calculate Fleiss' Kappa for inter-rater reliability."""
        # Simplified Fleiss Kappa calculation
        vote_counts = defaultdict(int)
        for label in votes.values():
            vote_counts[str(label)] += 1

        n = len(votes)  # Number of raters
        if n < 2:
            return self._majority_vote(task_id, votes)

        # Calculate observed agreement
        total_pairs = n * (n - 1)
        agreement_pairs = sum(c * (c - 1) for c in vote_counts.values())
        p_o = agreement_pairs / total_pairs if total_pairs > 0 else 0

        # Calculate expected agreement
        p_e = sum((c / n) ** 2 for c in vote_counts.values())

        # Calculate kappa
        if p_e == 1:
            kappa = 1.0
        else:
            kappa = (p_o - p_e) / (1 - p_e)

        # Normalize kappa to 0-1 range
        agreement_score = max(0, (kappa + 1) / 2)

        consensus_value = max(vote_counts.keys(), key=lambda k: vote_counts[k])

        disagreements = [
            {"annotator_id": aid, "voted": label, "consensus": consensus_value}
            for aid, label in votes.items()
            if str(label) != consensus_value
        ]

        return ConsensusResult(
            task_id=task_id,
            consensus_value=consensus_value,
            agreement_score=agreement_score,
            method_used=ConsensusMethod.FLEISS_KAPPA,
            annotator_votes=votes,
            disagreements=disagreements,
            confidence=agreement_score
        )

    def update_annotator_agreement(
        self,
        annotator_id: str,
        agreed_with_consensus: bool
    ):
        """Update annotator's agreement rate."""
        profile = self.get_or_create_profile(annotator_id)
        
        # Exponential moving average for agreement rate
        alpha = 0.1
        new_value = 1.0 if agreed_with_consensus else 0.0
        profile.agreement_rate = alpha * new_value + (1 - alpha) * profile.agreement_rate


class WorkflowQualityManager(QualityManager):
    """
    Extended Quality Manager with workflow-specific features.
    
    Adds consensus mechanism, quality gates, and workflow state management.
    """

    def __init__(self):
        super().__init__()
        self.consensus_engine = ConsensusEngine()
        self.quality_gates: Dict[str, QualityGate] = {}
        self.gate_results: Dict[str, List[QualityGateResult]] = defaultdict(list)
        self.workflow_states: Dict[str, Dict[str, Any]] = {}
        self._initialize_default_gates()

    def _initialize_default_gates(self):
        """Initialize default quality gates."""
        # Pre-annotation gate
        pre_annotation_gate = QualityGate(
            gate_id="pre_annotation",
            name="预标注质量门",
            description="检查数据在标注前的质量",
            rules=["annotation_completeness"],
            threshold=0.9,
            required=True
        )

        # Post-annotation gate
        post_annotation_gate = QualityGate(
            gate_id="post_annotation",
            name="标注后质量门",
            description="检查标注完成后的质量",
            rules=["confidence_threshold", "semantic_consistency"],
            threshold=0.8,
            required=True
        )

        # Consensus gate
        consensus_gate = QualityGate(
            gate_id="consensus",
            name="共识质量门",
            description="检查多标注员共识",
            rules=[],  # Uses consensus engine directly
            threshold=0.7,
            required=False
        )

        # Final review gate
        final_gate = QualityGate(
            gate_id="final_review",
            name="最终审核质量门",
            description="最终质量审核",
            rules=["factual_accuracy", "response_relevancy"],
            threshold=0.85,
            required=True
        )

        self.quality_gates = {
            gate.gate_id: gate for gate in [
                pre_annotation_gate, post_annotation_gate,
                consensus_gate, final_gate
            ]
        }

    def add_quality_gate(self, gate: QualityGate):
        """Add a quality gate."""
        self.quality_gates[gate.gate_id] = gate
        logger.info(f"Added quality gate: {gate.name}")

    def remove_quality_gate(self, gate_id: str) -> bool:
        """Remove a quality gate."""
        if gate_id in self.quality_gates:
            del self.quality_gates[gate_id]
            return True
        return False

    async def evaluate_quality_gate(
        self,
        gate_id: str,
        task_id: str,
        data: Dict[str, Any]
    ) -> QualityGateResult:
        """
        Evaluate a quality gate for a task.
        
        Args:
            gate_id: Quality gate identifier
            task_id: Task identifier
            data: Data to evaluate
            
        Returns:
            QualityGateResult with pass/fail status
        """
        gate = self.quality_gates.get(gate_id)
        if not gate:
            return QualityGateResult(
                gate_id=gate_id,
                status=QualityGateStatus.FAILED,
                score=0.0,
                issues=[f"Quality gate {gate_id} not found"]
            )

        rule_results = []
        total_score = 0.0
        issues = []

        # Evaluate each rule in the gate
        for rule_id in gate.rules:
            rule = self.quality_rules.get(rule_id)
            if not rule or not rule.enabled:
                continue

            try:
                # Simplified rule evaluation
                result = await self._evaluate_rule_for_gate(rule, data)
                rule_results.append(result)
                total_score += result.get("score", 0)
                
                if not result.get("passed", False):
                    issues.append(f"Rule {rule_id} failed: {result.get('message', '')}")
            except Exception as e:
                logger.error(f"Error evaluating rule {rule_id}: {e}")
                issues.append(f"Rule {rule_id} error: {str(e)}")

        # Calculate final score
        if rule_results:
            final_score = total_score / len(rule_results)
        else:
            final_score = 1.0  # No rules means pass

        # Determine status
        if final_score >= gate.threshold:
            status = QualityGateStatus.PASSED
        elif gate.auto_bypass and self._check_bypass_conditions(gate, data):
            status = QualityGateStatus.BYPASSED
        else:
            status = QualityGateStatus.FAILED

        result = QualityGateResult(
            gate_id=gate_id,
            status=status,
            score=final_score,
            rule_results=rule_results,
            issues=issues
        )

        # Store result
        self.gate_results[task_id].append(result)

        return result

    async def _evaluate_rule_for_gate(
        self,
        rule: QualityRule,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a single rule for gate checking."""
        # Simplified evaluation based on rule type
        if rule.rule_type == QualityRuleType.CONFIDENCE_THRESHOLD:
            confidence = data.get("confidence", 0)
            threshold = rule.parameters.get("min_confidence", rule.threshold)
            passed = confidence >= threshold
            return {
                "rule_id": rule.rule_id,
                "passed": passed,
                "score": confidence,
                "message": f"Confidence: {confidence:.2f} (threshold: {threshold})"
            }
        
        elif rule.rule_type == QualityRuleType.ANNOTATION_COMPLETENESS:
            required_fields = rule.parameters.get("required_fields", [])
            missing = [f for f in required_fields if f not in data or not data[f]]
            passed = len(missing) == 0
            score = (len(required_fields) - len(missing)) / len(required_fields) if required_fields else 1.0
            return {
                "rule_id": rule.rule_id,
                "passed": passed,
                "score": score,
                "message": f"Missing fields: {missing}" if missing else "All fields present"
            }
        
        else:
            # Default pass for unimplemented rules
            return {
                "rule_id": rule.rule_id,
                "passed": True,
                "score": 1.0,
                "message": "Rule type not fully implemented for gate"
            }

    def _check_bypass_conditions(
        self,
        gate: QualityGate,
        data: Dict[str, Any]
    ) -> bool:
        """Check if bypass conditions are met."""
        conditions = gate.bypass_conditions
        if not conditions:
            return False

        # Check priority bypass
        if conditions.get("high_priority") and data.get("priority") == "high":
            return True

        # Check deadline bypass
        if conditions.get("deadline_approaching"):
            deadline = data.get("deadline")
            if deadline and isinstance(deadline, datetime):
                if deadline - datetime.now() < timedelta(hours=24):
                    return True

        return False

    def calculate_consensus(
        self,
        task_id: str,
        annotations: List[Dict[str, Any]],
        method: ConsensusMethod = ConsensusMethod.WEIGHTED_VOTE
    ) -> ConsensusResult:
        """Calculate consensus for task annotations."""
        return self.consensus_engine.calculate_consensus(
            task_id=task_id,
            annotations=annotations,
            method=method
        )

    def get_annotator_profile(self, annotator_id: str) -> AnnotatorProfile:
        """Get annotator profile."""
        return self.consensus_engine.get_or_create_profile(annotator_id)

    def update_annotator_score(self, annotator_id: str, score: float):
        """Update annotator's quality score."""
        profile = self.consensus_engine.get_or_create_profile(annotator_id)
        profile.update_score(score)

    def set_workflow_state(self, task_id: str, state: Dict[str, Any]):
        """Set workflow state for a task."""
        self.workflow_states[task_id] = {
            **state,
            "updated_at": datetime.now().isoformat()
        }

    def get_workflow_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow state for a task."""
        return self.workflow_states.get(task_id)

    def get_gate_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get quality gate evaluation history for a task."""
        return [r.to_dict() for r in self.gate_results.get(task_id, [])]

    async def run_full_quality_workflow(
        self,
        task_id: str,
        data: Dict[str, Any],
        annotations: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Run the full quality workflow for a task.
        
        Args:
            task_id: Task identifier
            data: Task data
            annotations: Optional list of annotations
            
        Returns:
            Complete workflow result
        """
        results = {
            "task_id": task_id,
            "gates": {},
            "consensus": None,
            "overall_status": "pending",
            "issues": [],
            "timestamp": datetime.now().isoformat()
        }

        # Run pre-annotation gate
        pre_result = await self.evaluate_quality_gate("pre_annotation", task_id, data)
        results["gates"]["pre_annotation"] = pre_result.to_dict()

        if pre_result.status == QualityGateStatus.FAILED:
            results["overall_status"] = "blocked_pre_annotation"
            results["issues"].extend(pre_result.issues)
            return results

        # Run post-annotation gate if annotations exist
        if annotations:
            # Merge annotation data
            merged_data = {**data}
            if annotations:
                merged_data["confidence"] = statistics.mean(
                    [a.get("confidence", 0.5) for a in annotations]
                )

            post_result = await self.evaluate_quality_gate(
                "post_annotation", task_id, merged_data
            )
            results["gates"]["post_annotation"] = post_result.to_dict()

            # Calculate consensus
            if len(annotations) > 1:
                consensus = self.calculate_consensus(task_id, annotations)
                results["consensus"] = consensus.to_dict()

                # Update annotator profiles
                for ann in annotations:
                    annotator_id = ann.get("annotator_id")
                    if annotator_id:
                        agreed = str(ann.get("label")) == str(consensus.consensus_value)
                        self.consensus_engine.update_annotator_agreement(
                            annotator_id, agreed
                        )

            if post_result.status == QualityGateStatus.FAILED:
                results["overall_status"] = "needs_review"
                results["issues"].extend(post_result.issues)
            else:
                results["overall_status"] = "passed"
        else:
            results["overall_status"] = "awaiting_annotation"

        # Update workflow state
        self.set_workflow_state(task_id, {
            "status": results["overall_status"],
            "last_gate": list(results["gates"].keys())[-1] if results["gates"] else None
        })

        return results


# Global instance
workflow_quality_manager = WorkflowQualityManager()
