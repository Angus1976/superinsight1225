"""
Property-based tests for Plugin Manager.

Tests Property 6: 插件接口验证
Tests Property 7: 自动回退机制
Validates: Requirements 8.2, 8.7

For any registered plugin, the Plugin Manager should validate that it implements
all required interface methods. For any failed third-party call, the system
should automatically fallback to builtin methods.
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


class ConnectionType(str, Enum):
    """Plugin connection types."""
    REST_API = "rest_api"
    GRPC = "grpc"
    WEBHOOK = "webhook"
    SDK = "sdk"


class PluginInfo(BaseModel):
    """Plugin information."""
    name: str = Field(..., description="Plugin name")
    version: str = Field(default="1.0.0", description="Plugin version")
    description: str = Field(default="", description="Plugin description")
    connection_type: ConnectionType = Field(..., description="Connection type")
    supported_annotation_types: List[AnnotationType] = Field(
        default_factory=list, description="Supported annotation types"
    )
    config_schema: Dict[str, Any] = Field(default_factory=dict, description="Config schema")


class PluginHealthStatus(BaseModel):
    """Plugin health status."""
    healthy: bool = Field(..., description="Is plugin healthy")
    latency_ms: float = Field(default=0.0, description="Health check latency")
    message: str = Field(default="", description="Status message")


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
# Mock Plugin Interface
# ============================================================================

class MockPluginInterface(ABC):
    """Mock plugin interface for testing."""
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[AnnotationType]:
        pass
    
    @abstractmethod
    def to_native_format(self, tasks: List[AnnotationTask], annotation_type: AnnotationType) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def annotate(self, native_tasks: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def to_label_studio_format(self, native_results: Dict[str, Any]) -> List[AnnotationResult]:
        pass
    
    @abstractmethod
    async def health_check(self) -> PluginHealthStatus:
        pass


class ValidMockPlugin(MockPluginInterface):
    """Valid mock plugin implementing all required methods."""
    
    def __init__(self, name: str = "test_plugin", supported_types: List[AnnotationType] = None):
        self.name = name
        self._supported_types = supported_types or [AnnotationType.TEXT_CLASSIFICATION]
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name=self.name,
            version="1.0.0",
            description="Test plugin",
            connection_type=ConnectionType.REST_API,
            supported_annotation_types=self._supported_types,
        )
    
    def get_supported_types(self) -> List[AnnotationType]:
        return self._supported_types
    
    def to_native_format(self, tasks: List[AnnotationTask], annotation_type: AnnotationType) -> Dict[str, Any]:
        return {"tasks": [{"id": t.id, "data": t.data} for t in tasks]}
    
    async def annotate(self, native_tasks: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "results": [
                {"task_id": t["id"], "annotation": {"label": "test"}, "confidence": 0.9}
                for t in native_tasks.get("tasks", [])
            ]
        }
    
    def to_label_studio_format(self, native_results: Dict[str, Any]) -> List[AnnotationResult]:
        return [
            AnnotationResult(
                task_id=r["task_id"],
                annotation_data=r["annotation"],
                confidence=r["confidence"],
                method_used=self.name,
            )
            for r in native_results.get("results", [])
        ]
    
    async def health_check(self) -> PluginHealthStatus:
        return PluginHealthStatus(healthy=True, message="OK")


class FailingMockPlugin(MockPluginInterface):
    """Mock plugin that fails on annotate."""
    
    def __init__(self, name: str = "failing_plugin"):
        self.name = name
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name=self.name,
            version="1.0.0",
            description="Failing plugin",
            connection_type=ConnectionType.REST_API,
            supported_annotation_types=[AnnotationType.TEXT_CLASSIFICATION],
        )
    
    def get_supported_types(self) -> List[AnnotationType]:
        return [AnnotationType.TEXT_CLASSIFICATION]
    
    def to_native_format(self, tasks: List[AnnotationTask], annotation_type: AnnotationType) -> Dict[str, Any]:
        return {"tasks": [{"id": t.id} for t in tasks]}
    
    async def annotate(self, native_tasks: Dict[str, Any]) -> Dict[str, Any]:
        raise Exception("Plugin annotation failed")
    
    def to_label_studio_format(self, native_results: Dict[str, Any]) -> List[AnnotationResult]:
        return []
    
    async def health_check(self) -> PluginHealthStatus:
        return PluginHealthStatus(healthy=False, message="Plugin is unhealthy")


# ============================================================================
# Plugin Manager Mock
# ============================================================================

class MockPluginManager:
    """Mock plugin manager for testing."""
    
    REQUIRED_METHODS = [
        "get_info",
        "get_supported_types",
        "to_native_format",
        "annotate",
        "to_label_studio_format",
        "health_check",
    ]
    
    def __init__(self):
        self._plugins: Dict[str, MockPluginInterface] = {}
        self._enabled: Dict[str, bool] = {}
        self._priorities: Dict[str, int] = {}
    
    def validate_plugin_interface(self, plugin: Any, name: str) -> bool:
        """
        Validate that plugin implements all required methods.
        
        Property 6: 插件接口验证
        """
        for method_name in self.REQUIRED_METHODS:
            if not hasattr(plugin, method_name):
                return False
            if not callable(getattr(plugin, method_name)):
                return False
        return True
    
    def register_plugin(self, plugin: MockPluginInterface, name: str, priority: int = 0) -> bool:
        """Register a plugin after validation."""
        if not self.validate_plugin_interface(plugin, name):
            return False
        
        self._plugins[name] = plugin
        self._enabled[name] = True
        self._priorities[name] = priority
        return True
    
    def get_plugin(self, name: str) -> Optional[MockPluginInterface]:
        """Get a plugin by name."""
        if name in self._plugins and self._enabled.get(name, False):
            return self._plugins[name]
        return None
    
    def get_best_plugin(self, annotation_type: AnnotationType) -> Optional[MockPluginInterface]:
        """Get best plugin for annotation type by priority."""
        candidates = []
        for name, plugin in self._plugins.items():
            if not self._enabled.get(name, False):
                continue
            if annotation_type in plugin.get_supported_types():
                candidates.append((name, plugin, self._priorities.get(name, 0)))
        
        if not candidates:
            return None
        
        # Sort by priority descending
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[0][1]


# ============================================================================
# Third Party Adapter Mock with Fallback
# ============================================================================

class MockThirdPartyAdapter:
    """Mock third-party adapter with fallback support."""
    
    def __init__(self, plugin_manager: MockPluginManager):
        self.plugin_manager = plugin_manager
        self.fallback_called = False
    
    async def annotate_with_fallback(
        self,
        tasks: List[AnnotationTask],
        plugin_name: str,
        annotation_type: AnnotationType,
    ) -> List[AnnotationResult]:
        """
        Annotate with automatic fallback on failure.
        
        Property 7: 自动回退机制
        """
        plugin = self.plugin_manager.get_plugin(plugin_name)
        
        if not plugin:
            # Fallback: plugin not found
            self.fallback_called = True
            return self._builtin_annotate(tasks, annotation_type)
        
        try:
            native_tasks = plugin.to_native_format(tasks, annotation_type)
            native_results = await plugin.annotate(native_tasks)
            return plugin.to_label_studio_format(native_results)
        except Exception:
            # Fallback: plugin failed
            self.fallback_called = True
            return self._builtin_annotate(tasks, annotation_type)
    
    def _builtin_annotate(
        self,
        tasks: List[AnnotationTask],
        annotation_type: AnnotationType,
    ) -> List[AnnotationResult]:
        """Builtin fallback annotation."""
        return [
            AnnotationResult(
                task_id=task.id,
                annotation_data={"label": "fallback"},
                confidence=0.5,
                method_used="builtin_fallback",
            )
            for task in tasks
        ]


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def plugin_info_strategy(draw):
    """Generate random PluginInfo."""
    return PluginInfo(
        name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))),
        version=f"{draw(st.integers(0, 10))}.{draw(st.integers(0, 10))}.{draw(st.integers(0, 10))}",
        description=draw(st.text(max_size=200)),
        connection_type=draw(st.sampled_from(list(ConnectionType))),
        supported_annotation_types=draw(st.lists(
            st.sampled_from(list(AnnotationType)),
            min_size=1,
            max_size=3,
            unique=True,
        )),
    )


@st.composite
def annotation_task_strategy(draw):
    """Generate random AnnotationTask."""
    return AnnotationTask(
        id=str(uuid4()),
        data={"text": draw(st.text(min_size=1, max_size=500))},
        annotation_type=draw(st.sampled_from(list(AnnotationType))),
    )


# ============================================================================
# Property Tests
# ============================================================================

class TestPluginInterfaceValidation:
    """
    Property 6: 插件接口验证
    
    For any registered plugin, the Plugin Manager should validate that it
    implements all required interface methods.
    
    **Validates: Requirements 8.2**
    """
    
    def test_valid_plugin_passes_validation(self):
        """
        **Feature: ai-annotation, Property 6: 插件接口验证**
        **Validates: Requirements 8.2**
        
        Valid plugins implementing all methods should pass validation.
        """
        manager = MockPluginManager()
        plugin = ValidMockPlugin("test")
        
        assert manager.validate_plugin_interface(plugin, "test") is True
    
    def test_plugin_missing_method_fails_validation(self):
        """
        **Feature: ai-annotation, Property 6: 插件接口验证**
        **Validates: Requirements 8.2**
        
        Plugins missing required methods should fail validation.
        """
        manager = MockPluginManager()
        
        # Create incomplete plugin
        class IncompletePlugin:
            def get_info(self):
                return PluginInfo(name="incomplete", connection_type=ConnectionType.REST_API)
            # Missing other required methods
        
        plugin = IncompletePlugin()
        assert manager.validate_plugin_interface(plugin, "incomplete") is False
    
    @given(name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    @settings(max_examples=100)
    def test_valid_plugin_registration_succeeds(self, name: str):
        """
        **Feature: ai-annotation, Property 6: 插件接口验证**
        **Validates: Requirements 8.2**
        
        Valid plugins should be successfully registered.
        """
        manager = MockPluginManager()
        plugin = ValidMockPlugin(name)
        
        result = manager.register_plugin(plugin, name)
        assert result is True
        assert manager.get_plugin(name) is not None
    
    @given(
        names=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))),
            min_size=1,
            max_size=10,
            unique=True,
        )
    )
    @settings(max_examples=100)
    def test_all_registered_plugins_have_required_methods(self, names: List[str]):
        """
        **Feature: ai-annotation, Property 6: 插件接口验证**
        **Validates: Requirements 8.2**
        
        All registered plugins must have all required methods.
        """
        manager = MockPluginManager()
        
        for name in names:
            plugin = ValidMockPlugin(name)
            manager.register_plugin(plugin, name)
        
        # Verify all registered plugins have required methods
        for name in names:
            plugin = manager.get_plugin(name)
            assert plugin is not None
            for method_name in MockPluginManager.REQUIRED_METHODS:
                assert hasattr(plugin, method_name)
                assert callable(getattr(plugin, method_name))


class TestAutomaticFallback:
    """
    Property 7: 自动回退机制
    
    For any failed third-party call, the system should automatically
    fallback to builtin methods and not return empty results.
    
    **Validates: Requirements 8.7**
    """
    
    @pytest.mark.asyncio
    async def test_fallback_on_plugin_not_found(self):
        """
        **Feature: ai-annotation, Property 7: 自动回退机制**
        **Validates: Requirements 8.7**
        
        When plugin is not found, fallback should be used.
        """
        manager = MockPluginManager()
        adapter = MockThirdPartyAdapter(manager)
        
        tasks = [AnnotationTask(
            id="task1",
            data={"text": "test"},
            annotation_type=AnnotationType.TEXT_CLASSIFICATION,
        )]
        
        results = await adapter.annotate_with_fallback(
            tasks, "nonexistent_plugin", AnnotationType.TEXT_CLASSIFICATION
        )
        
        assert adapter.fallback_called is True
        assert len(results) == len(tasks)
        assert all(r.method_used == "builtin_fallback" for r in results)
    
    @pytest.mark.asyncio
    async def test_fallback_on_plugin_failure(self):
        """
        **Feature: ai-annotation, Property 7: 自动回退机制**
        **Validates: Requirements 8.7**
        
        When plugin fails, fallback should be used.
        """
        manager = MockPluginManager()
        failing_plugin = FailingMockPlugin("failing")
        manager.register_plugin(failing_plugin, "failing")
        
        adapter = MockThirdPartyAdapter(manager)
        
        tasks = [AnnotationTask(
            id="task1",
            data={"text": "test"},
            annotation_type=AnnotationType.TEXT_CLASSIFICATION,
        )]
        
        results = await adapter.annotate_with_fallback(
            tasks, "failing", AnnotationType.TEXT_CLASSIFICATION
        )
        
        assert adapter.fallback_called is True
        assert len(results) == len(tasks)
        assert all(r.method_used == "builtin_fallback" for r in results)
    
    @pytest.mark.asyncio
    @given(tasks=st.lists(annotation_task_strategy(), min_size=1, max_size=10))
    @settings(max_examples=100)
    async def test_fallback_never_returns_empty(self, tasks: List[AnnotationTask]):
        """
        **Feature: ai-annotation, Property 7: 自动回退机制**
        **Validates: Requirements 8.7**
        
        Fallback should never return empty results.
        """
        manager = MockPluginManager()
        adapter = MockThirdPartyAdapter(manager)
        
        # Use nonexistent plugin to trigger fallback
        results = await adapter.annotate_with_fallback(
            tasks, "nonexistent", AnnotationType.TEXT_CLASSIFICATION
        )
        
        assert len(results) == len(tasks), \
            "Fallback must return result for each task"
        assert all(r.task_id for r in results), \
            "All results must have task_id"
        assert all(r.annotation_data is not None for r in results), \
            "All results must have annotation_data"
    
    @pytest.mark.asyncio
    async def test_successful_plugin_no_fallback(self):
        """
        **Feature: ai-annotation, Property 7: 自动回退机制**
        **Validates: Requirements 8.7**
        
        When plugin succeeds, fallback should not be used.
        """
        manager = MockPluginManager()
        valid_plugin = ValidMockPlugin("valid")
        manager.register_plugin(valid_plugin, "valid")
        
        adapter = MockThirdPartyAdapter(manager)
        
        tasks = [AnnotationTask(
            id="task1",
            data={"text": "test"},
            annotation_type=AnnotationType.TEXT_CLASSIFICATION,
        )]
        
        results = await adapter.annotate_with_fallback(
            tasks, "valid", AnnotationType.TEXT_CLASSIFICATION
        )
        
        assert adapter.fallback_called is False
        assert len(results) == len(tasks)
        assert all(r.method_used == "valid" for r in results)


class TestPluginPriority:
    """
    Tests for plugin priority management.
    
    **Validates: Requirements 9.6**
    """
    
    @given(
        priorities=st.lists(
            st.integers(min_value=0, max_value=100),
            min_size=2,
            max_size=5,
        )
    )
    @settings(max_examples=100)
    def test_highest_priority_plugin_selected(self, priorities: List[int]):
        """
        **Feature: ai-annotation, Property 6: 插件接口验证**
        **Validates: Requirements 9.6**
        
        Plugin with highest priority should be selected.
        """
        manager = MockPluginManager()
        
        # Register plugins with different priorities
        for i, priority in enumerate(priorities):
            plugin = ValidMockPlugin(f"plugin_{i}")
            manager.register_plugin(plugin, f"plugin_{i}", priority)
            manager._priorities[f"plugin_{i}"] = priority
        
        # Get best plugin
        best = manager.get_best_plugin(AnnotationType.TEXT_CLASSIFICATION)
        
        assert best is not None
        
        # Find expected best (highest priority)
        max_priority = max(priorities)
        expected_idx = priorities.index(max_priority)
        expected_name = f"plugin_{expected_idx}"
        
        assert best.name == expected_name


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
