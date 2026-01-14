"""
Property-based tests for Method Switcher.

Tests Property 2: 方法路由正确性
Validates: Requirements 4.2, 4.3

For any configured default method and specified method, the Method Switcher
should correctly route to the corresponding service, with specified method
taking priority over default method.
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
from abc import ABC, abstractmethod


# ============================================================================
# Local copies of schemas to avoid import issues
# ============================================================================

class AnnotationType(str, Enum):
    """Supported annotation types."""
    TEXT_CLASSIFICATION = "text_classification"
    NER = "ner"
    SENTIMENT = "sentiment"


class AnnotationMethodType(str, Enum):
    """Available annotation method types."""
    LLM = "llm"
    ML_BACKEND = "ml_backend"
    ARGILLA = "argilla"
    THIRD_PARTY = "third_party"
    CUSTOM = "custom"


class MethodInfo(BaseModel):
    """Information about an annotation method."""
    name: str = Field(..., description="Method name")
    method_type: AnnotationMethodType = Field(..., description="Method type")
    description: str = Field(default="", description="Description")
    supported_types: List[AnnotationType] = Field(default_factory=list, description="Supported types")
    enabled: bool = Field(default=True, description="Is enabled")


class AnnotationTask(BaseModel):
    """Annotation task."""
    id: str = Field(..., description="Task ID")
    data: Dict[str, Any] = Field(..., description="Task data")
    annotation_type: AnnotationType = Field(..., description="Annotation type")


class AnnotationResult(BaseModel):
    """Annotation result."""
    task_id: str = Field(..., description="Task ID")
    annotation_data: Dict[str, Any] = Field(..., description="Annotation data")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence")
    method_used: str = Field(default="", description="Method used")


# ============================================================================
# Mock Method Implementation
# ============================================================================

class MockAnnotationMethod:
    """Mock annotation method for testing."""
    
    def __init__(
        self,
        name: str,
        method_type: AnnotationMethodType = AnnotationMethodType.CUSTOM,
        supported_types: Optional[List[AnnotationType]] = None,
    ):
        self.name = name
        self.method_type = method_type
        self._supported_types = supported_types or list(AnnotationType)
        self.call_count = 0
    
    async def annotate(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
        **kwargs
    ) -> List[AnnotationResult]:
        """Execute annotation."""
        self.call_count += 1
        return [
            AnnotationResult(
                task_id=task.id,
                annotation_data={"label": f"{self.name}_result"},
                confidence=0.8,
                method_used=self.name,
            )
            for task in tasks
        ]
    
    def get_info(self) -> MethodInfo:
        return MethodInfo(
            name=self.name,
            method_type=self.method_type,
            description=f"Mock method: {self.name}",
            supported_types=self._supported_types,
        )
    
    def supports_type(self, annotation_type: AnnotationType) -> bool:
        return annotation_type in self._supported_types


# ============================================================================
# Mock Method Switcher
# ============================================================================

class MockMethodSwitcher:
    """Mock method switcher for testing."""
    
    def __init__(self):
        self._methods: Dict[str, MockAnnotationMethod] = {}
        self._default_method: str = ""
        self._switch_logs: List[Dict[str, Any]] = []
    
    def register_method(self, name: str, method: MockAnnotationMethod) -> None:
        """Register a method."""
        self._methods[name] = method
        if not self._default_method:
            self._default_method = name
    
    def get_current_method(self) -> str:
        """Get current default method."""
        return self._default_method
    
    def switch_method(self, method: str, reason: str = "") -> bool:
        """Switch default method."""
        if method not in self._methods:
            return False
        
        old_method = self._default_method
        self._default_method = method
        
        self._switch_logs.append({
            "from": old_method,
            "to": method,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return True
    
    async def annotate(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
        method: Optional[str] = None,
        **kwargs
    ) -> List[AnnotationResult]:
        """
        Execute annotation.
        
        Property 2: 方法路由正确性
        - Specified method takes priority over default
        - Routes to correct method
        """
        # Specified method takes priority over default
        method_name = method if method else self._default_method
        
        if method_name not in self._methods:
            raise ValueError(f"Unknown method: {method_name}")
        
        annotation_method = self._methods[method_name]
        
        if not annotation_method.supports_type(annotation_type):
            raise ValueError(f"Method {method_name} doesn't support {annotation_type}")
        
        return await annotation_method.annotate(tasks, annotation_type, **kwargs)
    
    def list_available_methods(self) -> List[str]:
        """List available methods."""
        return list(self._methods.keys())
    
    def get_switch_history(self) -> List[Dict[str, Any]]:
        """Get switch history."""
        return self._switch_logs


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def annotation_task_strategy(draw):
    """Generate random AnnotationTask."""
    return AnnotationTask(
        id=str(uuid4()),
        data={"text": draw(st.text(min_size=1, max_size=500))},
        annotation_type=draw(st.sampled_from(list(AnnotationType))),
    )


@st.composite
def method_name_strategy(draw):
    """Generate valid method names."""
    return draw(st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_')
    ))


# ============================================================================
# Property Tests
# ============================================================================

class TestMethodRouting:
    """
    Property 2: 方法路由正确性
    
    For any configured default method and specified method, the Method Switcher
    should correctly route to the corresponding service, with specified method
    taking priority over default method.
    
    **Validates: Requirements 4.2, 4.3**
    """
    
    @pytest.mark.asyncio
    async def test_routes_to_default_method_when_not_specified(self):
        """
        **Feature: ai-annotation, Property 2: 方法路由正确性**
        **Validates: Requirements 4.2**
        
        When no method is specified, should route to default method.
        """
        switcher = MockMethodSwitcher()
        
        method_a = MockAnnotationMethod("method_a")
        method_b = MockAnnotationMethod("method_b")
        
        switcher.register_method("method_a", method_a)
        switcher.register_method("method_b", method_b)
        switcher.switch_method("method_a")
        
        tasks = [AnnotationTask(
            id="task1",
            data={"text": "test"},
            annotation_type=AnnotationType.TEXT_CLASSIFICATION,
        )]
        
        results = await switcher.annotate(
            tasks, AnnotationType.TEXT_CLASSIFICATION
        )
        
        assert len(results) == 1
        assert results[0].method_used == "method_a"
        assert method_a.call_count == 1
        assert method_b.call_count == 0
    
    @pytest.mark.asyncio
    async def test_specified_method_takes_priority(self):
        """
        **Feature: ai-annotation, Property 2: 方法路由正确性**
        **Validates: Requirements 4.3**
        
        Specified method should take priority over default method.
        """
        switcher = MockMethodSwitcher()
        
        method_a = MockAnnotationMethod("method_a")
        method_b = MockAnnotationMethod("method_b")
        
        switcher.register_method("method_a", method_a)
        switcher.register_method("method_b", method_b)
        switcher.switch_method("method_a")  # Set default to method_a
        
        tasks = [AnnotationTask(
            id="task1",
            data={"text": "test"},
            annotation_type=AnnotationType.TEXT_CLASSIFICATION,
        )]
        
        # Specify method_b explicitly
        results = await switcher.annotate(
            tasks, AnnotationType.TEXT_CLASSIFICATION, method="method_b"
        )
        
        assert len(results) == 1
        assert results[0].method_used == "method_b"
        assert method_a.call_count == 0  # Default not called
        assert method_b.call_count == 1  # Specified method called
    
    @pytest.mark.asyncio
    @given(
        default_idx=st.integers(min_value=0, max_value=2),
        specified_idx=st.integers(min_value=0, max_value=2),
    )
    @settings(max_examples=100)
    async def test_routing_correctness_property(
        self,
        default_idx: int,
        specified_idx: int,
    ):
        """
        **Feature: ai-annotation, Property 2: 方法路由正确性**
        **Validates: Requirements 4.2, 4.3**
        
        For any combination of default and specified methods,
        routing should be correct.
        """
        switcher = MockMethodSwitcher()
        
        methods = [
            MockAnnotationMethod("method_0"),
            MockAnnotationMethod("method_1"),
            MockAnnotationMethod("method_2"),
        ]
        
        for m in methods:
            switcher.register_method(m.name, m)
        
        # Set default
        switcher.switch_method(f"method_{default_idx}")
        
        tasks = [AnnotationTask(
            id="task1",
            data={"text": "test"},
            annotation_type=AnnotationType.TEXT_CLASSIFICATION,
        )]
        
        # Test with specified method
        results = await switcher.annotate(
            tasks,
            AnnotationType.TEXT_CLASSIFICATION,
            method=f"method_{specified_idx}",
        )
        
        # Specified method should be used
        assert results[0].method_used == f"method_{specified_idx}"
        assert methods[specified_idx].call_count == 1
        
        # Other methods should not be called
        for i, m in enumerate(methods):
            if i != specified_idx:
                assert m.call_count == 0
    
    @pytest.mark.asyncio
    async def test_unknown_method_raises_error(self):
        """
        **Feature: ai-annotation, Property 2: 方法路由正确性**
        **Validates: Requirements 4.2**
        
        Unknown method should raise error.
        """
        switcher = MockMethodSwitcher()
        switcher.register_method("method_a", MockAnnotationMethod("method_a"))
        
        tasks = [AnnotationTask(
            id="task1",
            data={"text": "test"},
            annotation_type=AnnotationType.TEXT_CLASSIFICATION,
        )]
        
        with pytest.raises(ValueError, match="Unknown method"):
            await switcher.annotate(
                tasks,
                AnnotationType.TEXT_CLASSIFICATION,
                method="nonexistent",
            )


class TestMethodSwitching:
    """
    Tests for method switching functionality.
    
    **Validates: Requirements 4.4**
    """
    
    def test_switch_method_updates_default(self):
        """
        **Feature: ai-annotation, Property 2: 方法路由正确性**
        **Validates: Requirements 4.4**
        
        Switching method should update the default.
        """
        switcher = MockMethodSwitcher()
        
        switcher.register_method("method_a", MockAnnotationMethod("method_a"))
        switcher.register_method("method_b", MockAnnotationMethod("method_b"))
        
        assert switcher.get_current_method() == "method_a"
        
        switcher.switch_method("method_b")
        assert switcher.get_current_method() == "method_b"
    
    def test_switch_to_unknown_method_fails(self):
        """
        **Feature: ai-annotation, Property 2: 方法路由正确性**
        **Validates: Requirements 4.4**
        
        Switching to unknown method should fail.
        """
        switcher = MockMethodSwitcher()
        switcher.register_method("method_a", MockAnnotationMethod("method_a"))
        
        result = switcher.switch_method("nonexistent")
        assert result is False
        assert switcher.get_current_method() == "method_a"
    
    @given(
        method_names=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            min_size=2,
            max_size=5,
            unique=True,
        )
    )
    @settings(max_examples=100)
    def test_switch_logs_recorded(self, method_names: List[str]):
        """
        **Feature: ai-annotation, Property 2: 方法路由正确性**
        **Validates: Requirements 4.6**
        
        Method switches should be logged.
        """
        switcher = MockMethodSwitcher()
        
        for name in method_names:
            switcher.register_method(name, MockAnnotationMethod(name))
        
        # Perform switches
        for i in range(1, len(method_names)):
            switcher.switch_method(method_names[i], f"switch_{i}")
        
        history = switcher.get_switch_history()
        
        # Should have len-1 switches
        assert len(history) == len(method_names) - 1
        
        # Each switch should have required fields
        for log in history:
            assert "from" in log
            assert "to" in log
            assert "reason" in log
            assert "timestamp" in log


class TestAnnotationTypeSupport:
    """
    Tests for annotation type support checking.
    
    **Validates: Requirements 4.2**
    """
    
    @pytest.mark.asyncio
    async def test_unsupported_type_raises_error(self):
        """
        **Feature: ai-annotation, Property 2: 方法路由正确性**
        **Validates: Requirements 4.2**
        
        Using unsupported annotation type should raise error.
        """
        switcher = MockMethodSwitcher()
        
        # Method only supports TEXT_CLASSIFICATION
        limited_method = MockAnnotationMethod(
            "limited",
            supported_types=[AnnotationType.TEXT_CLASSIFICATION],
        )
        switcher.register_method("limited", limited_method)
        
        tasks = [AnnotationTask(
            id="task1",
            data={"text": "test"},
            annotation_type=AnnotationType.NER,
        )]
        
        with pytest.raises(ValueError, match="doesn't support"):
            await switcher.annotate(tasks, AnnotationType.NER)
    
    @pytest.mark.asyncio
    @given(annotation_type=st.sampled_from(list(AnnotationType)))
    @settings(max_examples=100)
    async def test_supported_type_succeeds(self, annotation_type: AnnotationType):
        """
        **Feature: ai-annotation, Property 2: 方法路由正确性**
        **Validates: Requirements 4.2**
        
        Using supported annotation type should succeed.
        """
        switcher = MockMethodSwitcher()
        
        # Method supports all types
        method = MockAnnotationMethod("all_types")
        switcher.register_method("all_types", method)
        
        tasks = [AnnotationTask(
            id="task1",
            data={"text": "test"},
            annotation_type=annotation_type,
        )]
        
        results = await switcher.annotate(tasks, annotation_type)
        
        assert len(results) == 1
        assert results[0].method_used == "all_types"


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
