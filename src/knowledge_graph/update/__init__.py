"""
Knowledge Graph Update Module.

Provides data listening, incremental updates, and version management
for the knowledge graph system.
"""

from .data_listener import (
    DataListener,
    DataChangeEvent,
    ChangeType,
    DataSource,
)
from .version_manager import (
    VersionManager,
    GraphVersion,
    VersionDiff,
    ChangeRecord,
)
from .incremental_updater import (
    IncrementalUpdater,
    UpdateResult,
    UpdateStrategy,
)

__all__ = [
    # Data Listener
    "DataListener",
    "DataChangeEvent",
    "ChangeType",
    "DataSource",
    # Version Manager
    "VersionManager",
    "GraphVersion",
    "VersionDiff",
    "ChangeRecord",
    # Incremental Updater
    "IncrementalUpdater",
    "UpdateResult",
    "UpdateStrategy",
]
