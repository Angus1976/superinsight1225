"""
ToolRegistry — thread-safe tool registration, discovery, and version management.

Supports hot-plugging: tools can be registered/unregistered at runtime
without system restart. All public methods are protected by a threading lock.
"""

import threading
from typing import Dict, List, Optional

from src.toolkit.models.tool import (
    DependencyStatus,
    Tool,
    ToolCategory,
    ToolMetadata,
)


class ToolRegistry:
    """Thread-safe registry for managing processing tools.

    Provides registration, discovery, version management, and
    dependency resolution with hot-plugging support.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_tool(self, tool: Tool) -> str:
        """Register a tool, making it discoverable and executable.

        Returns the tool ID on success.
        Raises ValueError if metadata is invalid or ID already exists.
        """
        self._validate_metadata(tool.metadata)

        with self._lock:
            if tool.metadata.id in self._tools:
                raise ValueError(f"Tool already registered: {tool.metadata.id}")
            self._tools[tool.metadata.id] = tool

        return tool.metadata.id

    def unregister_tool(self, tool_id: str) -> bool:
        """Remove a tool by ID. Returns True if removed, False if not found."""
        with self._lock:
            if tool_id not in self._tools:
                return False
            del self._tools[tool_id]
            return True

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def find_tools(
        self,
        category: Optional[ToolCategory] = None,
        capabilities: Optional[List[str]] = None,
        input_format: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> List[Tool]:
        """Search for tools matching the given criteria.

        Results are sorted by tool name for determinism.
        """
        with self._lock:
            results = list(self._tools.values())

        results = self._filter_tools(results, category, capabilities, input_format, output_format)
        return sorted(results, key=lambda t: t.metadata.name)

    def get_tool_metadata(self, tool_id: str) -> Optional[ToolMetadata]:
        """Retrieve metadata for a specific tool. Returns None if not found."""
        with self._lock:
            tool = self._tools.get(tool_id)

        if tool is None:
            return None
        return tool.metadata

    # ------------------------------------------------------------------
    # Version management
    # ------------------------------------------------------------------

    def update_tool_version(self, tool_id: str, version: str) -> bool:
        """Update the version string of an existing tool.

        Returns True on success, False if tool not found.
        Raises ValueError if version string is empty.
        """
        if not version or not version.strip():
            raise ValueError("Version string must not be empty")

        with self._lock:
            tool = self._tools.get(tool_id)
            if tool is None:
                return False
            tool.metadata.version = version
            return True

    # ------------------------------------------------------------------
    # Dependency resolution
    # ------------------------------------------------------------------

    def check_dependencies(self, tool_id: str) -> DependencyStatus:
        """Check whether all dependencies of a tool are registered.

        Raises ValueError if the tool itself is not registered.
        """
        with self._lock:
            tool = self._tools.get(tool_id)
            if tool is None:
                raise ValueError(f"Tool not found: {tool_id}")

            deps = tool.metadata.dependencies
            resolved = [d for d in deps if d in self._tools]
            missing = [d for d in deps if d not in self._tools]

        return DependencyStatus(
            tool_id=tool_id,
            all_satisfied=len(missing) == 0,
            resolved=sorted(resolved),
            missing=sorted(missing),
        )

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def tool_count(self) -> int:
        """Number of currently registered tools."""
        with self._lock:
            return len(self._tools)

    def list_tool_ids(self) -> List[str]:
        """Return sorted list of all registered tool IDs."""
        with self._lock:
            return sorted(self._tools.keys())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_metadata(metadata: ToolMetadata) -> None:
        """Guard: reject metadata with missing required fields."""
        if not metadata.id or not metadata.id.strip():
            raise ValueError("Tool metadata must have a non-empty id")
        if not metadata.name or not metadata.name.strip():
            raise ValueError("Tool metadata must have a non-empty name")

    @staticmethod
    def _filter_tools(
        tools: List[Tool],
        category: Optional[ToolCategory],
        capabilities: Optional[List[str]],
        input_format: Optional[str],
        output_format: Optional[str],
    ) -> List[Tool]:
        """Apply search filters to a list of tools."""
        if category is not None:
            tools = [t for t in tools if t.metadata.category == category]
        if capabilities:
            cap_set = set(capabilities)
            tools = [t for t in tools if cap_set.issubset(set(t.metadata.capabilities))]
        if input_format is not None:
            tools = [t for t in tools if input_format in t.metadata.input_formats]
        if output_format is not None:
            tools = [t for t in tools if output_format in t.metadata.output_formats]
        return tools
