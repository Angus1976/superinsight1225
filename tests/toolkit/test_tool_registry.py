"""
Unit tests for ToolRegistry — registration, discovery, version management,
dependency resolution, and hot-plugging.

Validates Requirements 3.1 and 3.2.
"""

import threading
from typing import List, Optional

import pytest

from src.toolkit.models.tool import (
    DependencyStatus,
    Tool,
    ToolCategory,
    ToolMetadata,
)
from src.toolkit.orchestration.tool_registry import ToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool(
    tool_id: str = "tool-1",
    name: str = "Test Tool",
    category: ToolCategory = ToolCategory.ANALYZER,
    capabilities: Optional[List[str]] = None,
    input_formats: Optional[List[str]] = None,
    output_formats: Optional[List[str]] = None,
    dependencies: Optional[List[str]] = None,
    version: str = "1.0.0",
) -> Tool:
    return Tool(
        metadata=ToolMetadata(
            id=tool_id,
            name=name,
            category=category,
            capabilities=capabilities or [],
            input_formats=input_formats or [],
            output_formats=output_formats or [],
            dependencies=dependencies or [],
            version=version,
        )
    )


# ---------------------------------------------------------------------------
# Registration tests  (Req 3.1, 3.2)
# ---------------------------------------------------------------------------

class TestRegisterTool:
    def test_register_returns_tool_id(self):
        registry = ToolRegistry()
        tid = registry.register_tool(_make_tool("abc"))
        assert tid == "abc"

    def test_registered_tool_is_discoverable(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("t1", name="Alpha"))
        results = registry.find_tools()
        assert len(results) == 1
        assert results[0].metadata.id == "t1"

    def test_duplicate_id_raises(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("dup"))
        with pytest.raises(ValueError, match="already registered"):
            registry.register_tool(_make_tool("dup"))

    def test_tool_count_increments(self):
        registry = ToolRegistry()
        assert registry.tool_count == 0
        registry.register_tool(_make_tool("a"))
        assert registry.tool_count == 1
        registry.register_tool(_make_tool("b"))
        assert registry.tool_count == 2


class TestUnregisterTool:
    def test_unregister_existing(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("x"))
        assert registry.unregister_tool("x") is True
        assert registry.tool_count == 0

    def test_unregister_nonexistent_returns_false(self):
        registry = ToolRegistry()
        assert registry.unregister_tool("nope") is False

    def test_unregistered_tool_not_discoverable(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("rm", capabilities=["cap"]))
        registry.unregister_tool("rm")
        assert registry.find_tools(capabilities=["cap"]) == []


# ---------------------------------------------------------------------------
# Discovery tests
# ---------------------------------------------------------------------------

class TestFindTools:
    def test_filter_by_category(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("a1", name="A", category=ToolCategory.ANALYZER))
        registry.register_tool(_make_tool("t1", name="T", category=ToolCategory.TRANSFORMER))

        results = registry.find_tools(category=ToolCategory.ANALYZER)
        assert len(results) == 1
        assert results[0].metadata.id == "a1"

    def test_filter_by_capabilities(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("c1", name="C1", capabilities=["nlp", "ner"]))
        registry.register_tool(_make_tool("c2", name="C2", capabilities=["nlp"]))

        results = registry.find_tools(capabilities=["nlp", "ner"])
        assert len(results) == 1
        assert results[0].metadata.id == "c1"

    def test_filter_by_input_format(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("i1", name="I1", input_formats=["csv", "json"]))
        registry.register_tool(_make_tool("i2", name="I2", input_formats=["parquet"]))

        results = registry.find_tools(input_format="csv")
        assert len(results) == 1
        assert results[0].metadata.id == "i1"

    def test_filter_by_output_format(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("o1", name="O1", output_formats=["json"]))
        registry.register_tool(_make_tool("o2", name="O2", output_formats=["csv"]))

        results = registry.find_tools(output_format="json")
        assert len(results) == 1
        assert results[0].metadata.id == "o1"

    def test_combined_filters(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool(
            "match", name="Match",
            category=ToolCategory.AI_MODEL,
            capabilities=["embedding"],
            input_formats=["text"],
        ))
        registry.register_tool(_make_tool(
            "miss", name="Miss",
            category=ToolCategory.AI_MODEL,
            capabilities=["classification"],
            input_formats=["text"],
        ))

        results = registry.find_tools(
            category=ToolCategory.AI_MODEL,
            capabilities=["embedding"],
            input_format="text",
        )
        assert len(results) == 1
        assert results[0].metadata.id == "match"

    def test_results_sorted_by_name(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("z", name="Zeta"))
        registry.register_tool(_make_tool("a", name="Alpha"))
        registry.register_tool(_make_tool("m", name="Mid"))

        names = [t.metadata.name for t in registry.find_tools()]
        assert names == ["Alpha", "Mid", "Zeta"]

    def test_no_match_returns_empty(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("x", name="X"))
        assert registry.find_tools(category=ToolCategory.VISUALIZER) == []


# ---------------------------------------------------------------------------
# Metadata retrieval
# ---------------------------------------------------------------------------

class TestGetToolMetadata:
    def test_existing_tool(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("m1", name="Meta"))
        meta = registry.get_tool_metadata("m1")
        assert meta is not None
        assert meta.name == "Meta"

    def test_nonexistent_returns_none(self):
        registry = ToolRegistry()
        assert registry.get_tool_metadata("ghost") is None


# ---------------------------------------------------------------------------
# Version management
# ---------------------------------------------------------------------------

class TestUpdateToolVersion:
    def test_update_version(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("v1", version="1.0.0"))
        assert registry.update_tool_version("v1", "2.0.0") is True
        assert registry.get_tool_metadata("v1").version == "2.0.0"

    def test_update_nonexistent_returns_false(self):
        registry = ToolRegistry()
        assert registry.update_tool_version("nope", "2.0.0") is False

    def test_empty_version_raises(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("v2"))
        with pytest.raises(ValueError, match="must not be empty"):
            registry.update_tool_version("v2", "")


# ---------------------------------------------------------------------------
# Dependency resolution
# ---------------------------------------------------------------------------

class TestCheckDependencies:
    def test_no_dependencies(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("solo"))
        status = registry.check_dependencies("solo")
        assert status.all_satisfied is True
        assert status.missing == []

    def test_all_satisfied(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("dep-a", name="A"))
        registry.register_tool(_make_tool("dep-b", name="B"))
        registry.register_tool(_make_tool("main", name="Main", dependencies=["dep-a", "dep-b"]))

        status = registry.check_dependencies("main")
        assert status.all_satisfied is True
        assert sorted(status.resolved) == ["dep-a", "dep-b"]
        assert status.missing == []

    def test_missing_dependency(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("partial", name="P", dependencies=["exists", "gone"]))
        registry.register_tool(_make_tool("exists", name="E"))

        status = registry.check_dependencies("partial")
        assert status.all_satisfied is False
        assert "gone" in status.missing
        assert "exists" in status.resolved

    def test_unknown_tool_raises(self):
        registry = ToolRegistry()
        with pytest.raises(ValueError, match="not found"):
            registry.check_dependencies("unknown")


# ---------------------------------------------------------------------------
# Hot-plugging (Req 3.2) — runtime add/remove without restart
# ---------------------------------------------------------------------------

class TestHotPlugging:
    def test_register_and_use_at_runtime(self):
        """Tools registered after init are immediately discoverable."""
        registry = ToolRegistry()
        assert registry.tool_count == 0

        registry.register_tool(_make_tool("hot1", name="Hot1", capabilities=["stream"]))
        assert registry.tool_count == 1
        assert len(registry.find_tools(capabilities=["stream"])) == 1

    def test_unregister_at_runtime(self):
        """Unregistered tools are immediately undiscoverable."""
        registry = ToolRegistry()
        registry.register_tool(_make_tool("hot2", name="Hot2"))
        registry.unregister_tool("hot2")
        assert registry.tool_count == 0
        assert registry.find_tools() == []

    def test_concurrent_registration(self):
        """Multiple threads can register tools safely."""
        registry = ToolRegistry()
        errors: list = []

        def register(idx: int):
            try:
                registry.register_tool(_make_tool(f"t-{idx}", name=f"Tool {idx}"))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert registry.tool_count == 20

    def test_dependency_updates_after_hot_plug(self):
        """Dependencies resolve correctly after a new tool is hot-plugged."""
        registry = ToolRegistry()
        registry.register_tool(_make_tool("consumer", name="C", dependencies=["provider"]))

        status_before = registry.check_dependencies("consumer")
        assert status_before.all_satisfied is False

        registry.register_tool(_make_tool("provider", name="P"))

        status_after = registry.check_dependencies("consumer")
        assert status_after.all_satisfied is True


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------

class TestIntrospection:
    def test_list_tool_ids_sorted(self):
        registry = ToolRegistry()
        registry.register_tool(_make_tool("z-tool", name="Z"))
        registry.register_tool(_make_tool("a-tool", name="A"))
        assert registry.list_tool_ids() == ["a-tool", "z-tool"]
