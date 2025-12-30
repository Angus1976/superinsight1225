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
from .update import (
    DataListener,
    DataChangeEvent,
    ChangeType,
    DataSource,
    VersionManager,
    GraphVersion,
    VersionDiff,
    ChangeRecord,
    IncrementalUpdater,
    UpdateResult,
    UpdateStrategy,
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
    # Update System
    "DataListener",
    "DataChangeEvent",
    "ChangeType",
    "DataSource",
    "VersionManager",
    "GraphVersion",
    "VersionDiff",
    "ChangeRecord",
    "IncrementalUpdater",
    "UpdateResult",
    "UpdateStrategy",
]

__version__ = "1.1.0"
