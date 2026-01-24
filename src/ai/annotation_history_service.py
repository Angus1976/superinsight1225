"""Annotation History and Versioning Service.

This module provides comprehensive annotation history and versioning:
- Version tracking for all annotation changes
- Change tracking with diff generation
- Rollback capability to any previous version
- Version comparison
- History timeline generation

Requirements:
- 7.4: Annotation history and versioning
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field, asdict
from enum import Enum
from copy import deepcopy


class ChangeType(str, Enum):
    """Type of change in annotation."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    RESTORED = "restored"
    MERGED = "merged"
    SPLIT = "split"


class VersionStatus(str, Enum):
    """Status of annotation version."""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ROLLED_BACK = "rolled_back"
    DELETED = "deleted"


@dataclass
class AnnotationChange:
    """Represents a single change in annotation."""
    field_name: str
    old_value: Any
    new_value: Any
    change_type: str = "modified"


@dataclass
class AnnotationVersionRecord:
    """Complete version record for an annotation."""
    version_id: UUID = field(default_factory=uuid4)
    annotation_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    version_number: int = 1
    
    # Version metadata
    created_by: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    change_type: ChangeType = ChangeType.CREATED
    change_description: str = ""
    
    # Annotation data
    annotation_data: Dict[str, Any] = field(default_factory=dict)
    
    # Change tracking
    changes: List[AnnotationChange] = field(default_factory=list)
    parent_version_id: Optional[UUID] = None
    
    # Status
    status: VersionStatus = VersionStatus.ACTIVE
    
    # AI metadata
    ai_generated: bool = False
    ai_model: Optional[str] = None
    ai_confidence: Optional[float] = None


@dataclass
class VersionDiff:
    """Difference between two versions."""
    from_version: int
    to_version: int
    changes: List[AnnotationChange] = field(default_factory=list)
    summary: str = ""


@dataclass
class HistoryTimeline:
    """Timeline of annotation history."""
    annotation_id: UUID = field(default_factory=uuid4)
    total_versions: int = 0
    current_version: int = 0
    events: List[Dict[str, Any]] = field(default_factory=list)


class AnnotationHistoryService:
    """Service for managing annotation history and versioning."""

    def __init__(self):
        """Initialize annotation history service."""
        self._versions: Dict[UUID, Dict[int, AnnotationVersionRecord]] = {}
        self._current_versions: Dict[UUID, int] = {}
        self._lock = asyncio.Lock()
        
        # Indexes
        self._tenant_index: Dict[UUID, List[UUID]] = {}
        self._user_index: Dict[UUID, List[UUID]] = {}

    async def create_version(
        self,
        annotation_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        annotation_data: Dict[str, Any],
        change_type: ChangeType = ChangeType.CREATED,
        change_description: str = "",
        ai_generated: bool = False,
        ai_model: Optional[str] = None,
        ai_confidence: Optional[float] = None
    ) -> AnnotationVersionRecord:
        """Create a new version of an annotation.

        Args:
            annotation_id: Annotation ID
            tenant_id: Tenant ID
            user_id: User creating the version
            annotation_data: Annotation data
            change_type: Type of change
            change_description: Description of changes
            ai_generated: Whether AI generated this version
            ai_model: AI model used
            ai_confidence: AI confidence score

        Returns:
            Created version record
        """
        async with self._lock:
            # Get existing versions
            if annotation_id not in self._versions:
                self._versions[annotation_id] = {}
                self._current_versions[annotation_id] = 0

            # Calculate version number
            version_number = self._current_versions[annotation_id] + 1
            
            # Get parent version for change tracking
            parent_version_id = None
            changes = []
            
            if version_number > 1:
                parent_version = self._versions[annotation_id].get(version_number - 1)
                if parent_version:
                    parent_version_id = parent_version.version_id
                    changes = self._calculate_changes(
                        parent_version.annotation_data,
                        annotation_data
                    )
                    # Mark parent as superseded
                    parent_version.status = VersionStatus.SUPERSEDED

            # Create version record
            version = AnnotationVersionRecord(
                annotation_id=annotation_id,
                tenant_id=tenant_id,
                version_number=version_number,
                created_by=user_id,
                change_type=change_type,
                change_description=change_description,
                annotation_data=deepcopy(annotation_data),
                changes=changes,
                parent_version_id=parent_version_id,
                ai_generated=ai_generated,
                ai_model=ai_model,
                ai_confidence=ai_confidence
            )

            # Store version
            self._versions[annotation_id][version_number] = version
            self._current_versions[annotation_id] = version_number

            # Update indexes
            if tenant_id not in self._tenant_index:
                self._tenant_index[tenant_id] = []
            if annotation_id not in self._tenant_index[tenant_id]:
                self._tenant_index[tenant_id].append(annotation_id)

            if user_id not in self._user_index:
                self._user_index[user_id] = []
            self._user_index[user_id].append(annotation_id)

            return version

    def _calculate_changes(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> List[AnnotationChange]:
        """Calculate changes between two annotation states.

        Args:
            old_data: Previous annotation data
            new_data: New annotation data

        Returns:
            List of changes
        """
        changes = []
        
        # Find modified and deleted fields
        for key, old_value in old_data.items():
            if key not in new_data:
                changes.append(AnnotationChange(
                    field_name=key,
                    old_value=old_value,
                    new_value=None,
                    change_type="deleted"
                ))
            elif new_data[key] != old_value:
                changes.append(AnnotationChange(
                    field_name=key,
                    old_value=old_value,
                    new_value=new_data[key],
                    change_type="modified"
                ))

        # Find added fields
        for key, new_value in new_data.items():
            if key not in old_data:
                changes.append(AnnotationChange(
                    field_name=key,
                    old_value=None,
                    new_value=new_value,
                    change_type="added"
                ))

        return changes

    async def get_version(
        self,
        annotation_id: UUID,
        version_number: int
    ) -> Optional[AnnotationVersionRecord]:
        """Get a specific version of an annotation.

        Args:
            annotation_id: Annotation ID
            version_number: Version number

        Returns:
            Version record or None
        """
        async with self._lock:
            versions = self._versions.get(annotation_id, {})
            return versions.get(version_number)

    async def get_current_version(
        self,
        annotation_id: UUID
    ) -> Optional[AnnotationVersionRecord]:
        """Get the current (latest) version of an annotation.

        Args:
            annotation_id: Annotation ID

        Returns:
            Current version record or None
        """
        async with self._lock:
            current_num = self._current_versions.get(annotation_id)
            if current_num is None:
                return None
            
            versions = self._versions.get(annotation_id, {})
            return versions.get(current_num)

    async def get_all_versions(
        self,
        annotation_id: UUID,
        include_deleted: bool = False
    ) -> List[AnnotationVersionRecord]:
        """Get all versions of an annotation.

        Args:
            annotation_id: Annotation ID
            include_deleted: Include deleted versions

        Returns:
            List of versions (newest first)
        """
        async with self._lock:
            versions = self._versions.get(annotation_id, {})
            result = list(versions.values())
            
            if not include_deleted:
                result = [v for v in result if v.status != VersionStatus.DELETED]
            
            # Sort by version number (newest first)
            result.sort(key=lambda v: v.version_number, reverse=True)
            return result

    async def rollback(
        self,
        annotation_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        target_version: int,
        reason: str = ""
    ) -> AnnotationVersionRecord:
        """Rollback annotation to a previous version.

        Args:
            annotation_id: Annotation ID
            tenant_id: Tenant ID
            user_id: User performing rollback
            target_version: Version number to rollback to
            reason: Reason for rollback

        Returns:
            New version record (restored state)

        Raises:
            ValueError: If target version doesn't exist
        """
        async with self._lock:
            # Get target version
            versions = self._versions.get(annotation_id, {})
            target = versions.get(target_version)
            
            if not target:
                raise ValueError(f"Version {target_version} not found for annotation {annotation_id}")

            # Mark current version as rolled back
            current_num = self._current_versions.get(annotation_id)
            if current_num:
                current = versions.get(current_num)
                if current:
                    current.status = VersionStatus.ROLLED_BACK

        # Create new version with restored data (outside lock to avoid deadlock)
        return await self.create_version(
            annotation_id=annotation_id,
            tenant_id=tenant_id,
            user_id=user_id,
            annotation_data=deepcopy(target.annotation_data),
            change_type=ChangeType.RESTORED,
            change_description=f"Rolled back to version {target_version}. {reason}".strip()
        )

    async def compare_versions(
        self,
        annotation_id: UUID,
        from_version: int,
        to_version: int
    ) -> VersionDiff:
        """Compare two versions of an annotation.

        Args:
            annotation_id: Annotation ID
            from_version: Source version number
            to_version: Target version number

        Returns:
            Version diff

        Raises:
            ValueError: If versions don't exist
        """
        async with self._lock:
            versions = self._versions.get(annotation_id, {})
            
            from_ver = versions.get(from_version)
            to_ver = versions.get(to_version)
            
            if not from_ver:
                raise ValueError(f"Version {from_version} not found")
            if not to_ver:
                raise ValueError(f"Version {to_version} not found")

            changes = self._calculate_changes(
                from_ver.annotation_data,
                to_ver.annotation_data
            )

            # Generate summary
            added = len([c for c in changes if c.change_type == "added"])
            modified = len([c for c in changes if c.change_type == "modified"])
            deleted = len([c for c in changes if c.change_type == "deleted"])
            
            summary = f"{added} added, {modified} modified, {deleted} deleted"

            return VersionDiff(
                from_version=from_version,
                to_version=to_version,
                changes=changes,
                summary=summary
            )

    async def get_history_timeline(
        self,
        annotation_id: UUID
    ) -> HistoryTimeline:
        """Get timeline of annotation history.

        Args:
            annotation_id: Annotation ID

        Returns:
            History timeline
        """
        async with self._lock:
            versions = self._versions.get(annotation_id, {})
            current_num = self._current_versions.get(annotation_id, 0)

            events = []
            for version in sorted(versions.values(), key=lambda v: v.version_number):
                event = {
                    "version": version.version_number,
                    "timestamp": version.created_at.isoformat(),
                    "user_id": str(version.created_by),
                    "change_type": version.change_type.value,
                    "description": version.change_description,
                    "status": version.status.value,
                    "ai_generated": version.ai_generated,
                    "changes_count": len(version.changes)
                }
                events.append(event)

            return HistoryTimeline(
                annotation_id=annotation_id,
                total_versions=len(versions),
                current_version=current_num,
                events=events
            )

    async def delete_version(
        self,
        annotation_id: UUID,
        version_number: int
    ) -> bool:
        """Soft delete a version (mark as deleted).

        Args:
            annotation_id: Annotation ID
            version_number: Version number to delete

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            versions = self._versions.get(annotation_id, {})
            version = versions.get(version_number)
            
            if not version:
                return False

            # Cannot delete current version
            if version_number == self._current_versions.get(annotation_id):
                raise ValueError("Cannot delete current version")

            version.status = VersionStatus.DELETED
            return True

    async def get_versions_by_user(
        self,
        user_id: UUID,
        limit: int = 100
    ) -> List[AnnotationVersionRecord]:
        """Get versions created by a user.

        Args:
            user_id: User ID
            limit: Maximum versions to return

        Returns:
            List of versions
        """
        async with self._lock:
            annotation_ids = self._user_index.get(user_id, [])
            
            results = []
            for ann_id in annotation_ids:
                versions = self._versions.get(ann_id, {})
                for version in versions.values():
                    if version.created_by == user_id:
                        results.append(version)

            # Sort by creation time (newest first)
            results.sort(key=lambda v: v.created_at, reverse=True)
            return results[:limit]

    async def get_versions_by_tenant(
        self,
        tenant_id: UUID,
        limit: int = 100
    ) -> List[AnnotationVersionRecord]:
        """Get versions for a tenant.

        Args:
            tenant_id: Tenant ID
            limit: Maximum versions to return

        Returns:
            List of versions
        """
        async with self._lock:
            annotation_ids = self._tenant_index.get(tenant_id, [])
            
            results = []
            for ann_id in annotation_ids:
                versions = self._versions.get(ann_id, {})
                for version in versions.values():
                    if version.tenant_id == tenant_id:
                        results.append(version)

            # Sort by creation time (newest first)
            results.sort(key=lambda v: v.created_at, reverse=True)
            return results[:limit]

    async def export_version_history(
        self,
        annotation_id: UUID,
        format: str = "json"
    ) -> str:
        """Export version history.

        Args:
            annotation_id: Annotation ID
            format: Export format ("json")

        Returns:
            Exported data as string
        """
        versions = await self.get_all_versions(annotation_id, include_deleted=True)
        
        if format == "json":
            data = []
            for version in versions:
                version_dict = {
                    "version_id": str(version.version_id),
                    "annotation_id": str(version.annotation_id),
                    "tenant_id": str(version.tenant_id),
                    "version_number": version.version_number,
                    "created_by": str(version.created_by),
                    "created_at": version.created_at.isoformat(),
                    "change_type": version.change_type.value,
                    "change_description": version.change_description,
                    "annotation_data": version.annotation_data,
                    "status": version.status.value,
                    "ai_generated": version.ai_generated,
                    "ai_model": version.ai_model,
                    "ai_confidence": version.ai_confidence,
                    "changes": [
                        {
                            "field": c.field_name,
                            "old": c.old_value,
                            "new": c.new_value,
                            "type": c.change_type
                        }
                        for c in version.changes
                    ]
                }
                data.append(version_dict)
            
            return json.dumps(data, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Global instance
_history_service: Optional[AnnotationHistoryService] = None
_history_lock = asyncio.Lock()


async def get_annotation_history_service() -> AnnotationHistoryService:
    """Get or create the global annotation history service.

    Returns:
        Annotation history service instance
    """
    global _history_service

    async with _history_lock:
        if _history_service is None:
            _history_service = AnnotationHistoryService()
        return _history_service


async def reset_annotation_history_service():
    """Reset the global annotation history service (for testing)."""
    global _history_service

    async with _history_lock:
        _history_service = None
