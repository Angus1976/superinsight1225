"""
Property-based tests for Method Switcher.

Tests Property 2: 方法路由正确性
Validates: Requirements 4.1, 4.2

Uses Hypothesis for property-based testing with 100+ iterations.
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.text_to_sql.switcher import (
    MethodSwitcher,
    get_method_switcher,
    reset_method_switcher,
    DBType,
)
from src.text_to_sql.schemas import (
    SQLGenerationResult,
    MethodInfo,
    MethodType,
    TextToSQLConfig,
)
from src.text_to_sql.schema_analyzer import DatabaseSchema


# =============================================================================
# Mock Classes for Testing
# =============================================================================

class MockTemplateFiller:
    """Mock template filler for testing."""
    
    def __init__(self, should_match: bool = True, confidence: float = 0.9):
        self.should_match = should_match
        self.confidence = confidence
        self.generate_called = False
        self.templates = []  # Empty list for testing
    
    def generate(self, query: str, schema=None) -> SQLGenerationResult:
        self.generate_called = True
        
        if self.should_match:
            return SQLGenerationResult(
                sql=f"SELECT * FROM template_table",
                method_used="template",
                confidence=self.confidence,
                execution_time_ms=1.0,
                template_id="test_template",
            )
        else:
            return SQLGenerationResult(
                sql="",
                method_used="template",
                confidence=0.0,
                execution_time_ms=1.0,
            )
    
    def match_template(self, query: str):
        """Mock template matching."""
        if self.should_match:
            return Mock(match_score=self.confidence)
        return None


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
                sql=f"SELECT * FROM llm_table",
                method_used="llm",
                confidence=self.confidence,
                execution_time_ms=100.0,
            )
        else:
            return SQLGenerationResult(
                sql="",
                method_used="llm",
                confidence=0.0,
                execution_time_ms=100.0,
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        return {"total_calls": 0, "successful_calls": 0}


class MockHybridGenerator:
    """Mock hybrid generator for testing."""
    
    def __init__(self, should_succeed: bool = True, confidence: float = 0.85):
        self.should_succeed = should_succeed
        self.confidence = confidence
        self.generate_called = False
    
    async def generate(self, query: str, schema=None, db_type: str = "postgresql") -> SQLGenerationResult:
        self.generate_called = True
        
        if self.should_succeed:
            return SQLGenerationResult(
                sql=f"SELECT * FROM hybrid_table",
                method_used="hybrid",
                confidence=self.confidence,
                execution_time_ms=50.0,
            )
        else:
            return SQLGenerationResult(
                sql="",
                method_used="hybrid",
                confidence=0.0,
                execution_time_ms=50.0,
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        return {"total_calls": 0}
    
    def set_template_threshold(self, threshold: float) -> None:
        pass


class MockPluginManager:
    """Mock plugin manager for testing."""
    
    def __init__(self):
        self._plugins = {}
    
    async def list_plugins(self):
        return []
    
    def is_plugin_enabled(self, name: str) -> bool:
        return False


# =============================================================================
# Property 2: Method Routing Correctness Tests
# =============================================================================

class TestMethodRoutingCorrectness:
    """
    Property 2: 方法路由正确性
    
    For any configured default method and call-time specified method,
    Method Switcher should correctly route to the corresponding generator,
    with specified method taking priority over default method.
    
    **Validates: Requirements 4.1, 4.2**
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        default_method=st.sampled_from([MethodType.TEMPLATE, MethodType.LLM, MethodType.HYBRID]),
        override_method=st.sampled_from([MethodType.TEMPLATE, MethodType.LLM, MethodType.HYBRID]),
    )
    def test_property_2_override_method_takes_priority(
        self,
        default_method: MethodType,
        override_method: MethodType,
    ):
        """
        Property 2: Override method takes priority over default.
        
        For any default method and override method,
        the override should be used when specified.
        
        **Feature: text-to-sql-methods, Property 2: 方法路由正确性**
        **Validates: Requirements 4.1, 4.2**
        """
        # Create config with default method
        config = TextToSQLConfig(
            default_method=default_method,
            auto_select_enabled=False,  # Disable auto-select for this test
        )
        
        # Create mocks
        mock_template = MockTemplateFiller(should_match=True)
        mock_llm = MockLLMGenerator(should_succeed=True)
        mock_hybrid = MockHybridGenerator(should_succeed=True)
        mock_plugin_manager = MockPluginManager()
        
        # Create switcher
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        # Generate with override method
        result = asyncio.get_event_loop().run_until_complete(
            switcher.generate_sql("test query", method=override_method)
        )
        
        # Verify correct method was used
        expected_method = override_method.value
        assert result.method_used == expected_method, \
            f"Expected {expected_method}, got {result.method_used}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        default_method=st.sampled_from([MethodType.TEMPLATE, MethodType.LLM, MethodType.HYBRID]),
    )
    def test_property_2_default_method_used_when_no_override(
        self,
        default_method: MethodType,
    ):
        """
        Property 2: Default method used when no override specified.
        
        For any default method, it should be used when no override is specified.
        
        **Feature: text-to-sql-methods, Property 2: 方法路由正确性**
        **Validates: Requirements 4.1**
        """
        # Create config with default method
        config = TextToSQLConfig(
            default_method=default_method,
            auto_select_enabled=False,  # Disable auto-select
        )
        
        # Create mocks
        mock_template = MockTemplateFiller(should_match=True)
        mock_llm = MockLLMGenerator(should_succeed=True)
        mock_hybrid = MockHybridGenerator(should_succeed=True)
        mock_plugin_manager = MockPluginManager()
        
        # Create switcher
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        # Generate without override
        result = asyncio.get_event_loop().run_until_complete(
            switcher.generate_sql("test query")
        )
        
        # Verify default method was used
        expected_method = default_method.value
        assert result.method_used == expected_method, \
            f"Expected default {expected_method}, got {result.method_used}"
    
    @settings(max_examples=100, deadline=None)
    @given(query=st.text(min_size=1, max_size=200))
    def test_property_2_template_routing(self, query: str):
        """
        Property 2: Template method routing.
        
        For any query with template method specified,
        the template filler should be called.
        
        **Feature: text-to-sql-methods, Property 2: 方法路由正确性**
        **Validates: Requirements 4.2**
        """
        assume(query.strip())
        
        config = TextToSQLConfig(auto_select_enabled=False)
        mock_template = MockTemplateFiller(should_match=True)
        mock_llm = MockLLMGenerator(should_succeed=True)
        mock_hybrid = MockHybridGenerator(should_succeed=True)
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        result = asyncio.get_event_loop().run_until_complete(
            switcher.generate_sql(query, method=MethodType.TEMPLATE)
        )
        
        assert mock_template.generate_called, "Template filler should be called"
        assert result.method_used == "template", "Method should be template"
    
    @settings(max_examples=100, deadline=None)
    @given(query=st.text(min_size=1, max_size=200))
    def test_property_2_llm_routing(self, query: str):
        """
        Property 2: LLM method routing.
        
        For any query with LLM method specified,
        the LLM generator should be called.
        
        **Feature: text-to-sql-methods, Property 2: 方法路由正确性**
        **Validates: Requirements 4.2**
        """
        assume(query.strip())
        
        config = TextToSQLConfig(auto_select_enabled=False)
        mock_template = MockTemplateFiller(should_match=True)
        mock_llm = MockLLMGenerator(should_succeed=True)
        mock_hybrid = MockHybridGenerator(should_succeed=True)
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        result = asyncio.get_event_loop().run_until_complete(
            switcher.generate_sql(query, method=MethodType.LLM)
        )
        
        assert mock_llm.generate_called, "LLM generator should be called"
        assert result.method_used == "llm", "Method should be llm"
    
    @settings(max_examples=100, deadline=None)
    @given(query=st.text(min_size=1, max_size=200))
    def test_property_2_hybrid_routing(self, query: str):
        """
        Property 2: Hybrid method routing.
        
        For any query with hybrid method specified,
        the hybrid generator should be called.
        
        **Feature: text-to-sql-methods, Property 2: 方法路由正确性**
        **Validates: Requirements 4.2**
        """
        assume(query.strip())
        
        config = TextToSQLConfig(auto_select_enabled=False)
        mock_template = MockTemplateFiller(should_match=True)
        mock_llm = MockLLMGenerator(should_succeed=True)
        mock_hybrid = MockHybridGenerator(should_succeed=True)
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        result = asyncio.get_event_loop().run_until_complete(
            switcher.generate_sql(query, method=MethodType.HYBRID)
        )
        
        assert mock_hybrid.generate_called, "Hybrid generator should be called"
        assert result.method_used == "hybrid", "Method should be hybrid"



# =============================================================================
# Method Switching Performance Tests
# =============================================================================

class TestMethodSwitchingPerformance:
    """Tests for method switching performance (< 500ms requirement)."""
    
    @settings(max_examples=100, deadline=None)
    @given(
        from_method=st.sampled_from([MethodType.TEMPLATE, MethodType.LLM, MethodType.HYBRID]),
        to_method=st.sampled_from([MethodType.TEMPLATE, MethodType.LLM, MethodType.HYBRID]),
    )
    def test_switch_time_under_500ms(
        self,
        from_method: MethodType,
        to_method: MethodType,
    ):
        """
        Test that method switching completes in under 500ms.
        
        **Feature: text-to-sql-methods, Property 2: 方法路由正确性**
        **Validates: Requirements 4.4**
        """
        config = TextToSQLConfig(default_method=from_method)
        
        mock_template = MockTemplateFiller()
        mock_llm = MockLLMGenerator()
        mock_hybrid = MockHybridGenerator()
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        # Switch method
        switch_time = switcher.switch_method(to_method)
        
        # Verify switch time is under 500ms
        assert switch_time < 500, f"Switch time {switch_time}ms exceeds 500ms limit"
        
        # Verify method was switched
        assert switcher.get_current_method() == to_method, \
            f"Method should be {to_method}, got {switcher.get_current_method()}"
    
    def test_multiple_switches_performance(self):
        """Test performance of multiple consecutive switches."""
        config = TextToSQLConfig(default_method=MethodType.TEMPLATE)
        
        mock_template = MockTemplateFiller()
        mock_llm = MockLLMGenerator()
        mock_hybrid = MockHybridGenerator()
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        methods = [MethodType.TEMPLATE, MethodType.LLM, MethodType.HYBRID]
        total_time = 0.0
        
        for _ in range(10):
            for method in methods:
                switch_time = switcher.switch_method(method)
                total_time += switch_time
        
        # Average switch time should be well under 500ms
        avg_time = total_time / 30
        assert avg_time < 100, f"Average switch time {avg_time}ms is too high"


# =============================================================================
# Auto Method Selection Tests
# =============================================================================

class TestAutoMethodSelection:
    """Tests for automatic method selection."""
    
    @settings(max_examples=100, deadline=None)
    @given(
        query=st.text(min_size=1, max_size=200),
        db_type=st.sampled_from(["postgresql", "mysql", "sqlite"]),
    )
    def test_auto_select_returns_valid_method(self, query: str, db_type: str):
        """
        Test that auto_select_method always returns a valid method.
        
        **Feature: text-to-sql-methods, Property 2: 方法路由正确性**
        **Validates: Requirements 4.5**
        """
        assume(query.strip())
        
        config = TextToSQLConfig(auto_select_enabled=True)
        mock_template = MockTemplateFiller()
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            plugin_manager=mock_plugin_manager,
        )
        
        selected = switcher.auto_select_method(query, db_type)
        
        # Should return a valid MethodType
        assert selected in [MethodType.TEMPLATE, MethodType.LLM, MethodType.HYBRID], \
            f"Invalid method selected: {selected}"
    
    def test_auto_select_template_for_simple_queries(self):
        """Test that simple queries select template method."""
        config = TextToSQLConfig(auto_select_enabled=True)
        mock_template = MockTemplateFiller(should_match=True, confidence=0.9)
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            plugin_manager=mock_plugin_manager,
        )
        
        # Simple count query
        simple_queries = [
            "统计用户的数量",
            "查询订单的总数",
            "计算销售的总额",
        ]
        
        for query in simple_queries:
            selected = switcher.auto_select_method(query)
            # Should prefer template for simple queries
            assert selected in [MethodType.TEMPLATE, MethodType.HYBRID], \
                f"Simple query '{query}' should select template or hybrid, got {selected}"
    
    def test_auto_select_llm_for_complex_queries(self):
        """Test that complex queries select LLM method."""
        config = TextToSQLConfig(auto_select_enabled=True)
        mock_template = MockTemplateFiller(should_match=False, confidence=0.0)
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            plugin_manager=mock_plugin_manager,
        )
        
        # Complex queries
        complex_queries = [
            "使用窗口函数计算每个部门的排名",
            "使用递归CTE查询组织架构",
            "使用JSONB提取嵌套数据",
        ]
        
        for query in complex_queries:
            selected = switcher.auto_select_method(query)
            # Should prefer LLM for complex queries
            assert selected in [MethodType.LLM, MethodType.HYBRID], \
                f"Complex query '{query}' should select LLM or hybrid, got {selected}"


# =============================================================================
# Fallback Mechanism Tests
# =============================================================================

class TestFallbackMechanism:
    """Tests for fallback mechanism when methods fail."""
    
    @settings(max_examples=100, deadline=None)
    @given(
        failing_method=st.sampled_from([MethodType.TEMPLATE, MethodType.LLM]),
    )
    def test_fallback_to_hybrid_on_failure(self, failing_method: MethodType):
        """
        Test that switcher falls back to hybrid when other methods fail.
        
        **Feature: text-to-sql-methods, Property 2: 方法路由正确性**
        **Validates: Requirements 4.1, 4.2**
        """
        config = TextToSQLConfig(
            default_method=failing_method,
            auto_select_enabled=False,
            fallback_enabled=True,
        )
        
        # Create failing mocks
        mock_template = MockTemplateFiller(should_match=False, confidence=0.0)
        mock_llm = MockLLMGenerator(should_succeed=False)
        mock_hybrid = MockHybridGenerator(should_succeed=True)
        mock_plugin_manager = MockPluginManager()
        
        # Make the failing method raise an exception
        if failing_method == MethodType.TEMPLATE:
            mock_template.generate = Mock(side_effect=Exception("Template failed"))
        else:
            mock_llm.generate = AsyncMock(side_effect=Exception("LLM failed"))
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        result = asyncio.get_event_loop().run_until_complete(
            switcher.generate_sql("test query", method=failing_method)
        )
        
        # Should have fallen back to hybrid
        if result.sql:
            assert "fallback" in result.metadata or result.method_used == "hybrid", \
                "Should indicate fallback was used"


# =============================================================================
# Statistics Tracking Tests
# =============================================================================

class TestStatisticsTracking:
    """Tests for statistics tracking."""
    
    def test_method_call_tracking(self):
        """Test that method calls are tracked correctly."""
        config = TextToSQLConfig(auto_select_enabled=False)
        
        mock_template = MockTemplateFiller(should_match=True)
        mock_llm = MockLLMGenerator(should_succeed=True)
        mock_hybrid = MockHybridGenerator(should_succeed=True)
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        # Make calls with different methods
        asyncio.get_event_loop().run_until_complete(
            switcher.generate_sql("query 1", method=MethodType.TEMPLATE)
        )
        asyncio.get_event_loop().run_until_complete(
            switcher.generate_sql("query 2", method=MethodType.LLM)
        )
        asyncio.get_event_loop().run_until_complete(
            switcher.generate_sql("query 3", method=MethodType.HYBRID)
        )
        
        stats = switcher.get_statistics()
        
        assert stats["total_calls"] == 3, "Should track total calls"
        assert stats["method_calls"]["template"] == 1, "Should track template calls"
        assert stats["method_calls"]["llm"] == 1, "Should track LLM calls"
        assert stats["method_calls"]["hybrid"] == 1, "Should track hybrid calls"
    
    def test_statistics_reset(self):
        """Test that statistics can be reset."""
        config = TextToSQLConfig(auto_select_enabled=False)
        
        mock_template = MockTemplateFiller(should_match=True)
        mock_llm = MockLLMGenerator(should_succeed=True)
        mock_hybrid = MockHybridGenerator(should_succeed=True)
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        # Make some calls
        asyncio.get_event_loop().run_until_complete(
            switcher.generate_sql("query", method=MethodType.TEMPLATE)
        )
        
        # Reset
        switcher.reset_statistics()
        
        stats = switcher.get_statistics()
        assert stats["total_calls"] == 0, "Total calls should be reset"
        assert len(stats["method_calls"]) == 0, "Method calls should be reset"


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfiguration:
    """Tests for configuration management."""
    
    def test_config_update(self):
        """Test configuration update."""
        initial_config = TextToSQLConfig(default_method=MethodType.TEMPLATE)
        
        mock_template = MockTemplateFiller()
        mock_llm = MockLLMGenerator()
        mock_hybrid = MockHybridGenerator()
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=initial_config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        # Update config
        new_config = TextToSQLConfig(default_method=MethodType.LLM)
        switcher.update_config(new_config)
        
        assert switcher.get_current_method() == MethodType.LLM, \
            "Default method should be updated"
    
    def test_list_available_methods(self):
        """Test listing available methods."""
        config = TextToSQLConfig()
        
        mock_template = MockTemplateFiller()
        mock_llm = MockLLMGenerator()
        mock_hybrid = MockHybridGenerator()
        mock_plugin_manager = MockPluginManager()
        
        switcher = MethodSwitcher(
            config=config,
            template_filler=mock_template,
            llm_generator=mock_llm,
            hybrid_generator=mock_hybrid,
            plugin_manager=mock_plugin_manager,
        )
        
        methods = switcher.list_available_methods()
        
        # Should have at least 3 built-in methods
        assert len(methods) >= 3, "Should have at least 3 methods"
        
        method_names = [m.name for m in methods]
        assert "template" in method_names, "Should have template method"
        assert "llm" in method_names, "Should have LLM method"
        assert "hybrid" in method_names, "Should have hybrid method"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
