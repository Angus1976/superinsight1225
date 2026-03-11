"""
Property-based tests for Tool Registration Round-Trip.

Validates: Requirement 3.1
"""

import pytest
from hypothesis import given, settings, strategies as st

from src.toolkit.models.tool import Tool, ToolCategory, ToolMetadata
from src.toolkit.orchestration.tool_registry import ToolRegistry


# ---------------------------------------------------------------------------
# Hypothesis Strategies
# ---------------------------------------------------------------------------

@st.composite
def tool_metadata_strategy(draw):
    """Generate random ToolMetadata with varying categories and capabilities."""
    tool_id = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
        min_size=1,
        max_size=30,
    ).filter(lambda s: s.strip()))
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "Z"), whitelist_characters="-_"),
        min_size=1,
        max_size=50,
    ).filter(lambda s: s.strip()))
    category = draw(st.sampled_from(list(ToolCategory)))
    capabilities = draw(st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
            min_size=1,
            max_size=20,
        ).filter(lambda s: s.strip()),
        min_size=1,
        max_size=5,
        unique=True,
    ))
    input_formats = draw(st.lists(
        st.sampled_from(["csv", "json", "xlsx", "txt", "parquet", "xml", "html"]),
        min_size=0,
        max_size=3,
        unique=True,
    ))
    output_formats = draw(st.lists(
        st.sampled_from(["csv", "json", "xlsx", "txt", "parquet", "xml", "html"]),
        min_size=0,
        max_size=3,
        unique=True,
    ))

    return ToolMetadata(
        id=tool_id,
        name=name,
        category=category,
        capabilities=capabilities,
        input_formats=input_formats,
        output_formats=output_formats,
    )


@st.composite
def tool_strategy(draw):
    """Generate a random Tool with valid metadata."""
    metadata = draw(tool_metadata_strategy())
    return Tool(metadata=metadata)


# ---------------------------------------------------------------------------
# Property 6: Tool Registration Round-Trip
# Validates: Requirement 3.1
#
# For any valid Tool, registering it in a fresh ToolRegistry makes it:
# a) discoverable by its capabilities
# b) discoverable by its category
# c) retrievable via get_tool_metadata with correct metadata
# ---------------------------------------------------------------------------

class TestToolRegistrationRoundTrip:
    """**Validates: Requirement 3.1**"""

    @given(tool=tool_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_registered_tool_discoverable_by_capabilities(self, tool: Tool):
        """A registered tool is found when searching by its capabilities."""
        registry = ToolRegistry()
        returned_id = registry.register_tool(tool)

        assert returned_id == tool.metadata.id

        if tool.metadata.capabilities:
            found = registry.find_tools(capabilities=tool.metadata.capabilities)
            found_ids = [t.metadata.id for t in found]
            assert tool.metadata.id in found_ids, (
                f"Tool {tool.metadata.id} not found by capabilities {tool.metadata.capabilities}"
            )

    @given(tool=tool_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_registered_tool_discoverable_by_category(self, tool: Tool):
        """A registered tool is found when searching by its category."""
        registry = ToolRegistry()
        registry.register_tool(tool)

        found = registry.find_tools(category=tool.metadata.category)
        found_ids = [t.metadata.id for t in found]
        assert tool.metadata.id in found_ids, (
            f"Tool {tool.metadata.id} not found by category {tool.metadata.category}"
        )

    @given(tool=tool_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_get_tool_metadata_returns_correct_metadata(self, tool: Tool):
        """get_tool_metadata returns the exact metadata that was registered."""
        registry = ToolRegistry()
        registry.register_tool(tool)

        metadata = registry.get_tool_metadata(tool.metadata.id)

        assert metadata is not None, "Metadata must not be None for a registered tool"
        assert metadata.id == tool.metadata.id
        assert metadata.name == tool.metadata.name
        assert metadata.category == tool.metadata.category
        assert metadata.capabilities == tool.metadata.capabilities
        assert metadata.input_formats == tool.metadata.input_formats
        assert metadata.output_formats == tool.metadata.output_formats
