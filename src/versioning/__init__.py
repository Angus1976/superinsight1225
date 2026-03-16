"""
Data Versioning Module.

Provides comprehensive data version control and management:
- Version creation and tracking
- Change tracking
- Diff calculation
- Snapshot management
- Lineage tracking
- Impact analysis

Note: This module is the primary versioning module. For backward compatibility,
src.version also re-exports the foundational models (DataVersion, DataVersionTag, etc.)
which are used by the lineage module.
"""

from src.versioning.version_manager import (
    VersionManager,
    VersionType,
    version_manager,
)
from src.versioning.change_tracker import (
    ChangeTracker,
    change_tracker,
)
from src.models.versioning import ChangeType
from src.versioning.diff_engine import (
    DiffEngine,
    DiffLevel,
    DiffResult,
    FieldChange,
    MergeResult,
    MergeConflict,
    diff_engine,
)
from src.versioning.snapshot_manager import (
    SnapshotManager,
    RestoreResult,
    RetentionPolicy,
    snapshot_manager,
)
from src.versioning.lineage_engine import (
    LineageEngine,
    LineageGraph,
    LineageNode,
    LineageEdge,
    LineagePath,
    lineage_engine,
)
from src.versioning.impact_analyzer import (
    ImpactAnalyzer,
    ImpactReport,
    EntityImpact,
    RiskLevel,
    impact_analyzer,
)

# Re-export foundational models from src.version for unified access
# This allows users to import everything from src.versioning
from src.version.models import (
    DataVersion,
    DataVersionTag,
    DataVersionBranch,
    VersionStatus,
    VersionType as DataVersionType,  # Alias to avoid conflict with local VersionType
    DataLineageRecord,
    LineageRelationType,
)
from src.version.version_manager import (
    VersionControlManager,
    version_manager as version_control_manager,  # Alias to avoid conflict
    DeltaCalculator,
)
from src.version.query_engine import (
    VersionQueryEngine,
    VersionComparison,
    version_query_engine,
)

__all__ = [
    # Version Manager (high-level operations)
    "VersionManager",
    "VersionType",
    "version_manager",
    # Change Tracker
    "ChangeTracker",
    "ChangeType",
    "change_tracker",
    # Diff Engine
    "DiffEngine",
    "DiffLevel",
    "DiffResult",
    "FieldChange",
    "MergeResult",
    "MergeConflict",
    "diff_engine",
    # Snapshot Manager
    "SnapshotManager",
    "RestoreResult",
    "RetentionPolicy",
    "snapshot_manager",
    # Lineage Engine
    "LineageEngine",
    "LineageGraph",
    "LineageNode",
    "LineageEdge",
    "LineagePath",
    "lineage_engine",
    # Impact Analyzer
    "ImpactAnalyzer",
    "ImpactReport",
    "EntityImpact",
    "RiskLevel",
    "impact_analyzer",
    # Re-exported from src.version (foundational models)
    "DataVersion",
    "DataVersionTag",
    "DataVersionBranch",
    "VersionStatus",
    "DataVersionType",
    "DataLineageRecord",
    "LineageRelationType",
    "VersionControlManager",
    "version_control_manager",
    "DeltaCalculator",
    "VersionQueryEngine",
    "VersionComparison",
    "version_query_engine",
]
