"""
Storage Adapter Layer for the Intelligent Data Processing Toolkit.

Provides unified interface to multiple storage backends with
intelligent storage selection, lineage tracking, and local cache fallback.
"""

from .base import StorageAdapter, StorageResult, QueryResult
from .adapters import (
    PostgreSQLAdapter,
    VectorDBAdapter,
    GraphDBAdapter,
    DocumentDBAdapter,
    TimeSeriesAdapter,
)
from .lineage import LineageTracker, LineageNode, LineageEdge, LineageGraph
from .storage_abstraction import StorageAbstraction

__all__ = [
    "StorageAdapter",
    "StorageResult",
    "QueryResult",
    "PostgreSQLAdapter",
    "VectorDBAdapter",
    "GraphDBAdapter",
    "DocumentDBAdapter",
    "TimeSeriesAdapter",
    "LineageTracker",
    "LineageNode",
    "LineageEdge",
    "LineageGraph",
    "StorageAbstraction",
]
