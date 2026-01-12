"""
Consensus Engine for Multi-Annotator Agreement.

Provides advanced consensus calculation methods:
- Inter-annotator agreement metrics
- Weighted voting systems
- Disagreement analysis
- Annotator reliability tracking
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics
import math

logger = logging.getLogger(__name__)


class AgreementMetric(str, Enum):
    """Types of agreement metrics."""
    PERCENT_AGREEMENT = "percent_agreement"
    COHENS_KAPPA = "cohens_kappa"
    FLEISS_KAPPA = "fleiss_kappa"
    KRIPPENDORFF_ALPHA = "krippendorff_alpha"
    SCOTTS_PI = "scotts_pi"


class DisagreementType(str, Enum):
    """Types of disagreements."""
    MINOR = "minor"  # Small difference in labels
    MAJOR = "major"  # Significant difference
    CRITICAL = "critical"  # Completely opposite labels
    SYSTEMATIC = "systematic"  # Pattern of disagreement


@dataclass
class DisagreementAnalysis:
    """Analysis of disagreements between annotators."""
    task_id: str
    disagreement_type: DisagreementType
    annotators_involved: List[str]
    labels_in_conflict: Dict[str, Any]
    severity_score: float
    potential_causes: List[str]
    resolution_suggestions: List[str]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "disagreement_type": self.disagreement_type.value,
            "annotators_involved": self.annotators_involved,
            "labels_in_conflict": self.labels_in_conflict,
            "severity_score": self.severity_score,
            "potential_causes": self.potential_causes,
            "resolution_suggestions": self.resolution_suggestions,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class AgreementReport:
    """Comprehensive agreement report."""
    project_id: str
    total_tasks: int
    tasks_with_agreement: int
    tasks_with_disagreement: int
    overall_agreement_rate: float
    metric_scores: Dict[AgreementMetric, float] = field(default_factory=dict)
    annotator_reliability: Dict[str, float] = field(default_factory=dict)
    common_disagreement_patterns: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "total_tasks": self.total_tasks,
            "tasks_with_agreement": self.tasks_with_agreement,
            "tasks_with_disagreement": self.tasks_with_disagreement,
            "overall_agreement_rate": self.overall_agreement_rate,
            "metric_scores": {k.value: v for k, v in self.metric_scores.items()},
            "annotator_reliability": self.annotator_reliability,
            "common_disagreement_patterns": self.common_disagreement_patterns,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at.isoformat()
        }


class AdvancedConsensusEngine:
    """
    Advanced consensus engine with multiple agreement metrics.
    
    Provides comprehensive inter-annotator agreement analysis.
    """

    def __init__(self):
        self.task_annotations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.disagreement_history: List[DisagreementAnalysis] = []
        self.annotator_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total_annotations": 0,
                "agreements": 0,
                "disagreements": 0,
                "reliability_score": 1.0,
                "expertise_confidence": {}
            }
        )

    def add_annotation(
        self,
        task_id: str,
        annotator_id: str,
        label: Any,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add an annotation for consensus tracking."""
        annotation = {
            "annotator_id": annotator_id,
            "label": label,
            "confidence": confidence,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        self.task_annotations[task_id].append(annotation)
        self.annotator_stats[annotator_id]["total_annotations"] += 1

    def calculate_agreement(
        self,
        task_id: str,
        metric: AgreementMetric = AgreementMetric.PERCENT_AGREEMENT
    ) -> float:
        """
        Calculate agreement score for a task.
        
        Args:
            task_id: Task identifier
            metric: Agreement metric to use
            
        Returns:
            Agreement score (0-1)
        """
        annotations = self.task_annotations.get(task_id, [])
        if len(annotations) < 2:
            return 1.0  # Single annotator = perfect agreement

        labels = [a["label"] for a in annotations]

        if metric == AgreementMetric.PERCENT_AGREEMENT:
            return self._percent_agreement(labels)
        elif metric == AgreementMetric.COHENS_KAPPA:
            return self._cohens_kappa(labels)
        elif metric == AgreementMetric.FLEISS_KAPPA:
            return self._fleiss_kappa(labels)
        elif metric == AgreementMetric.KRIPPENDORFF_ALPHA:
            return self._krippendorff_alpha(labels)
        elif metric == AgreementMetric.SCOTTS_PI:
            return self._scotts_pi(labels)
        else:
            return self._percent_agreement(labels)

    def _percent_agreement(self, labels: List[Any]) -> float:
        """Calculate simple percent agreement."""
        if not labels:
            return 0.0
        
        label_counts = defaultdict(int)
        for label in labels:
            label_counts[str(label)] += 1
        
        max_count = max(label_counts.values())
        return max_count / len(labels)

    def _cohens_kappa(self, labels: List[Any]) -> float:
        """Calculate Cohen's Kappa for two raters."""
        if len(labels) != 2:
            # Fall back to percent agreement for non-pair
            return self._percent_agreement(labels)

        # For two labels, calculate kappa
        label_set = list(set(str(l) for l in labels))
        if len(label_set) == 1:
            return 1.0  # Perfect agreement

        # Observed agreement
        p_o = 1.0 if str(labels[0]) == str(labels[1]) else 0.0

        # Expected agreement (assuming random)
        p_e = 1.0 / len(label_set)

        if p_e == 1:
            return 1.0

        kappa = (p_o - p_e) / (1 - p_e)
        return max(0, (kappa + 1) / 2)  # Normalize to 0-1

    def _fleiss_kappa(self, labels: List[Any]) -> float:
        """Calculate Fleiss' Kappa for multiple raters."""
        n = len(labels)
        if n < 2:
            return 1.0

        label_counts = defaultdict(int)
        for label in labels:
            label_counts[str(label)] += 1

        # Calculate P_i (proportion of agreement for this item)
        sum_squared = sum(c * c for c in label_counts.values())
        p_i = (sum_squared - n) / (n * (n - 1)) if n > 1 else 1.0

        # Calculate P_e (expected agreement by chance)
        p_j = {k: v / n for k, v in label_counts.items()}
        p_e = sum(p * p for p in p_j.values())

        if p_e == 1:
            return 1.0

        kappa = (p_i - p_e) / (1 - p_e)
        return max(0, (kappa + 1) / 2)  # Normalize to 0-1

    def _krippendorff_alpha(self, labels: List[Any]) -> float:
        """Calculate Krippendorff's Alpha."""
        # Simplified implementation
        n = len(labels)
        if n < 2:
            return 1.0

        # Calculate observed disagreement
        label_counts = defaultdict(int)
        for label in labels:
            label_counts[str(label)] += 1

        # Observed disagreement
        d_o = 1 - self._percent_agreement(labels)

        # Expected disagreement
        unique_labels = len(label_counts)
        d_e = (unique_labels - 1) / unique_labels if unique_labels > 1 else 0

        if d_e == 0:
            return 1.0

        alpha = 1 - (d_o / d_e)
        return max(0, (alpha + 1) / 2)  # Normalize to 0-1

    def _scotts_pi(self, labels: List[Any]) -> float:
        """Calculate Scott's Pi."""
        # Similar to Cohen's Kappa but with different expected agreement
        return self._fleiss_kappa(labels)  # Simplified

    def analyze_disagreement(
        self,
        task_id: str,
        label_hierarchy: Optional[Dict[str, List[str]]] = None
    ) -> Optional[DisagreementAnalysis]:
        """
        Analyze disagreement for a task.
        
        Args:
            task_id: Task identifier
            label_hierarchy: Optional hierarchy for determining disagreement severity
            
        Returns:
            DisagreementAnalysis or None if no disagreement
        """
        annotations = self.task_annotations.get(task_id, [])
        if len(annotations) < 2:
            return None

        labels = {a["annotator_id"]: a["label"] for a in annotations}
        unique_labels = set(str(l) for l in labels.values())

        if len(unique_labels) == 1:
            return None  # No disagreement

        # Determine disagreement type
        disagreement_type = self._classify_disagreement(
            list(labels.values()), label_hierarchy
        )

        # Calculate severity
        severity = self._calculate_disagreement_severity(
            list(labels.values()), label_hierarchy
        )

        # Identify potential causes
        causes = self._identify_disagreement_causes(annotations)

        # Generate resolution suggestions
        suggestions = self._generate_resolution_suggestions(
            disagreement_type, annotations
        )

        analysis = DisagreementAnalysis(
            task_id=task_id,
            disagreement_type=disagreement_type,
            annotators_involved=list(labels.keys()),
            labels_in_conflict=labels,
            severity_score=severity,
            potential_causes=causes,
            resolution_suggestions=suggestions
        )

        self.disagreement_history.append(analysis)
        
        # Update annotator stats
        for annotator_id in labels.keys():
            self.annotator_stats[annotator_id]["disagreements"] += 1

        return analysis

    def _classify_disagreement(
        self,
        labels: List[Any],
        hierarchy: Optional[Dict[str, List[str]]] = None
    ) -> DisagreementType:
        """Classify the type of disagreement."""
        unique_labels = set(str(l) for l in labels)
        
        if len(unique_labels) == 2:
            # Check if labels are related in hierarchy
            if hierarchy:
                l1, l2 = list(unique_labels)
                if l1 in hierarchy.get(l2, []) or l2 in hierarchy.get(l1, []):
                    return DisagreementType.MINOR
            return DisagreementType.MAJOR
        elif len(unique_labels) > 2:
            return DisagreementType.CRITICAL
        
        return DisagreementType.MINOR

    def _calculate_disagreement_severity(
        self,
        labels: List[Any],
        hierarchy: Optional[Dict[str, List[str]]] = None
    ) -> float:
        """Calculate severity score for disagreement (0-1)."""
        unique_labels = set(str(l) for l in labels)
        n_unique = len(unique_labels)
        n_total = len(labels)

        # Base severity on number of unique labels
        base_severity = (n_unique - 1) / n_total

        # Adjust based on distribution
        label_counts = defaultdict(int)
        for label in labels:
            label_counts[str(label)] += 1

        # Higher severity if votes are evenly split
        max_count = max(label_counts.values())
        distribution_factor = 1 - (max_count / n_total)

        return min(1.0, base_severity + distribution_factor * 0.5)

    def _identify_disagreement_causes(
        self,
        annotations: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify potential causes of disagreement."""
        causes = []

        # Check confidence levels
        confidences = [a.get("confidence", 1.0) for a in annotations]
        if min(confidences) < 0.5:
            causes.append("低置信度标注可能导致不一致")

        # Check for systematic patterns
        annotator_labels = defaultdict(list)
        for a in annotations:
            annotator_labels[a["annotator_id"]].append(a["label"])

        # Check if specific annotator consistently differs
        if len(annotator_labels) > 2:
            causes.append("多标注员参与可能增加分歧")

        # Check time-based patterns
        timestamps = [a.get("timestamp") for a in annotations if a.get("timestamp")]
        if timestamps and len(timestamps) > 1:
            causes.append("标注时间差异可能影响一致性")

        if not causes:
            causes.append("标注指南理解差异")

        return causes

    def _generate_resolution_suggestions(
        self,
        disagreement_type: DisagreementType,
        annotations: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate suggestions for resolving disagreement."""
        suggestions = []

        if disagreement_type == DisagreementType.MINOR:
            suggestions.append("建议由高级标注员进行仲裁")
            suggestions.append("可考虑接受多数投票结果")
        elif disagreement_type == DisagreementType.MAJOR:
            suggestions.append("需要专家审核和决策")
            suggestions.append("建议更新标注指南以明确边界情况")
        elif disagreement_type == DisagreementType.CRITICAL:
            suggestions.append("需要项目负责人介入")
            suggestions.append("建议组织标注员培训会议")
            suggestions.append("考虑重新定义标签体系")

        # Add confidence-based suggestions
        low_confidence = [a for a in annotations if a.get("confidence", 1.0) < 0.7]
        if low_confidence:
            suggestions.append("对低置信度标注进行重新审核")

        return suggestions

    def generate_agreement_report(
        self,
        project_id: str,
        task_ids: Optional[List[str]] = None
    ) -> AgreementReport:
        """
        Generate comprehensive agreement report.
        
        Args:
            project_id: Project identifier
            task_ids: Optional list of task IDs to include
            
        Returns:
            AgreementReport with detailed analysis
        """
        if task_ids is None:
            task_ids = list(self.task_annotations.keys())

        total_tasks = len(task_ids)
        tasks_with_agreement = 0
        tasks_with_disagreement = 0
        all_agreement_scores = []

        for task_id in task_ids:
            annotations = self.task_annotations.get(task_id, [])
            if len(annotations) < 2:
                continue

            agreement = self.calculate_agreement(task_id)
            all_agreement_scores.append(agreement)

            if agreement >= 0.8:
                tasks_with_agreement += 1
            else:
                tasks_with_disagreement += 1

        # Calculate metric scores
        metric_scores = {}
        for metric in AgreementMetric:
            scores = []
            for task_id in task_ids:
                if len(self.task_annotations.get(task_id, [])) >= 2:
                    scores.append(self.calculate_agreement(task_id, metric))
            if scores:
                metric_scores[metric] = statistics.mean(scores)

        # Calculate annotator reliability
        annotator_reliability = {}
        for annotator_id, stats in self.annotator_stats.items():
            total = stats["total_annotations"]
            if total > 0:
                reliability = stats["agreements"] / total if stats["agreements"] + stats["disagreements"] > 0 else 0.5
                annotator_reliability[annotator_id] = reliability

        # Identify common disagreement patterns
        patterns = self._identify_common_patterns()

        # Generate recommendations
        recommendations = self._generate_report_recommendations(
            all_agreement_scores, patterns
        )

        return AgreementReport(
            project_id=project_id,
            total_tasks=total_tasks,
            tasks_with_agreement=tasks_with_agreement,
            tasks_with_disagreement=tasks_with_disagreement,
            overall_agreement_rate=statistics.mean(all_agreement_scores) if all_agreement_scores else 0.0,
            metric_scores=metric_scores,
            annotator_reliability=annotator_reliability,
            common_disagreement_patterns=patterns,
            recommendations=recommendations
        )

    def _identify_common_patterns(self) -> List[Dict[str, Any]]:
        """Identify common disagreement patterns."""
        patterns = []

        # Group by disagreement type
        type_counts = defaultdict(int)
        for analysis in self.disagreement_history:
            type_counts[analysis.disagreement_type.value] += 1

        for dtype, count in type_counts.items():
            if count >= 3:
                patterns.append({
                    "pattern": f"频繁的{dtype}类型分歧",
                    "count": count,
                    "severity": "high" if dtype == "critical" else "medium"
                })

        return patterns

    def _generate_report_recommendations(
        self,
        agreement_scores: List[float],
        patterns: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on report data."""
        recommendations = []

        if agreement_scores:
            avg_agreement = statistics.mean(agreement_scores)
            if avg_agreement < 0.7:
                recommendations.append("整体一致性较低，建议加强标注员培训")
            elif avg_agreement < 0.85:
                recommendations.append("建议定期进行标注校准会议")

        if patterns:
            recommendations.append("存在重复性分歧模式，建议更新标注指南")

        if not recommendations:
            recommendations.append("标注质量良好，继续保持当前流程")

        return recommendations


# Global instance
advanced_consensus_engine = AdvancedConsensusEngine()
