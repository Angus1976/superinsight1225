"""
Data Versioning Module.

Provides comprehensive data version control and management:
- Version creation and tracking
- Change tracking
- Diff calculation
- Snapshot management
- Lineage tracking
- Impact analysis
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

__all__ = [
    # Version Manager
    "VersionManager",
    "VersionType",
    "version_manager",
    # Change Tracker
    "ChangeTracker",
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
]
