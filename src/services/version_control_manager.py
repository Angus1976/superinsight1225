"""
Version Control Manager Service for Data Lifecycle Management

Manages data versioning throughout the lifecycle with checksum verification,
version comparison, and rollback capabilities.
"""

import hashlib
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, cast, desc, String

from src.models.data_lifecycle import (
    VersionModel,
    ChangeType
)


class VersionDiff:
    """Version difference model"""
    def __init__(
        self,
        version_id1: UUID,
        version_id2: UUID,
        changes: List[Dict[str, Any]],
        summary: Dict[str, Any]
    ):
        self.version_id1 = version_id1
        self.version_id2 = version_id2
        self.changes = changes
        self.summary = summary


class VersionControlManager:
    """
    Version Control Manager for tracking data versions throughout lifecycle.
    
    Responsibilities:
    - Create version snapshots with checksums
    - Track version history
    - Support version comparison
    - Enable rollback operations
    - Manage version tags
    - Ensure version monotonicity
    
    Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
    """
    
    def __init__(self, db: Session):
        """
        Initialize the Version Control Manager.
        
        Args:
            db: Database session
        """
        self.db = db

    def _get_version_by_uuid(self, version_uuid: UUID) -> Optional[VersionModel]:
        """
        Load a version row by id.

        Compare via cast(String) so SQLite unit tests stay correct after long runs
        where PGUUID bind / compiled-cache interactions can make ``id == UUID``
        miss rows that are present.
        """
        sid = str(version_uuid)
        return (
            self.db.query(VersionModel)
            .filter(cast(VersionModel.id, String) == sid)
            .first()
        )

    def create_version(
        self,
        data_id: str,
        content: Dict[str, Any],
        change_type: ChangeType,
        created_by: str,
        description: Optional[str] = None,
        parent_version_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VersionModel:
        """
        Create a new version snapshot with checksum.
        
        Args:
            data_id: ID of the data being versioned
            content: Version content (structured data)
            change_type: Type of change (INITIAL, ANNOTATION, ENHANCEMENT, etc.)
            created_by: User ID who created this version
            description: Optional description of changes
            parent_version_id: Optional parent version ID for tracking lineage
            metadata: Additional metadata
        
        Returns:
            Created VersionModel instance
        
        Raises:
            ValueError: If required fields missing or parent version invalid
        
        Validates: Requirements 8.1, 8.5
        """
        # Validate required fields
        if not data_id:
            raise ValueError("data_id is required")
        if not content:
            raise ValueError("content is required")
        if not created_by:
            raise ValueError("created_by is required")
        
        # Validate parent version if provided
        parent_uuid = None
        if parent_version_id:
            try:
                parent_uuid = UUID(parent_version_id)
                parent_version = self._get_version_by_uuid(parent_uuid)
                if not parent_version:
                    raise ValueError(f"Parent version {parent_version_id} not found")
                if parent_version.data_id != data_id:
                    raise ValueError(
                        f"Parent version belongs to different data_id: "
                        f"{parent_version.data_id} != {data_id}"
                    )
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid parent_version_id: {e}")
        
        # Get next version number (monotonically increasing)
        latest_version = self.db.query(VersionModel).filter(
            VersionModel.data_id == data_id
        ).order_by(desc(VersionModel.version_number)).first()
        
        version_number = 1 if not latest_version else latest_version.version_number + 1
        
        # Calculate checksum (SHA-256)
        checksum = self._calculate_checksum(content)
        
        # Create version
        version = VersionModel(
            data_id=data_id,
            version_number=version_number,
            content=content,
            change_type=change_type,
            description=description,
            parent_version_id=parent_uuid,
            checksum=checksum,
            tags=[],
            created_by=created_by,
            created_at=datetime.utcnow(),
            metadata_=metadata or {}
        )
        
        self.db.add(version)
        self.db.flush()
        version_pk = version.id
        self.db.commit()
        # Re-load: refresh() can fail under SQLite when prior tests leave ORM
        # column types inconsistent across the suite.
        reloaded = self._get_version_by_uuid(version_pk)
        if reloaded is None:
            raise RuntimeError(
                f"Version row missing after insert (id={version_pk!r})"
            )
        return reloaded
    
    def get_version(self, version_id: str) -> Optional[VersionModel]:
        """
        Get a specific version by ID.
        
        Args:
            version_id: UUID of the version
        
        Returns:
            VersionModel instance or None if not found
        
        Validates: Requirements 8.2
        """
        try:
            version_uuid = UUID(version_id)
        except (ValueError, AttributeError):
            return None
        
        return self._get_version_by_uuid(version_uuid)

    
    def get_version_history(
        self,
        data_id: str,
        limit: Optional[int] = None
    ) -> List[VersionModel]:
        """
        Get version history for a data item, ordered by version number descending.
        
        Args:
            data_id: ID of the data
            limit: Optional limit on number of versions to return
        
        Returns:
            List of VersionModel instances ordered by version number (newest first)
        
        Validates: Requirements 8.2
        """
        query = self.db.query(VersionModel).filter(
            VersionModel.data_id == data_id
        ).order_by(desc(VersionModel.version_number))
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def compare_versions(
        self,
        version_id1: str,
        version_id2: str
    ) -> VersionDiff:
        """
        Compare two versions and return differences.
        
        Args:
            version_id1: UUID of first version
            version_id2: UUID of second version
        
        Returns:
            VersionDiff object with changes and summary
        
        Raises:
            ValueError: If versions not found or belong to different data items
        
        Validates: Requirements 8.3
        """
        # Get both versions
        version1 = self.get_version(version_id1)
        version2 = self.get_version(version_id2)
        
        if not version1:
            raise ValueError(f"Version {version_id1} not found")
        if not version2:
            raise ValueError(f"Version {version_id2} not found")
        
        # Validate they belong to same data item
        if version1.data_id != version2.data_id:
            raise ValueError(
                f"Versions belong to different data items: "
                f"{version1.data_id} != {version2.data_id}"
            )
        
        # Calculate differences
        changes = self._calculate_diff(version1.content, version2.content)
        
        # Generate summary
        summary = {
            'data_id': version1.data_id,
            'version1_number': version1.version_number,
            'version2_number': version2.version_number,
            'version1_created_at': version1.created_at.isoformat(),
            'version2_created_at': version2.created_at.isoformat(),
            'version1_created_by': version1.created_by,
            'version2_created_by': version2.created_by,
            'version1_change_type': version1.change_type.value,
            'version2_change_type': version2.change_type.value,
            'total_changes': len(changes),
            'checksum_match': version1.checksum == version2.checksum
        }
        
        return VersionDiff(
            version_id1=version1.id,
            version_id2=version2.id,
            changes=changes,
            summary=summary
        )
    
    def rollback_to_version(
        self,
        data_id: str,
        version_id: str,
        rolled_back_by: str,
        reason: Optional[str] = None
    ) -> VersionModel:
        """
        Rollback data to a previous version by creating a new version with old content.
        
        Args:
            data_id: ID of the data to rollback
            version_id: UUID of the version to rollback to
            rolled_back_by: User ID performing the rollback
            reason: Optional reason for rollback
        
        Returns:
            New VersionModel instance with rolled back content
        
        Raises:
            ValueError: If version not found or doesn't belong to data_id
        
        Validates: Requirements 8.4
        """
        # Get target version
        target_version = self.get_version(version_id)
        if not target_version:
            raise ValueError(f"Version {version_id} not found")
        
        # Validate version belongs to data_id
        if target_version.data_id != data_id:
            raise ValueError(
                f"Version {version_id} belongs to different data_id: "
                f"{target_version.data_id} != {data_id}"
            )
        
        # Get current latest version
        latest_version = self.db.query(VersionModel).filter(
            VersionModel.data_id == data_id
        ).order_by(desc(VersionModel.version_number)).first()
        
        # Create new version with rolled back content
        description = (
            f"Rolled back to version {target_version.version_number}. "
            f"Reason: {reason}" if reason else 
            f"Rolled back to version {target_version.version_number}"
        )
        
        new_version = self.create_version(
            data_id=data_id,
            content=target_version.content,
            change_type=ChangeType.CORRECTION,
            created_by=rolled_back_by,
            description=description,
            parent_version_id=str(latest_version.id) if latest_version else None,
            metadata={
                'rollback': True,
                'target_version_id': str(target_version.id),
                'target_version_number': target_version.version_number,
                'reason': reason
            }
        )
        
        return new_version
    
    def tag_version(
        self,
        version_id: str,
        tag: str
    ) -> VersionModel:
        """
        Add a descriptive tag to a version.
        
        Args:
            version_id: UUID of the version
            tag: Tag string to add
        
        Returns:
            Updated VersionModel instance
        
        Raises:
            ValueError: If version not found or tag is empty
        
        Validates: Requirements 8.6
        """
        if not tag or not tag.strip():
            raise ValueError("Tag cannot be empty")
        
        version = self.get_version(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")
        
        # Add tag if not already present
        if tag not in version.tags:
            version.tags = version.tags + [tag]
            vid = version.id
            self.db.commit()
            reloaded = self._get_version_by_uuid(vid)
            return reloaded if reloaded is not None else version

        return version
    
    def verify_checksum(
        self,
        version_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify the integrity of a version by recalculating its checksum.
        
        Args:
            version_id: UUID of the version
        
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if checksum matches, False otherwise
            - error_message: None if valid, error description if invalid
        
        Validates: Requirements 8.5
        """
        version = self.get_version(version_id)
        if not version:
            return False, f"Version {version_id} not found"
        
        # Recalculate checksum
        calculated_checksum = self._calculate_checksum(version.content)
        
        # Compare with stored checksum
        if calculated_checksum == version.checksum:
            return True, None
        else:
            return False, (
                f"Checksum mismatch: stored={version.checksum}, "
                f"calculated={calculated_checksum}"
            )
    
    def _calculate_checksum(self, content: Dict[str, Any]) -> str:
        """
        Calculate SHA-256 checksum for content.
        
        Args:
            content: Content dictionary to hash
        
        Returns:
            Hexadecimal checksum string
        """
        # Convert content to stable JSON string (sorted keys)
        content_json = json.dumps(content, sort_keys=True, ensure_ascii=False)
        
        # Calculate SHA-256 hash
        hash_obj = hashlib.sha256(content_json.encode('utf-8'))
        
        return hash_obj.hexdigest()
    
    def _calculate_diff(
        self,
        content1: Dict[str, Any],
        content2: Dict[str, Any],
        path: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Calculate differences between two content dictionaries.
        
        Args:
            content1: First content dictionary
            content2: Second content dictionary
            path: Current path in nested structure (for recursion)
        
        Returns:
            List of change dictionaries with type, path, old_value, new_value
        """
        changes = []
        
        # Get all keys from both dictionaries
        all_keys = set(content1.keys()) | set(content2.keys())
        
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key
            
            # Key only in content1 (removed)
            if key not in content2:
                changes.append({
                    'type': 'removed',
                    'path': current_path,
                    'old_value': content1[key],
                    'new_value': None
                })
            
            # Key only in content2 (added)
            elif key not in content1:
                changes.append({
                    'type': 'added',
                    'path': current_path,
                    'old_value': None,
                    'new_value': content2[key]
                })
            
            # Key in both - check if values differ
            else:
                value1 = content1[key]
                value2 = content2[key]
                
                # Both are dictionaries - recurse
                if isinstance(value1, dict) and isinstance(value2, dict):
                    nested_changes = self._calculate_diff(
                        value1, value2, current_path
                    )
                    changes.extend(nested_changes)
                
                # Values differ
                elif value1 != value2:
                    changes.append({
                        'type': 'modified',
                        'path': current_path,
                        'old_value': value1,
                        'new_value': value2
                    })
        
        return changes
