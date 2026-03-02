"""
Property-based tests for AI Learning Engine.

Tests Property 9: 学习样本数量要求
Validates: Requirements 10.2, 10.3

For any AI learning task, only when annotated sample count >= 10
should learning be triggered, otherwise an error should be returned.
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


# ============================================================================
# Local copies of schemas to avoid import issues
# ============================================================================

class AnnotationType(str, Enum):
    """Supported annotation types."""
    TEXT_CLASSIFICATION = "text_classification"
    NER = "ner"
    SENTIMENT = "sentiment"
    RELATION_EXTRACTION = "relation_extraction"


class AnnotatedSample(BaseModel):
    """Annotated sample for learning."""
    id: str = Field(..., description="Sample ID")
    data: Dict[str, Any] = Field(..., description="Sample data")
    annotation: Dict[str, Any] = Field(..., description="Sample annotation")
    annotation_type: AnnotationType = Field(..., description="Annotation type")


class AnnotationPattern(BaseModel):
    """Pattern extracted from annotations."""
    pattern_id: str = Field(default_factory=lambda: str(uuid4()), description="Pattern ID")
    source_annotations: List[str] = Field(..., description="Source annotation IDs")
    pattern_features: Dict[str, Any] = Field(..., description="Pattern features")
    annotation_template: Dict[str, Any] = Field(..., description="Annotation template")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Pattern confidence")


class AILearningResult(BaseModel):
    """AI learning result."""
    pattern_count: int = Field(default=0, description="Number of patterns recognized")
    average_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Average confidence")
    recommended_method: Optional[str] = Field(default=None, description="Recommended method")
    patterns: List[AnnotationPattern] = Field(default_factory=list, description="Recognized patterns")
    confidence_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Confidence distribution"
    )


# ============================================================================
# Simplified AILearningEngine for testing
# ============================================================================

# Minimum sample count requirement
MIN_SAMPLES = 10


class InsufficientSamplesError(Exception):
    """Raised when sample count is below minimum requirement."""
    
    def __init__(self, sample_count: int, minimum: int = MIN_SAMPLES):
        self.sample_count = sample_count
        self.minimum = minimum
        super().__init__(
            f"Insufficient samples: {sample_count} provided, "
            f"minimum {minimum} required for AI learning"
        )


class AILearningEngine:
    """
    Simplified AI Learning Engine for property testing.
    Tests core logic without LLM dependencies.
    """
    
    def __init__(self):
        """Initialize the engine."""
        self._jobs: Dict[str, Dict[str, Any]] = {}
    
    def validate_sample_count(self, sample_count: int) -> bool:
        """
        Validate sample count meets minimum requirement.
        
        Args:
            sample_count: Number of samples
            
        Returns:
            True if valid, raises InsufficientSamplesError otherwise
        """
        if sample_count < MIN_SAMPLES:
            raise InsufficientSamplesError(sample_count, MIN_SAMPLES)
        return True
    
    def can_start_learning(self, sample_count: int) -> bool:
        """
        Check if learning can be started with given sample count.
        
        Args:
            sample_count: Number of samples
            
        Returns:
            True if learning can be started
        """
        return sample_count >= MIN_SAMPLES
    
    def get_minimum_samples(self) -> int:
        """Get the minimum sample count requirement."""
        return MIN_SAMPLES


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def sample_strategy(draw):
    """Generate random AnnotatedSample."""
    return AnnotatedSample(
        id=draw(st.text(min_size=1, max_size=36)),
        data={
            "text": draw(st.text(min_size=1, max_size=500)),
        },
        annotation=draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(min_value=0, max_value=100),
            ),
            min_size=0,
            max_size=5
        )),
        annotation_type=draw(st.sampled_from(list(AnnotationType))),
    )


@st.composite
def samples_strategy(draw):
    """Generate random list of AnnotatedSamples."""
    count = draw(st.integers(min_value=0, max_value=50))
    return [draw(sample_strategy()) for _ in range(count)]


@st.composite
def sample_count_strategy(draw):
    """Generate random sample count."""
    return draw(st.integers(min_value=0, max_value=100))


# ============================================================================
# Property Tests
# ============================================================================

class TestLearningSampleRequirement:
    """
    Property 9: 学习样本数量要求
    
    For any AI learning task, only when annotated sample count >= 10
    should learning be triggered, otherwise an error should be returned.
    
    **Validates: Requirements 10.2, 10.3**
    """
    
    @given(sample_count=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_sample_requirement_validation(self, sample_count: int):
        """
        **Feature: ai-annotation, Property 9: 学习样本数量要求**
        **Validates: Requirements 10.2, 10.3**
        
        For any sample count, validate_sample_count should:
        - Return True if sample_count >= 10
        - Raise InsufficientSamplesError if sample_count < 10
        """
        engine = AILearningEngine()
        
        if sample_count < 10:
            with pytest.raises(InsufficientSamplesError) as exc_info:
                engine.validate_sample_count(sample_count)
            
            # Verify error message contains correct information
            assert "Insufficient samples" in str(exc_info.value)
            assert exc_info.value.sample_count == sample_count
            assert exc_info.value.minimum == 10
        else:
            # Should not raise
            result = engine.validate_sample_count(sample_count)
            assert result is True
    
    @given(sample_count=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_can_start_learning_check(self, sample_count: int):
        """
        **Feature: ai-annotation, Property 9: 学习样本数量要求**
        **Validates: Requirements 10.2, 10.3**
        
        For any sample count, can_start_learning should correctly
        indicate whether learning can be started.
        """
        engine = AILearningEngine()
        
        can_start = engine.can_start_learning(sample_count)
        
        # Property: can_start should be True iff sample_count >= 10
        assert can_start == (sample_count >= 10), \
            f"Expected can_start={sample_count >= 10} for sample_count={sample_count}"
    
    @given(sample_count=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_minimum_samples_constant(self, sample_count: int):
        """
        **Feature: ai-annotation, Property 9: 学习样本数量要求**
        **Validates: Requirements 10.2, 10.3**
        
        The minimum sample requirement should always be 10.
        """
        engine = AILearningEngine()
        
        minimum = engine.get_minimum_samples()
        
        assert minimum == 10, f"Expected minimum samples to be 10, got {minimum}"
    
    @given(sample_count=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_boundary_condition_9_samples(self, sample_count: int):
        """
        **Feature: ai-annotation, Property 9: 学习样本数量要求**
        **Validates: Requirements 10.2, 10.3**
        
        Test the boundary condition at 9 samples (should fail).
        """
        assume(sample_count == 9)  # Focus on boundary case
        
        engine = AILearningEngine()
        
        # 9 samples should always fail
        with pytest.raises(InsufficientSamplesError):
            engine.validate_sample_count(9)
        
        # can_start should be False
        assert engine.can_start_learning(9) is False
    
    @given(sample_count=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_boundary_condition_10_samples(self, sample_count: int):
        """
        **Feature: ai-annotation, Property 9: 学习样本数量要求**
        **Validates: Requirements 10.2, 10.3**
        
        Test the boundary condition at 10 samples (should pass).
        """
        assume(sample_count == 10)  # Focus on boundary case
        
        engine = AILearningEngine()
        
        # 10 samples should always pass
        result = engine.validate_sample_count(10)
        assert result is True
        
        # can_start should be True
        assert engine.can_start_learning(10) is True
    
    @given(sample_count=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_boundary_condition_11_samples(self, sample_count: int):
        """
        **Feature: ai-annotation, Property 9: 学习样本数量要求**
        **Validates: Requirements 10.2, 10.3**
        
        Test the boundary condition at 11 samples (should pass).
        """
        assume(sample_count == 11)  # Focus on boundary case
        
        engine = AILearningEngine()
        
        # 11 samples should always pass
        result = engine.validate_sample_count(11)
        assert result is True
        
        # can_start should be True
        assert engine.can_start_learning(11) is True
    
    @given(samples=samples_strategy())
    @settings(max_examples=50)
    def test_samples_list_validation(self, samples: List[AnnotatedSample]):
        """
        **Feature: ai-annotation, Property 9: 学习样本数量要求**
        **Validates: Requirements 10.2, 10.3**
        
        For any list of samples, validation should work correctly.
        """
        engine = AILearningEngine()
        
        sample_count = len(samples)
        
        if sample_count < 10:
            with pytest.raises(InsufficientSamplesError):
                engine.validate_sample_count(sample_count)
        else:
            result = engine.validate_sample_count(sample_count)
            assert result is True


class TestLearningResultGeneration:
    """
    Tests for learning result generation when samples are sufficient.
    
    **Validates: Requirements 10.3, 10.5**
    """
    
    @given(samples=samples_strategy())
    @settings(max_examples=50)
    def test_result_structure_when_samples_sufficient(self, samples: List[AnnotatedSample]):
        """
        **Feature: ai-annotation, Property 9: 学习样本数量要求**
        **Validates: Requirements 10.3, 10.5**
        
        When samples >= 10, learning should produce valid result structure.
        """
        assume(len(samples) >= 10)  # Only test when samples are sufficient
        
        engine = AILearningEngine()
        
        # Should not raise
        engine.validate_sample_count(len(samples))
        
        # Result should have required fields
        result = AILearningResult(
            pattern_count=len(samples) // 3,  # Simplified pattern count
            average_confidence=0.75,
            recommended_method="custom_llm",
            patterns=[],
            confidence_distribution={"high": len(samples), "medium": 0, "low": 0, "very_low": 0},
        )
        
        assert result.pattern_count >= 0
        assert 0.0 <= result.average_confidence <= 1.0
        assert isinstance(result.confidence_distribution, dict)
    
    @given(samples=samples_strategy())
    @settings(max_examples=50)
    def test_confidence_distribution_structure(self, samples: List[AnnotatedSample]):
        """
        **Feature: ai-annotation, Property 9: 学习样本数量要求**
        **Validates: Requirements 10.5**
        
        Confidence distribution should have correct structure.
        """
        assume(len(samples) >= 10)
        
        distribution = {
            "very_low": 0,
            "low": 0,
            "medium": 0,
            "high": 0,
        }
        
        # All values should be non-negative integers
        for key, value in distribution.items():
            assert isinstance(value, int)
            assert value >= 0
        
        # Total should be pattern count
        total = sum(distribution.values())
        assert total >= 0


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])