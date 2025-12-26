"""
Knowledge Graph Module for SuperInsight Platform.

Provides graph-based knowledge storage, entity extraction, relation mining,
and intelligent query capabilities.
"""

from .core.models import (
    Entity,
    Relation,
    EntityType,
    RelationType,
    GraphSchema,
    ExtractedEntity,
    ExtractedRelation,
)
from .core.graph_db import (
    GraphDatabase,
    get_graph_database,
)

__all__ = [
    # Models
    "Entity",
    "Relation",
    "EntityType",
    "RelationType",
    "GraphSchema",
    "ExtractedEntity",
    "ExtractedRelation",
    # Database
    "GraphDatabase",
    "get_graph_database",
]

__version__ = "1.0.0"
