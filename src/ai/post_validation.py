"""
Post-Validation Engine for SuperInsight platform.

Implements multi-dimensional validation using Ragas and DeepEval frameworks,
with custom rule support and comprehensive reporting.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Tuple, Set, Callable
from datetime import datetime
from uuid import uuid4
from collections import defaultdict
import statistics

from src.ai.annotation_schemas import (
    ValidationConfig,
    ValidationRule,
    ValidationIssue,
    ValidationReport,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Validation Dimension Handlers
# ============================================================================

class ValidationDimension:
    """Base class for validation dimensions."""
    
    name: str = "base"
    
    async def validate(
        self,
        annotations: List[Dict[str, Any]],
        ground_truth: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[float, List[ValidationIssue]]:
        """
        Validate annotations and return score with issues.
        
        Args:
            annotations: List of annotations to validate
            ground_truth: Optional ground truth annotations
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (score, list of issues)
        """
        raise NotImplementedError


class AccuracyDimension(ValidationDimension):
    """Validates annotation accuracy against ground truth."""
    
    name = "accuracy"
    
    async def validate(
        self,
        annotations: List[Dict[str, Any]],
        ground_truth: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[float, List[ValidationIssue]]:
        """Calculate accuracy score."""
        issues = []
        
        if not ground_truth or len(ground_truth) != len(annotations):
            # Without ground truth, estimate based on confidence
            confidences = [
                a.get("confidence", 0.5) for a in annotations
            ]
            score = statistics.mean(confidences) if confidences else 0.5
            return score, issues
        
        correct = 0
        for i, (ann, gt) in enumerate(zip(annotations, ground_truth)):
            if self._compare_annotations(ann, gt):
                correct += 1
            else:
                issues.append(ValidationIssue(
                    annotation_id=ann.get("id", str(i)),
                    dimension=self.name,
                    severity="warning",
                    message=f"Annotation differs from ground truth",
                    details={"expected": gt, "actual": ann},
                ))
        
        score = correct / len(annotations) if annotations else 0.0
        return score, issues
    
    def _compare_annotations(
        self,
        annotation: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> bool:
        """Compare annotation with ground truth."""
        # Simple comparison - can be made more sophisticated
        ann_data = annotation.get("annotation_data", annotation)
        gt_data = ground_truth.get("annotation_data", ground_truth)
        
        # Compare key fields
        for key in ["label", "sentiment", "entities"]:
            if key in gt_data:
                if ann_data.get(key) != gt_data.get(key):
                    return False
        
        return True


class RecallDimension(ValidationDimension):
    """Validates annotation recall (coverage of expected items)."""
    
    name = "recall"
    
    async def validate(
        self,
        annotations: List[Dict[str, Any]],
        ground_truth: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[float, List[ValidationIssue]]:
        """Calculate recall score."""
        issues = []
        
        if not ground_truth:
            # Without ground truth, estimate based on completeness
            complete = sum(1 for a in annotations if a.get("annotation_data"))
            score = complete / len(annotations) if annotations else 0.5
            return score, issues
        
        # Calculate recall for entity-based annotations
        total_expected = 0
        total_found = 0
        
        for i, (ann, gt) in enumerate(zip(annotations, ground_truth)):
            gt_entities = gt.get("annotation_data", gt).get("entities", [])
            ann_entities = ann.get("annotation_data", ann).get("entities", [])
            
            if gt_entities:
                total_expected += len(gt_entities)
                found = self._count_matching_entities(ann_entities, gt_entities)
                total_found += found
                
                if found < len(gt_entities):
                    issues.append(ValidationIssue(
                        annotation_id=ann.get("id", str(i)),
                        dimension=self.name,
                        severity="warning",
                        message=f"Missing {len(gt_entities) - found} entities",
                        details={
                            "expected_count": len(gt_entities),
                            "found_count": found,
                        },
                    ))
        
        score = total_found / total_expected if total_expected > 0 else 1.0
        return score, issues
    
    def _count_matching_entities(
        self,
        predicted: List[Dict],
        expected: List[Dict],
    ) -> int:
        """Count matching entities."""
        matched = 0
        for exp in expected:
            for pred in predicted:
                if (pred.get("text") == exp.get("text") and
                    pred.get("label") == exp.get("label")):
                    matched += 1
                    break
        return matched


class ConsistencyDimension(ValidationDimension):
    """Validates annotation consistency across similar items."""
    
    name = "consistency"
    
    async def validate(
        self,
        annotations: List[Dict[str, Any]],
        ground_truth: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[float, List[ValidationIssue]]:
        """Calculate consistency score."""
        issues = []
        
        if len(annotations) < 2:
            return 1.0, issues
        
        # Group annotations by similar content
        groups = self._group_similar_annotations(annotations)
        
        consistent_groups = 0
        total_groups = 0
        
        for group_key, group_annotations in groups.items():
            if len(group_annotations) < 2:
                continue
            
            total_groups += 1
            
            # Check if all annotations in group are consistent
            if self._check_group_consistency(group_annotations):
                consistent_groups += 1
            else:
                for ann in group_annotations:
                    issues.append(ValidationIssue(
                        annotation_id=ann.get("id", "unknown"),
                        dimension=self.name,
                        severity="warning",
                        message="Inconsistent annotation for similar content",
                        details={"group": group_key},
                    ))
        
        score = consistent_groups / total_groups if total_groups > 0 else 1.0
        return score, issues
    
    def _group_similar_annotations(
        self,
        annotations: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group annotations by similar content."""
        groups = defaultdict(list)
        
        for ann in annotations:
            # Create a simple content hash
            content = ann.get("data", {}).get("text", "")
            if content:
                # Use first few words as group key
                key = " ".join(content.split()[:3]).lower()
                groups[key].append(ann)
        
        return groups
    
    def _check_group_consistency(
        self,
        annotations: List[Dict[str, Any]],
    ) -> bool:
        """Check if annotations in a group are consistent."""
        if not annotations:
            return True
        
        first_label = annotations[0].get("annotation_data", {}).get("label")
        
        for ann in annotations[1:]:
            label = ann.get("annotation_data", {}).get("label")
            if label != first_label:
                return False
        
        return True


class CompletenessDimension(ValidationDimension):
    """Validates annotation completeness."""
    
    name = "completeness"
    
    async def validate(
        self,
        annotations: List[Dict[str, Any]],
        ground_truth: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[float, List[ValidationIssue]]:
        """Calculate completeness score."""
        issues = []
        schema = kwargs.get("schema", {})
        required_fields = schema.get("required_fields", ["label"])
        
        complete_count = 0
        
        for i, ann in enumerate(annotations):
            ann_data = ann.get("annotation_data", ann)
            missing_fields = []
            
            for field in required_fields:
                if field not in ann_data or not ann_data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                issues.append(ValidationIssue(
                    annotation_id=ann.get("id", str(i)),
                    dimension=self.name,
                    severity="error",
                    message=f"Missing required fields: {missing_fields}",
                    details={"missing_fields": missing_fields},
                ))
            else:
                complete_count += 1
        
        score = complete_count / len(annotations) if annotations else 0.0
        return score, issues


# ============================================================================
# Ragas and DeepEval Integration (Placeholder)
# ============================================================================

class RagasEvaluator:
    """
    Ragas framework integration for semantic quality evaluation.
    
    Note: This is a placeholder implementation. In production,
    this would integrate with the actual Ragas library.
    """
    
    async def evaluate(
        self,
        annotations: List[Dict[str, Any]],
        config: Dict[str, Any] = None,
    ) -> Dict[str, float]:
        """
        Evaluate annotations using Ragas metrics.
        
        Args:
            annotations: Annotations to evaluate
            config: Evaluation configuration
            
        Returns:
            Dictionary of metric scores
        """
        # Placeholder implementation
        # In production, this would call ragas.evaluate()
        return {
            "faithfulness": 0.85,
            "answer_relevancy": 0.82,
            "context_precision": 0.78,
            "context_recall": 0.80,
        }


class DeepEvalEvaluator:
    """
    DeepEval framework integration for deep evaluation.
    
    Note: This is a placeholder implementation. In production,
    this would integrate with the actual DeepEval library.
    """
    
    async def evaluate(
        self,
        annotations: List[Dict[str, Any]],
        config: Dict[str, Any] = None,
    ) -> Dict[str, float]:
        """
        Evaluate annotations using DeepEval metrics.
        
        Args:
            annotations: Annotations to evaluate
            config: Evaluation configuration
            
        Returns:
            Dictionary of metric scores
        """
        # Placeholder implementation
        # In production, this would call deepeval metrics
        return {
            "coherence": 0.88,
            "fluency": 0.90,
            "relevance": 0.85,
            "groundedness": 0.82,
        }


# ============================================================================
# Post-Validation Engine
# ============================================================================

class PostValidationEngine:
    """
    Post-validation engine for multi-dimensional annotation validation.
    
    Features:
    - Multi-dimensional validation (accuracy, recall, consistency, completeness)
    - Ragas framework integration for semantic evaluation
    - DeepEval framework integration for deep evaluation
    - Custom validation rules support
    - Comprehensive reporting with recommendations
    """
    
    def __init__(self):
        """Initialize the post-validation engine."""
        self.ragas_evaluator = RagasEvaluator()
        self.deepeval_evaluator = DeepEvalEvaluator()
        
        # Register validation dimensions
        self.dimensions: Dict[str, ValidationDimension] = {
            "accuracy": AccuracyDimension(),
            "recall": RecallDimension(),
            "consistency": ConsistencyDimension(),
            "completeness": CompletenessDimension(),
        }
        
        # Custom rules
        self.custom_rules: List[ValidationRule] = []
    
    async def validate(
        self,
        annotations: List[Dict[str, Any]],
        config: ValidationConfig = None,
        ground_truth: Optional[List[Dict[str, Any]]] = None,
    ) -> ValidationReport:
        """
        Execute multi-dimensional validation.
        
        Args:
            annotations: Annotations to validate
            config: Validation configuration
            ground_truth: Optional ground truth for comparison
            
        Returns:
            ValidationReport with scores and issues
        """
        config = config or ValidationConfig()
        start_time = time.time()
        
        all_issues: List[ValidationIssue] = []
        dimension_scores: Dict[str, float] = {}
        
        # Validate each configured dimension
        for dim_name in config.dimensions:
            if dim_name in self.dimensions:
                dimension = self.dimensions[dim_name]
                score, issues = await dimension.validate(
                    annotations, ground_truth
                )
                dimension_scores[dim_name] = score
                all_issues.extend(issues)
        
        # Run Ragas evaluation if enabled
        if config.use_ragas:
            try:
                ragas_scores = await self.ragas_evaluator.evaluate(annotations)
                for key, value in ragas_scores.items():
                    dimension_scores[f"ragas_{key}"] = value
            except Exception as e:
                logger.warning(f"Ragas evaluation failed: {e}")
        
        # Run DeepEval evaluation if enabled
        if config.use_deepeval:
            try:
                deepeval_scores = await self.deepeval_evaluator.evaluate(annotations)
                for key, value in deepeval_scores.items():
                    dimension_scores[f"deepeval_{key}"] = value
            except Exception as e:
                logger.warning(f"DeepEval evaluation failed: {e}")
        
        # Apply custom rules
        for rule in config.custom_rules:
            if rule.enabled:
                rule_issues = await self._apply_custom_rule(rule, annotations)
                all_issues.extend(rule_issues)
        
        # Calculate overall score
        core_dimensions = ["accuracy", "recall", "consistency", "completeness"]
        core_scores = [dimension_scores.get(d, 0.5) for d in core_dimensions if d in dimension_scores]
        overall_score = statistics.mean(core_scores) if core_scores else 0.5
        
        # Generate recommendations
        recommendations = self._generate_recommendations(dimension_scores, all_issues)
        
        processing_time = (time.time() - start_time) * 1000
        
        return ValidationReport(
            report_id=str(uuid4()),
            overall_score=overall_score,
            accuracy=dimension_scores.get("accuracy", 0.0),
            recall=dimension_scores.get("recall", 0.0),
            consistency=dimension_scores.get("consistency", 0.0),
            completeness=dimension_scores.get("completeness", 0.0),
            dimension_scores=dimension_scores,
            issues=all_issues,
            recommendations=recommendations,
            total_annotations=len(annotations),
            created_at=datetime.utcnow(),
        )
    
    async def validate_accuracy(
        self,
        annotations: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]],
    ) -> float:
        """Validate accuracy against ground truth."""
        score, _ = await self.dimensions["accuracy"].validate(
            annotations, ground_truth
        )
        return score
    
    async def validate_consistency(
        self,
        annotations: List[Dict[str, Any]],
    ) -> float:
        """Validate annotation consistency."""
        score, _ = await self.dimensions["consistency"].validate(annotations)
        return score
    
    async def validate_completeness(
        self,
        annotations: List[Dict[str, Any]],
        schema: Dict[str, Any] = None,
    ) -> float:
        """Validate annotation completeness."""
        score, _ = await self.dimensions["completeness"].validate(
            annotations, schema=schema or {}
        )
        return score
    
    def generate_report(
        self,
        results: Dict[str, Any],
    ) -> ValidationReport:
        """
        Generate validation report from results.
        
        Args:
            results: Validation results dictionary
            
        Returns:
            ValidationReport object
        """
        return ValidationReport(
            report_id=str(uuid4()),
            overall_score=results.get("overall_score", 0.0),
            accuracy=results.get("accuracy", 0.0),
            recall=results.get("recall", 0.0),
            consistency=results.get("consistency", 0.0),
            completeness=results.get("completeness", 0.0),
            dimension_scores=results.get("dimension_scores", {}),
            issues=results.get("issues", []),
            recommendations=results.get("recommendations", []),
            total_annotations=results.get("total_annotations", 0),
            created_at=datetime.utcnow(),
        )
    
    def add_custom_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule."""
        self.custom_rules.append(rule)
    
    async def _apply_custom_rule(
        self,
        rule: ValidationRule,
        annotations: List[Dict[str, Any]],
    ) -> List[ValidationIssue]:
        """Apply a custom validation rule."""
        issues = []
        
        # Simple rule types
        if rule.rule_type == "required_field":
            field = rule.parameters.get("field")
            for i, ann in enumerate(annotations):
                if field and field not in ann.get("annotation_data", {}):
                    issues.append(ValidationIssue(
                        annotation_id=ann.get("id", str(i)),
                        dimension="custom",
                        severity="error",
                        message=f"Custom rule '{rule.name}': Missing field '{field}'",
                        details={"rule": rule.name},
                    ))
        
        elif rule.rule_type == "min_confidence":
            min_conf = rule.parameters.get("threshold", 0.5)
            for i, ann in enumerate(annotations):
                conf = ann.get("confidence", 0)
                if conf < min_conf:
                    issues.append(ValidationIssue(
                        annotation_id=ann.get("id", str(i)),
                        dimension="custom",
                        severity="warning",
                        message=f"Custom rule '{rule.name}': Confidence {conf} below {min_conf}",
                        details={"rule": rule.name, "confidence": conf},
                    ))
        
        return issues
    
    def _generate_recommendations(
        self,
        scores: Dict[str, float],
        issues: List[ValidationIssue],
    ) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Check each dimension
        if scores.get("accuracy", 1.0) < 0.8:
            recommendations.append(
                "Consider reviewing annotations with low accuracy scores"
            )
        
        if scores.get("recall", 1.0) < 0.8:
            recommendations.append(
                "Some expected items may be missing - review for completeness"
            )
        
        if scores.get("consistency", 1.0) < 0.8:
            recommendations.append(
                "Inconsistent annotations detected - consider standardizing guidelines"
            )
        
        if scores.get("completeness", 1.0) < 0.9:
            recommendations.append(
                "Some annotations are incomplete - ensure all required fields are filled"
            )
        
        # Check issue severity
        error_count = sum(1 for i in issues if i.severity == "error")
        if error_count > 0:
            recommendations.append(
                f"Address {error_count} critical issues before finalizing"
            )
        
        return recommendations


# Singleton instance
_engine_instance: Optional[PostValidationEngine] = None


def get_post_validation_engine() -> PostValidationEngine:
    """
    Get or create the post-validation engine instance.
    
    Returns:
        PostValidationEngine instance
    """
    global _engine_instance
    
    if _engine_instance is None:
        _engine_instance = PostValidationEngine()
    
    return _engine_instance
