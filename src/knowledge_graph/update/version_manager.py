"""
Version Manager for Knowledge Graph.

Provides version control, change tracking, and rollback capabilities
for the knowledge graph.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from ..core.models import Entity, Relation, EntityType, RelationType

logger = logging.getLogger(__name__)


class ChangeOperationType(str, Enum):
    """Types of change operations."""
    CREATE_ENTITY = "create_entity"
    UPDATE_ENTITY = "update_entity"
    DELETE_ENTITY = "delete_entity"
    CREATE_RELATION = "create_relation"
    UPDATE_RELATION = "update_relation"
    DELETE_RELATION = "delete_relation"
    MERGE_ENTITY = "merge_entity"
    SPLIT_ENTITY = "split_entity"


class VersionStatus(str, Enum):
    """Version status."""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ROLLED_BACK = "rolled_back"
    DRAFT = "draft"
    ARCHIVED = "archived"


@dataclass
class ChangeRecord:
    """
    Records a single change operation in the knowledge graph.

    Captures enough information to replay or reverse the change.
    """
    id: UUID = field(default_factory=uuid4)
    operation: ChangeOperationType = ChangeOperationType.UPDATE_ENTITY
    entity_id: Optional[UUID] = None
    relation_id: Optional[UUID] = None
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "operation": self.operation.value,
            "entity_id": str(self.entity_id) if self.entity_id else None,
            "relation_id": str(self.relation_id) if self.relation_id else None,
            "old_data": self.old_data,
            "new_data": self.new_data,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangeRecord":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            operation=ChangeOperationType(data["operation"]),
            entity_id=UUID(data["entity_id"]) if data.get("entity_id") else None,
            relation_id=UUID(data["relation_id"]) if data.get("relation_id") else None,
            old_data=data.get("old_data"),
            new_data=data.get("new_data"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            user_id=data.get("user_id"),
            tenant_id=data.get("tenant_id"),
            source=data.get("source"),
            metadata=data.get("metadata", {}),
        )

    def get_reverse_operation(self) -> "ChangeRecord":
        """Get the reverse operation for rollback."""
        reverse_ops = {
            ChangeOperationType.CREATE_ENTITY: ChangeOperationType.DELETE_ENTITY,
            ChangeOperationType.UPDATE_ENTITY: ChangeOperationType.UPDATE_ENTITY,
            ChangeOperationType.DELETE_ENTITY: ChangeOperationType.CREATE_ENTITY,
            ChangeOperationType.CREATE_RELATION: ChangeOperationType.DELETE_RELATION,
            ChangeOperationType.UPDATE_RELATION: ChangeOperationType.UPDATE_RELATION,
            ChangeOperationType.DELETE_RELATION: ChangeOperationType.CREATE_RELATION,
        }

        return ChangeRecord(
            operation=reverse_ops.get(self.operation, self.operation),
            entity_id=self.entity_id,
            relation_id=self.relation_id,
            old_data=self.new_data,
            new_data=self.old_data,
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            source=f"rollback:{self.source}",
            metadata={"original_change_id": str(self.id)},
        )


@dataclass
class GraphVersion:
    """
    Represents a version/snapshot of the knowledge graph.

    Contains metadata about the version and references to changes.
    """
    id: UUID = field(default_factory=uuid4)
    version_number: int = 1
    name: Optional[str] = None
    description: Optional[str] = None
    status: VersionStatus = VersionStatus.ACTIVE
    parent_version_id: Optional[UUID] = None
    change_records: List[ChangeRecord] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None
    tenant_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Statistics
    entities_count: int = 0
    relations_count: int = 0
    entities_added: int = 0
    entities_updated: int = 0
    entities_deleted: int = 0
    relations_added: int = 0
    relations_updated: int = 0
    relations_deleted: int = 0

    def add_change(self, change: ChangeRecord) -> None:
        """Add a change record to this version."""
        self.change_records.append(change)

        # Update statistics
        if change.operation == ChangeOperationType.CREATE_ENTITY:
            self.entities_added += 1
        elif change.operation == ChangeOperationType.UPDATE_ENTITY:
            self.entities_updated += 1
        elif change.operation == ChangeOperationType.DELETE_ENTITY:
            self.entities_deleted += 1
        elif change.operation == ChangeOperationType.CREATE_RELATION:
            self.relations_added += 1
        elif change.operation == ChangeOperationType.UPDATE_RELATION:
            self.relations_updated += 1
        elif change.operation == ChangeOperationType.DELETE_RELATION:
            self.relations_deleted += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "version_number": self.version_number,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "parent_version_id": str(self.parent_version_id) if self.parent_version_id else None,
            "change_records_count": len(self.change_records),
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "tenant_id": self.tenant_id,
            "metadata": self.metadata,
            "stats": {
                "entities_count": self.entities_count,
                "relations_count": self.relations_count,
                "entities_added": self.entities_added,
                "entities_updated": self.entities_updated,
                "entities_deleted": self.entities_deleted,
                "relations_added": self.relations_added,
                "relations_updated": self.relations_updated,
                "relations_deleted": self.relations_deleted,
            },
        }


@dataclass
class VersionDiff:
    """
    Represents the difference between two graph versions.

    Used for comparing versions and generating migration plans.
    """
    from_version_id: UUID
    to_version_id: UUID
    entities_added: List[Dict[str, Any]] = field(default_factory=list)
    entities_updated: List[Dict[str, Any]] = field(default_factory=list)
    entities_deleted: List[Dict[str, Any]] = field(default_factory=list)
    relations_added: List[Dict[str, Any]] = field(default_factory=list)
    relations_updated: List[Dict[str, Any]] = field(default_factory=list)
    relations_deleted: List[Dict[str, Any]] = field(default_factory=list)
    computed_at: datetime = field(default_factory=datetime.now)

    @property
    def total_changes(self) -> int:
        """Get total number of changes."""
        return (
            len(self.entities_added) +
            len(self.entities_updated) +
            len(self.entities_deleted) +
            len(self.relations_added) +
            len(self.relations_updated) +
            len(self.relations_deleted)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "from_version_id": str(self.from_version_id),
            "to_version_id": str(self.to_version_id),
            "entities_added": self.entities_added,
            "entities_updated": self.entities_updated,
            "entities_deleted": self.entities_deleted,
            "relations_added": self.relations_added,
            "relations_updated": self.relations_updated,
            "relations_deleted": self.relations_deleted,
            "total_changes": self.total_changes,
            "computed_at": self.computed_at.isoformat(),
        }


class VersionManager:
    """
    Manages knowledge graph versions.

    Provides version creation, comparison, and rollback capabilities.
    """

    def __init__(
        self,
        max_versions: int = 100,
        auto_create_version: bool = True,
        version_threshold: int = 100,
    ):
        """
        Initialize VersionManager.

        Args:
            max_versions: Maximum versions to keep
            auto_create_version: Auto-create new version on changes
            version_threshold: Number of changes before auto-creating version
        """
        self.max_versions = max_versions
        self.auto_create_version = auto_create_version
        self.version_threshold = version_threshold

        self._versions: Dict[UUID, GraphVersion] = {}
        self._version_history: List[UUID] = []
        self._current_version_id: Optional[UUID] = None
        self._pending_changes: List[ChangeRecord] = []
        self._lock = asyncio.Lock()

        # Initialize with first version
        self._initialize_first_version()

    def _initialize_first_version(self) -> None:
        """Initialize the first version."""
        version = GraphVersion(
            version_number=1,
            name="Initial Version",
            description="Initial knowledge graph version",
            status=VersionStatus.ACTIVE,
        )
        self._versions[version.id] = version
        self._version_history.append(version.id)
        self._current_version_id = version.id
        logger.info(f"Initialized first version: {version.id}")

    @property
    def current_version(self) -> Optional[GraphVersion]:
        """Get the current active version."""
        if self._current_version_id:
            return self._versions.get(self._current_version_id)
        return None

    async def record_change(
        self,
        operation: ChangeOperationType,
        entity_id: Optional[UUID] = None,
        relation_id: Optional[UUID] = None,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> ChangeRecord:
        """
        Record a change to the knowledge graph.

        Args:
            operation: Type of change operation
            entity_id: Entity ID (for entity operations)
            relation_id: Relation ID (for relation operations)
            old_data: Previous data state
            new_data: New data state
            user_id: User who made the change
            tenant_id: Tenant ID
            source: Source of the change

        Returns:
            The created change record
        """
        change = ChangeRecord(
            operation=operation,
            entity_id=entity_id,
            relation_id=relation_id,
            old_data=old_data,
            new_data=new_data,
            user_id=user_id,
            tenant_id=tenant_id,
            source=source,
        )

        async with self._lock:
            self._pending_changes.append(change)

            # Check if we should create a new version
            if (self.auto_create_version and
                len(self._pending_changes) >= self.version_threshold):
                await self._create_version_from_pending()

        return change

    async def create_version(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> GraphVersion:
        """
        Create a new version with pending changes.

        Args:
            name: Version name
            description: Version description
            user_id: User creating the version
            tenant_id: Tenant ID

        Returns:
            The created version
        """
        async with self._lock:
            return await self._create_version_from_pending(
                name=name,
                description=description,
                user_id=user_id,
                tenant_id=tenant_id,
            )

    async def _create_version_from_pending(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> GraphVersion:
        """Create a new version from pending changes."""
        current = self.current_version
        version_number = current.version_number + 1 if current else 1

        version = GraphVersion(
            version_number=version_number,
            name=name or f"Version {version_number}",
            description=description,
            status=VersionStatus.ACTIVE,
            parent_version_id=self._current_version_id,
            created_by=user_id,
            tenant_id=tenant_id,
        )

        # Add pending changes
        for change in self._pending_changes:
            version.add_change(change)

        # Update version counts from current
        if current:
            version.entities_count = (
                current.entities_count +
                version.entities_added -
                version.entities_deleted
            )
            version.relations_count = (
                current.relations_count +
                version.relations_added -
                version.relations_deleted
            )

        # Mark previous version as superseded
        if current:
            current.status = VersionStatus.SUPERSEDED

        # Store version
        self._versions[version.id] = version
        self._version_history.append(version.id)
        self._current_version_id = version.id
        self._pending_changes.clear()

        # Clean up old versions
        await self._cleanup_old_versions()

        logger.info(f"Created version {version.version_number} with {len(version.change_records)} changes")
        return version

    async def _cleanup_old_versions(self) -> None:
        """Remove old versions beyond the limit."""
        while len(self._version_history) > self.max_versions:
            old_version_id = self._version_history.pop(0)
            if old_version_id in self._versions:
                old_version = self._versions[old_version_id]
                old_version.status = VersionStatus.ARCHIVED
                # Optionally remove from memory
                # del self._versions[old_version_id]

    async def get_version(self, version_id: UUID) -> Optional[GraphVersion]:
        """Get a specific version."""
        return self._versions.get(version_id)

    async def get_version_by_number(self, version_number: int) -> Optional[GraphVersion]:
        """Get a version by its version number."""
        for version in self._versions.values():
            if version.version_number == version_number:
                return version
        return None

    async def list_versions(
        self,
        limit: int = 50,
        offset: int = 0,
        tenant_id: Optional[str] = None,
    ) -> List[GraphVersion]:
        """List versions with pagination."""
        versions = list(self._versions.values())

        # Filter by tenant
        if tenant_id:
            versions = [v for v in versions if v.tenant_id == tenant_id]

        # Sort by version number descending
        versions.sort(key=lambda v: v.version_number, reverse=True)

        # Apply pagination
        return versions[offset:offset + limit]

    async def diff_versions(
        self,
        from_version_id: UUID,
        to_version_id: UUID,
    ) -> VersionDiff:
        """
        Compute the difference between two versions.

        Args:
            from_version_id: Source version ID
            to_version_id: Target version ID

        Returns:
            VersionDiff containing all changes
        """
        from_version = await self.get_version(from_version_id)
        to_version = await self.get_version(to_version_id)

        if not from_version or not to_version:
            raise ValueError("One or both versions not found")

        diff = VersionDiff(
            from_version_id=from_version_id,
            to_version_id=to_version_id,
        )

        # Find all versions between from and to
        versions_between = await self._get_versions_between(from_version, to_version)

        # Aggregate changes
        for version in versions_between:
            for change in version.change_records:
                change_dict = change.to_dict()

                if change.operation == ChangeOperationType.CREATE_ENTITY:
                    diff.entities_added.append(change_dict)
                elif change.operation == ChangeOperationType.UPDATE_ENTITY:
                    diff.entities_updated.append(change_dict)
                elif change.operation == ChangeOperationType.DELETE_ENTITY:
                    diff.entities_deleted.append(change_dict)
                elif change.operation == ChangeOperationType.CREATE_RELATION:
                    diff.relations_added.append(change_dict)
                elif change.operation == ChangeOperationType.UPDATE_RELATION:
                    diff.relations_updated.append(change_dict)
                elif change.operation == ChangeOperationType.DELETE_RELATION:
                    diff.relations_deleted.append(change_dict)

        return diff

    async def _get_versions_between(
        self,
        from_version: GraphVersion,
        to_version: GraphVersion,
    ) -> List[GraphVersion]:
        """Get all versions between two versions."""
        versions = []

        # Determine direction
        if from_version.version_number < to_version.version_number:
            # Forward direction
            for vid in self._version_history:
                version = self._versions.get(vid)
                if version and from_version.version_number < version.version_number <= to_version.version_number:
                    versions.append(version)
        else:
            # Backward direction (for rollback)
            for vid in reversed(self._version_history):
                version = self._versions.get(vid)
                if version and to_version.version_number < version.version_number <= from_version.version_number:
                    versions.append(version)

        return versions

    async def rollback_to_version(
        self,
        target_version_id: UUID,
        user_id: Optional[str] = None,
    ) -> GraphVersion:
        """
        Rollback the graph to a previous version.

        Creates a new version that reverses all changes since the target.

        Args:
            target_version_id: Version to rollback to
            user_id: User performing the rollback

        Returns:
            The new version created by rollback
        """
        target_version = await self.get_version(target_version_id)
        current = self.current_version

        if not target_version or not current:
            raise ValueError("Target version or current version not found")

        if target_version.version_number >= current.version_number:
            raise ValueError("Cannot rollback to a future or current version")

        # Get changes to reverse
        diff = await self.diff_versions(target_version_id, current.id)

        async with self._lock:
            # Create rollback version
            rollback_version = GraphVersion(
                version_number=current.version_number + 1,
                name=f"Rollback to v{target_version.version_number}",
                description=f"Rolled back from v{current.version_number} to v{target_version.version_number}",
                status=VersionStatus.ACTIVE,
                parent_version_id=current.id,
                created_by=user_id,
                metadata={
                    "rollback_target": str(target_version_id),
                    "rollback_from": str(current.id),
                },
            )

            # Create reverse changes
            # Note: In production, these would need to be applied to the actual graph database
            all_changes = (
                [(c, ChangeOperationType.DELETE_ENTITY) for c in diff.entities_added] +
                [(c, ChangeOperationType.UPDATE_ENTITY) for c in diff.entities_updated] +
                [(c, ChangeOperationType.CREATE_ENTITY) for c in diff.entities_deleted] +
                [(c, ChangeOperationType.DELETE_RELATION) for c in diff.relations_added] +
                [(c, ChangeOperationType.UPDATE_RELATION) for c in diff.relations_updated] +
                [(c, ChangeOperationType.CREATE_RELATION) for c in diff.relations_deleted]
            )

            for change_data, reverse_op in all_changes:
                reverse_change = ChangeRecord(
                    operation=reverse_op,
                    entity_id=UUID(change_data["entity_id"]) if change_data.get("entity_id") else None,
                    relation_id=UUID(change_data["relation_id"]) if change_data.get("relation_id") else None,
                    old_data=change_data.get("new_data"),
                    new_data=change_data.get("old_data"),
                    user_id=user_id,
                    source="rollback",
                    metadata={"original_change_id": change_data.get("id")},
                )
                rollback_version.add_change(reverse_change)

            # Update counts
            rollback_version.entities_count = target_version.entities_count
            rollback_version.relations_count = target_version.relations_count

            # Mark current as rolled back
            current.status = VersionStatus.ROLLED_BACK

            # Store and set as current
            self._versions[rollback_version.id] = rollback_version
            self._version_history.append(rollback_version.id)
            self._current_version_id = rollback_version.id

            logger.info(f"Rolled back to version {target_version.version_number}")
            return rollback_version

    async def get_entity_history(
        self,
        entity_id: UUID,
        limit: int = 100,
    ) -> List[ChangeRecord]:
        """
        Get the change history for a specific entity.

        Args:
            entity_id: Entity ID
            limit: Maximum records to return

        Returns:
            List of change records for the entity
        """
        history = []

        for version in self._versions.values():
            for change in version.change_records:
                if change.entity_id == entity_id:
                    history.append(change)
                    if len(history) >= limit:
                        break

        # Sort by timestamp descending
        history.sort(key=lambda c: c.timestamp, reverse=True)
        return history[:limit]

    async def get_relation_history(
        self,
        relation_id: UUID,
        limit: int = 100,
    ) -> List[ChangeRecord]:
        """
        Get the change history for a specific relation.

        Args:
            relation_id: Relation ID
            limit: Maximum records to return

        Returns:
            List of change records for the relation
        """
        history = []

        for version in self._versions.values():
            for change in version.change_records:
                if change.relation_id == relation_id:
                    history.append(change)
                    if len(history) >= limit:
                        break

        history.sort(key=lambda c: c.timestamp, reverse=True)
        return history[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get version manager statistics."""
        current = self.current_version
        return {
            "total_versions": len(self._versions),
            "current_version_number": current.version_number if current else 0,
            "pending_changes": len(self._pending_changes),
            "max_versions": self.max_versions,
            "auto_create_version": self.auto_create_version,
            "version_threshold": self.version_threshold,
        }


# Global instance
_version_manager: Optional[VersionManager] = None


def get_version_manager() -> VersionManager:
    """Get or create global VersionManager instance."""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager
