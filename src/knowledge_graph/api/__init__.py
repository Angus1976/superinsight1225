"""
API module for Knowledge Graph.

Provides REST API endpoints for knowledge graph operations.
"""

from .knowledge_graph_api import router as knowledge_graph_router

__all__ = [
    "knowledge_graph_router",
]
