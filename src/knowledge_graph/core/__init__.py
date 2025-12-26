"""
Core module for Knowledge Graph.

Provides graph database connections and data models.
"""

from .models import (
    Entity,
    Relation,
    EntityType,
    RelationType,
    GraphSchema,
    ExtractedEntity,
    ExtractedRelation,
)
from .graph_db import GraphDatabase, get_graph_database

__all__ = [
    "Entity",
    "Relation",
    "EntityType",
    "RelationType",
    "GraphSchema",
    "ExtractedEntity",
    "ExtractedRelation",
    "GraphDatabase",
    "get_graph_database",
]
