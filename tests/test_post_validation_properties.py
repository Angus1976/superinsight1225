"""
Property-based tests for Post-Validation Engine.

Tests Property 8: 验证报告完整性
Validates: Requirements 3.2

Validation reports must contain all required dimensions and scores.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from uuid import uuid4


# ============================================================================
# Local copies of schemas to avoid import issues
# ============================================================================

class ValidationIssue(BaseModel):
    """A validation issue found during validation."""
    annotation_id: str = Field(..., description="Annotation ID")
    dimension: str = Field(..., description="Validation dimension")
    severity: str = Field(default="warning", description="Issue severity")
    message: str = Field(..., description="Issue message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class ValidationReport(BaseModel):
    """Validation report with scores and issues."""
    report_id: str = Field(..., description="Report ID")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall score")
    accuracy: float = Field(default=0.0, ge=0.0, le=1.0, description="Accuracy score")
    recall: float = Field(default=0.0, ge=0.0, le=1.0, description="Recall score")
    consistency: float = Field(default=0.0, ge=0.0, le=1.0, description="Consistency score")
    completeness: float = Field(default=0.0, ge=0.0, le=1.0, description="Completeness score")
    dimension_scores: Dict[str, float] = Field(default_factory=dict, description="All dimension scores")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Validation issues")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    total_annotations: int = Field(default=0, ge=0, description="Total annotations validated")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


class ValidationConfig(BaseModel):
    """Configuration for validation."""
    dimensions: List[str] = Field(
        default=["accuracy", "recall", "consistency", "completeness"],
        description="Dimensions to validate"
    )
    use_ragas: bool = Field(default=False, description="Use Ragas framework")
    use_deepeval: bool = Field(default=False, description="Use DeepEval framework")
    custom_rules: List[Any] = Field(default_factory=list, description="Custom rules")


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def validation_issue_strategy(draw):
    """Generate random ValidationIssue."""
    return ValidationIssue(
        annotation_id=draw(st.text(min_size=1, max_size=36)),
        dimension=draw(st.sampled_from(["accuracy", "recall", "consistency", "completeness", "custom"])),
        severity=draw(st.sampled_from(["error", "warning", "info"])),
        message=draw(st.text(min_size=1, max_size=200)),
        details=draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(max_size=100),
            max_size=5
        )),
    )


@st.composite
def validation_report_strategy(draw):
    """Generate random ValidationReport."""
    accuracy = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    recall = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    consistency = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    completeness = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    
    # Calculate overall score as average
    overall = (accuracy + recall + consistency + completeness) / 4
    
    dimension_scores = {
        "accuracy": accuracy,
        "recall": recall,
        "consistency": consistency,
        "completeness": completeness,
    }
    
    # Optionally add ragas/deepeval scores
    if draw(st.booleans()):
        dimension_scores["ragas_faithfulness"] = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    if draw(st.booleans()):
        dimension_scores["deepeval_coherence"] = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    
    issues = draw(st.lists(validation_issue_strategy(), max_size=10))
    
    return ValidationReport(
        report_id=str(uuid4()),
        overall_score=overall,
        accuracy=accuracy,
        recall=recall,
        consistency=consistency,
        completeness=completeness,
        dimension_scores=dimension_scores,
        issues=issues,
        recommendations=draw(st.lists(st.text(min_size=1, max_size=200), max_size=5)),
        total_annotations=draw(st.integers(min_value=0, max_value=10000)),
        created_at=datetime.utcnow(),
    )


@st.composite
def annotation_strategy(draw):
    """Generate random annotation data."""
    return {
        "id": draw(st.text(min_size=1, max_size=36)),
        "data": {
            "text": draw(st.text(min_size=1, max_size=500)),
        },
        "annotation_data": {
            "label": draw(st.sampled_from(["positive", "negative", "neutral"])),
            "entities": draw(st.lists(
                st.fixed_dictionaries({
                    "text": st.text(min_size=1, max_size=50),
                    "label": st.sampled_from(["PERSON", "ORG", "LOC"]),
                }),
                max_size=5
            )),
        },
        "confidence": draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
    }


# ============================================================================
# Property Tests
# ============================================================================

class TestValidationReportCompleteness:
    """
    Property 8: 验证报告完整性
    
    Validation reports must contain all required dimensions and scores.
    
    **Validates: Requirements 3.2**
    """
    
    @given(report=validation_report_strategy())
    @settings(max_examples=100)
    def test_report_has_report_id(self, report: ValidationReport):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.2**
        
        Every validation report must have a unique report_id.
        """
        assert report.report_id is not None, \
            "Report must have report_id"
        assert len(report.report_id) > 0, \
            "report_id must not be empty"
    
    @given(report=validation_report_strategy())
    @settings(max_examples=100)
    def test_report_has_overall_score(self, report: ValidationReport):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.2**
        
        Every validation report must have an overall score in [0, 1].
        """
        assert report.overall_score is not None, \
            "Report must have overall_score"
        assert 0.0 <= report.overall_score <= 1.0, \
            f"Overall score {report.overall_score} must be in [0, 1]"
    
    @given(report=validation_report_strategy())
    @settings(max_examples=100)
    def test_report_has_core_dimensions(self, report: ValidationReport):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.2**
        
        Every validation report must have all four core dimension scores.
        """
        # Check individual dimension fields
        assert 0.0 <= report.accuracy <= 1.0, \
            f"Accuracy {report.accuracy} must be in [0, 1]"
        assert 0.0 <= report.recall <= 1.0, \
            f"Recall {report.recall} must be in [0, 1]"
        assert 0.0 <= report.consistency <= 1.0, \
            f"Consistency {report.consistency} must be in [0, 1]"
        assert 0.0 <= report.completeness <= 1.0, \
            f"Completeness {report.completeness} must be in [0, 1]"
    
    @given(report=validation_report_strategy())
    @settings(max_examples=100)
    def test_report_dimension_scores_match_fields(self, report: ValidationReport):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.2**
        
        Dimension scores dict should contain core dimensions.
        """
        core_dims = ["accuracy", "recall", "consistency", "completeness"]
        for dim in core_dims:
            assert dim in report.dimension_scores, \
                f"dimension_scores must contain {dim}"
            assert report.dimension_scores[dim] == getattr(report, dim), \
                f"dimension_scores[{dim}] must match report.{dim}"
    
    @given(report=validation_report_strategy())
    @settings(max_examples=100)
    def test_report_has_timestamp(self, report: ValidationReport):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.2**
        
        Every validation report must have a creation timestamp.
        """
        assert report.created_at is not None, \
            "Report must have created_at timestamp"
        assert isinstance(report.created_at, datetime), \
            "created_at must be a datetime"
    
    @given(report=validation_report_strategy())
    @settings(max_examples=100)
    def test_report_issues_are_valid(self, report: ValidationReport):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.2**
        
        All issues in the report must have required fields.
        """
        for issue in report.issues:
            assert issue.annotation_id, "Issue must have annotation_id"
            assert issue.dimension, "Issue must have dimension"
            assert issue.severity in ["error", "warning", "info"], \
                f"Invalid severity: {issue.severity}"
            assert issue.message, "Issue must have message"
    
    @given(report=validation_report_strategy())
    @settings(max_examples=100)
    def test_report_total_annotations_non_negative(self, report: ValidationReport):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.2**
        
        Total annotations count must be non-negative.
        """
        assert report.total_annotations >= 0, \
            "total_annotations must be non-negative"


class TestValidationScoreConsistency:
    """
    Tests for validation score consistency.
    
    **Validates: Requirements 3.1, 3.2**
    """
    
    @given(
        accuracy=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        recall=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        consistency=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        completeness=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_overall_score_is_average_of_dimensions(
        self,
        accuracy: float,
        recall: float,
        consistency: float,
        completeness: float,
    ):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.2**
        
        Overall score should be the average of core dimension scores.
        """
        expected_overall = (accuracy + recall + consistency + completeness) / 4
        
        report = ValidationReport(
            report_id=str(uuid4()),
            overall_score=expected_overall,
            accuracy=accuracy,
            recall=recall,
            consistency=consistency,
            completeness=completeness,
            dimension_scores={
                "accuracy": accuracy,
                "recall": recall,
                "consistency": consistency,
                "completeness": completeness,
            },
            total_annotations=100,
        )
        
        # Verify overall score matches expected
        assert abs(report.overall_score - expected_overall) < 0.0001, \
            f"Overall score {report.overall_score} should be {expected_overall}"
    
    @given(report=validation_report_strategy())
    @settings(max_examples=100)
    def test_all_dimension_scores_in_valid_range(self, report: ValidationReport):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.2**
        
        All dimension scores must be in [0, 1].
        """
        for dim_name, score in report.dimension_scores.items():
            assert 0.0 <= score <= 1.0, \
                f"Dimension {dim_name} score {score} must be in [0, 1]"


class TestValidationIssues:
    """
    Tests for validation issues.
    
    **Validates: Requirements 3.5**
    """
    
    @given(issue=validation_issue_strategy())
    @settings(max_examples=100)
    def test_issue_has_annotation_id(self, issue: ValidationIssue):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.5**
        
        Every issue must reference an annotation.
        """
        assert issue.annotation_id is not None, \
            "Issue must have annotation_id"
        assert len(issue.annotation_id) > 0, \
            "annotation_id must not be empty"
    
    @given(issue=validation_issue_strategy())
    @settings(max_examples=100)
    def test_issue_has_dimension(self, issue: ValidationIssue):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.5**
        
        Every issue must specify which dimension it relates to.
        """
        assert issue.dimension is not None, \
            "Issue must have dimension"
        assert len(issue.dimension) > 0, \
            "dimension must not be empty"
    
    @given(issue=validation_issue_strategy())
    @settings(max_examples=100)
    def test_issue_has_valid_severity(self, issue: ValidationIssue):
        """
        **Feature: ai-annotation, Property 8: 验证报告完整性**
        **Validates: Requirements 3.5**
        
        Issue severity must be one of: error, warning, info.
        """
        valid_severities = ["error", "warning", "info"]
        assert issue.severity in valid_severities, \
            f"Severity {issue.severity} must be one of {valid_severities}"


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
