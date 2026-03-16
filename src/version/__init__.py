"""
Data Version Control Module (Legacy).

NOTE: This module is maintained for backward compatibility.
The primary versioning module is now `src.versioning`, which re-exports
all symbols from this module plus advanced features (diff, snapshots,
change tracking, lineage graphs, impact analysis).

New code should import from `src.versioning` instead.
"""

from src.version.models import (
    DataVersion,
    DataVersionTag,
    DataVersionBranch,
    VersionStatus,
    VersionType,
    DataLineageRecord,
    LineageRelationType,
)
from src.version.version_manager import (
    VersionControlManager,
    DeltaCalculator,
    version_manager,
)
from src.version.query_engine import (
    VersionQueryEngine,
    VersionComparison,
    version_query_engine,
)

__all__ = [
    # Models
    "DataVersion",
    "DataVersionTag",
    "DataVersionBranch",
    "VersionStatus",
    "VersionType",
    # Manager
    "VersionControlManager",
    "version_manager",
    # Query Engine
    "VersionQueryEngine",
    "VersionComparison",
    "version_query_engine",
]
