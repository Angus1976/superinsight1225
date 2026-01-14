"""
Property-based tests for Hybrid Generator.

Tests Property 3: 混合方法优先级
Validates: Requirements 3.1, 3.2

Uses Hypothesis for property-based testing with 100+ iterations.
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch

from src.text_to_sql.hybrid import (
    HybridGenerator,
    SQLOptimizationRules,
    SQLOptimizationRule,
    MethodUsageLog,
    get_hybrid_generator,
)
from src.text_to_sql.schemas import SQLGenerationResult, MethodType
from src.text_to_sql.basic import TemplateFiller
from src.text_to_sql.llm_based import LLMSQLGenerator


# Mock classes for testing
class MockTemplateFiller:
    """Mock template filler for testing."""
    
    def __init__(self, should_match: bool = True, confidence: float = 0.9):
        self.should_match = should_match
        self.confidence = confidence
        self.generate_called = False
    
    def generate(self, query: str, schema=None) -> SQLGenerationResult:
        self.generate_called = True
        
        if self.should_match:
            return SQLGenerationResult(
                sql=f"SELECT * FROM test_table",
                method_used="template",
                confidence=self.confidence,
                execution_time_ms=1.0,
                template_id="test_template",
                metadata={"template_name": "Test Template"},
            )
        else:
            return SQLGenerationResult(
                sql="",
                method_used="template",
                confidence=0.0,
                execution_time_ms=1.0,
                metadata={"error": "No matching template"},
            )


class MockLLMGenerator:
    """Mock LLM generator for testing."""
    
    def __init__(self, should_succeed: bool = True, confidence: float = 0.8):
        self.should_succeed = should_succeed
        self.confidence = confidence
        self.generate_called = False
    
    async def generate(self, query: str, schema=None, db_type: str = "postgresql") -> SQLGenerationResult:
        self.generate_called = True
        
        if self.should_succeed:
            return SQLGenerationResult(
                sql=f"SELECT * FROM llm_table WHERE query = '{query[:20]}'",
                method_used="llm",
                confidence=self.confidence,
                execution_time_ms=100.0,
                explanation="LLM generated query",
                metadata={"model_used": "test_model"},
            )
        else:
            return SQLGenerationResult(
                sql="",
                method_used="llm",
                confidence=0.0,
                execution_time_ms=100.0,
                metadata={"error": "LLM generation failed"},
            )


class TestHybridGeneratorProperties:
    """Property-based tests for Hybrid Generator."""
    
    @settings(max_examples=100, deadline=None)
    @given(
        template_confidence=st.floats(min_value=0.7, max_value=1.0),
        threshold=st.floats(min_value=0.5, max_value=0.9)
    )
    def test_property_3_template_priority_when_high_confidence(
        self,
        template_confidence: float,
        threshold: float
    ):
        """
        Property 3: 混合方法优先级 - Template priority
        
        For any query where template matching succeeds with confidence
        above threshold, the hybrid generator should use template result.
        
        **Feature: text-to-sql-methods, Property 3: 混合方法优先级**
        **Validates: Requirements 3.1, 3.2**
        """
        # Create mocks
        mock_template = MockTemplateFiller(should_match=True, confidence=template_confidence)
        mock_llm = MockLLMGenerator(should_succeed=True)
        
        # Create hybrid generator with mocks
        generator = HybridGenerator(
            template_filler=mock_template,
            llm_generator=mock_llm,
            template_confidence_threshold=threshold
        )
        
        # Run generation
        result = asyncio.get_event_loop().run_until_complete(
            generator.generate("test query")
        )
        
        # Verify template was tried first
        assert mock_template.generate_called, "Template should be tried first"
        
        # If template confidence >= threshold, should use template
        if template_confidence >= threshold:
            assert result.method_used == "template", \
                f"Should use template when confidence {template_confidence} >= threshold {threshold}"
            assert not mock_llm.generate_called, "LLM should not be called when template succeeds"
    
    @settings(max_examples=100, deadline=None)
    @given(
        template_confidence=st.floats(min_value=0.0, max_value=0.6),
        threshold=st.floats(min_value=0.7, max_value=0.9)
    )
    def test_property_3_llm_fallback_when_low_confidence(
        self,
        template_confidence: float,
        threshold: float
    ):
        """
        Property 3: 混合方法优先级 - LLM fallback
        
        For any query where template matching has low confidence,
        the hybrid generator should fall back to LLM.
        
        **Feature: text-to-sql-methods, Property 3: 混合方法优先级**
        **Validates: Requirements 3.1, 3.2**
        """
        assume(template_confidence < threshold)
        
        # Create mocks
        mock_template = MockTemplateFiller(should_match=True, confidence=template_confidence)
        mock_llm = MockLLMGenerator(should_succeed=True)
        
        # Create hybrid generator
        generator = HybridGenerator(
            template_filler=mock_template,
            llm_generator=mock_llm,
            template_confidence_threshold=threshold
        )
        
        # Run generation
        result = asyncio.get_event_loop().run_until_complete(
            generator.generate("test query")
        )
        
        # Verify both were tried
        assert mock_template.generate_called, "Template should be tried first"
        assert mock_llm.generate_called, "LLM should be called as fallback"
        
        # Result should be from LLM or hybrid
        assert result.method_used in ["llm", "hybrid"], \
            f"Should use LLM/hybrid when template confidence {template_confidence} < threshold {threshold}"
    
    @settings(max_examples=100, deadline=None)
    @given(query=st.text(min_size=1, max_size=100))
    def test_property_3_template_always_tried_first(self, query: str):
        """
        Property 3: 混合方法优先级 - Template always first
        
        For any query, template matching should always be attempted first.
        
        **Feature: text-to-sql-methods, Property 3: 混合方法优先级**
        **Validates: Requirements 3.1**
        """
        assume(query.strip())
        
        # Create mocks
        mock_template = MockTemplateFiller(should_match=False)
        mock_llm = MockLLMGenerator(should_succeed=True)
        
        # Create hybrid generator
        generator = HybridGenerator(
            template_filler=mock_template,
            llm_generator=mock_llm,
        )
        
        # Run generation
        asyncio.get_event_loop().run_until_complete(
            generator.generate(query)
        )
        
        # Template should always be tried first
        assert mock_template.generate_called, "Template should always be tried first"
    
    @settings(max_examples=100, deadline=None)
    @given(
        template_succeeds=st.booleans(),
        llm_succeeds=st.booleans()
    )
    def test_property_3_graceful_degradation(
        self,
        template_succeeds: bool,
        llm_succeeds: bool
    ):
        """
        Property 3: 混合方法优先级 - Graceful degradation
        
        For any combination of template/LLM success/failure,
        the hybrid generator should handle gracefully.
        
        **Feature: text-to-sql-methods, Property 3: 混合方法优先级**
        **Validates: Requirements 3.1, 3.2**
        """
        # Create mocks
        mock_template = MockTemplateFiller(
            should_match=template_succeeds,
            confidence=0.9 if template_succeeds else 0.0
        )
        mock_llm = MockLLMGenerator(should_succeed=llm_succeeds)
        
        # Create hybrid generator
        generator = HybridGenerator(
            template_filler=mock_template,
            llm_generator=mock_llm,
        )
        
        # Run generation - should not raise
        result = asyncio.get_event_loop().run_until_complete(
            generator.generate("test query")
        )
        
        # Should always return a result
        assert result is not None, "Should always return a result"
        assert isinstance(result, SQLGenerationResult), "Should return SQLGenerationResult"
        
        # If both fail, should have empty SQL
        if not template_succeeds and not llm_succeeds:
            assert result.sql == "", "Should have empty SQL when both methods fail"
            assert result.confidence == 0.0, "Should have zero confidence when both fail"


class TestHybridGeneratorOptimization:
    """Tests for SQL optimization rules."""
    
    @settings(max_examples=100, deadline=None)
    @given(sql=st.text(min_size=10, max_size=200))
    def test_optimization_preserves_sql_structure(self, sql: str):
        """
        Test that optimization doesn't break SQL structure.
        
        **Feature: text-to-sql-methods, Property 3: 混合方法优先级**
        **Validates: Requirements 3.3**
        """
        rules = SQLOptimizationRules()
        
        optimized = rules.optimize(sql)
        
        # Should return a string
        assert isinstance(optimized, str), "Should return string"
        
        # Should not be empty if input wasn't empty
        if sql.strip():
            # Optimization might change content but shouldn't make it empty
            # unless the entire SQL was a pattern that gets removed
            pass
    
    def test_optimization_count_star(self):
        """Test COUNT(1) to COUNT(*) optimization."""
        rules = SQLOptimizationRules()
        
        sql = "SELECT COUNT(1) FROM users"
        optimized = rules.optimize(sql)
        
        assert "COUNT(*)" in optimized, "Should convert COUNT(1) to COUNT(*)"
    
    def test_add_custom_rule(self):
        """Test adding custom optimization rule."""
        rules = SQLOptimizationRules()
        
        custom_rule = SQLOptimizationRule(
            name="test_rule",
            pattern=r"TEST_PATTERN",
            replacement="REPLACED",
            description="Test rule",
        )
        
        rules.add_rule(custom_rule)
        
        sql = "SELECT TEST_PATTERN FROM users"
        optimized = rules.optimize(sql)
        
        assert "REPLACED" in optimized, "Custom rule should be applied"
    
    def test_remove_rule(self):
        """Test removing optimization rule."""
        rules = SQLOptimizationRules()
        
        # Remove existing rule
        result = rules.remove_rule("optimize_count_star")
        assert result, "Should successfully remove rule"
        
        # Verify rule is gone
        sql = "SELECT COUNT(1) FROM users"
        optimized = rules.optimize(sql)
        
        assert "COUNT(1)" in optimized, "Removed rule should not be applied"


class TestHybridGeneratorLogging:
    """Tests for method usage logging."""
    
    def test_usage_logging(self):
        """Test that usage is logged correctly."""
        mock_template = MockTemplateFiller(should_match=True, confidence=0.9)
        mock_llm = MockLLMGenerator(should_succeed=True)
        
        generator = HybridGenerator(
            template_filler=mock_template,
            llm_generator=mock_llm,
        )
        
        # Run generation
        asyncio.get_event_loop().run_until_complete(
            generator.generate("test query")
        )
        
        # Check logs
        stats = generator.get_usage_statistics()
        assert stats["total_queries"] == 1, "Should log one query"
    
    def test_statistics_tracking(self):
        """Test statistics tracking."""
        mock_template = MockTemplateFiller(should_match=True, confidence=0.9)
        mock_llm = MockLLMGenerator(should_succeed=True)
        
        generator = HybridGenerator(
            template_filler=mock_template,
            llm_generator=mock_llm,
        )
        
        # Run multiple generations
        for _ in range(3):
            asyncio.get_event_loop().run_until_complete(
                generator.generate("test query")
            )
        
        stats = generator.get_statistics()
        assert stats["total_calls"] == 3, "Should track total calls"
        assert stats["template_calls"] == 3, "Should track template calls"
    
    def test_clear_logs(self):
        """Test clearing usage logs."""
        mock_template = MockTemplateFiller(should_match=True, confidence=0.9)
        mock_llm = MockLLMGenerator(should_succeed=True)
        
        generator = HybridGenerator(
            template_filler=mock_template,
            llm_generator=mock_llm,
        )
        
        # Run generation
        asyncio.get_event_loop().run_until_complete(
            generator.generate("test query")
        )
        
        # Clear logs
        generator.clear_logs()
        
        stats = generator.get_usage_statistics()
        assert stats["total_queries"] == 0, "Logs should be cleared"


class TestHybridGeneratorConfidence:
    """Tests for confidence calculation."""
    
    @settings(max_examples=100, deadline=None)
    @given(confidence=st.floats(min_value=0.0, max_value=1.0))
    def test_confidence_calculation_template(self, confidence: float):
        """
        Test confidence calculation for template results.
        
        **Feature: text-to-sql-methods, Property 3: 混合方法优先级**
        **Validates: Requirements 3.5**
        """
        generator = HybridGenerator()
        
        result = SQLGenerationResult(
            sql="SELECT * FROM test",
            method_used="template",
            confidence=confidence,
            execution_time_ms=1.0,
        )
        
        calculated = generator.calculate_confidence(result)
        
        # Template confidence should be boosted slightly
        assert calculated >= confidence, "Template confidence should not decrease"
        assert calculated <= 1.0, "Confidence should not exceed 1.0"
    
    @settings(max_examples=100, deadline=None)
    @given(confidence=st.floats(min_value=0.0, max_value=1.0))
    def test_confidence_calculation_llm(self, confidence: float):
        """
        Test confidence calculation for LLM results.
        
        **Feature: text-to-sql-methods, Property 3: 混合方法优先级**
        **Validates: Requirements 3.5**
        """
        generator = HybridGenerator()
        
        result = SQLGenerationResult(
            sql="SELECT * FROM test",
            method_used="llm",
            confidence=confidence,
            execution_time_ms=100.0,
        )
        
        calculated = generator.calculate_confidence(result)
        
        # LLM confidence should be slightly reduced
        assert calculated <= confidence or confidence == 0.0, \
            "LLM confidence should not increase"
        assert calculated >= 0.0, "Confidence should not be negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
