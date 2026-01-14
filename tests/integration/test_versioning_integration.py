"""
Integration Tests for Data Version & Lineage Module.

Tests the integration between version control, change tracking,
diff engine, and snapshot management components.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta
import json
import hashlib
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


# ============================================================================
# Mock Classes for Integration Testing
# ============================================================================

class VersionType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class ChangeType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class SnapshotType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


@dataclass
class DataVersion:
    id: str
    entity_type: str
    entity_id: str
    version: str
    version_number: int
    data: Dict[str, Any]
    message: str
    created_by: str
    created_at: datetime
    parent_version_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ChangeRecord:
    id: str
    entity_type: str
    entity_id: str
    change_type: ChangeType
    old_snapshot: Optional[Dict[str, Any]]
    new_snapshot: Optional[Dict[str, Any]]
    diff: Optional[Dict[str, Any]]
    user_id: str
    created_at: datetime


@dataclass
class Snapshot:
    id: str
    entity_type: str
    entity_id: str
    snapshot_type: SnapshotType
    data: Dict[str, Any]
    checksum: str
    created_at: datetime


class IntegratedVersioningSystem:
    """
    Integrated versioning system that combines:
    - Version Manager
    - Change Tracker
    - Diff Engine
    - Snapshot Manager
    """
    
    def __init__(self):
        self.versions: Dict[str, List[DataVersion]] = {}
        self.changes: List[ChangeRecord] = []
        self.snapshots: Dict[str, List[Snapshot]] = {}
    
    def _get_entity_key(self, entity_type: str, entity_id: str) -> str:
        return f"{entity_type}:{entity_id}"
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _calculate_next_version(self, current: str, version_type: VersionType) -> str:
        try:
            parts = current.split('.')
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
        except (ValueError, IndexError):
            major, minor, patch = 0, 0, 0
        
        if version_type == VersionType.MAJOR:
            return f"{major + 1}.0.0"
        elif version_type == VersionType.MINOR:
            return f"{major}.{minor + 1}.0"
        else:
            return f"{major}.{minor}.{patch + 1}"
    
    def _compute_diff(self, old_data: Optional[Dict], new_data: Optional[Dict]) -> Dict:
        diff = {"added": {}, "removed": {}, "modified": {}}
        
        old_data = old_data or {}
        new_data = new_data or {}
        
        old_keys = set(old_data.keys())
        new_keys = set(new_data.keys())
        
        for key in new_keys - old_keys:
            diff["added"][key] = new_data[key]
        
        for key in old_keys - new_keys:
            diff["removed"][key] = old_data[key]
        
        for key in old_keys & new_keys:
            if old_data[key] != new_data[key]:
                diff["modified"][key] = {"old": old_data[key], "new": new_data[key]}
        
        return diff
    
    def create_version(
        self,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any],
        message: str,
        user_id: str,
        version_type: VersionType = VersionType.PATCH
    ) -> DataVersion:
        """Create a new version with integrated change tracking."""
        key = self._get_entity_key(entity_type, entity_id)
        
        # Get current version
        current_versions = self.versions.get(key, [])
        current = current_versions[-1] if current_versions else None
        
        # Calculate new version
        current_ver = current.version if current else "0.0.0"
        new_version = self._calculate_next_version(current_ver, version_type)
        version_number = (current.version_number + 1) if current else 1
        
        # Create version record
        version = DataVersion(
            id=str(uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            version=new_version,
            version_number=version_number,
            data=data,
            message=message,
            created_by=user_id,
            created_at=datetime.utcnow(),
            parent_version_id=current.id if current else None,
        )
        
        # Store version
        if key not in self.versions:
            self.versions[key] = []
        self.versions[key].append(version)
        
        # Track change
        change_type = ChangeType.UPDATE if current else ChangeType.CREATE
        old_data = current.data if current else None
        diff = self._compute_diff(old_data, data)
        
        change = ChangeRecord(
            id=str(uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            change_type=change_type,
            old_snapshot=old_data,
            new_snapshot=data,
            diff=diff,
            user_id=user_id,
            created_at=datetime.utcnow(),
        )
        self.changes.append(change)
        
        return version
    
    def get_version(self, entity_type: str, entity_id: str, version: str) -> Optional[DataVersion]:
        """Get a specific version."""
        key = self._get_entity_key(entity_type, entity_id)
        versions = self.versions.get(key, [])
        
        for v in versions:
            if v.version == version:
                return v
        return None
    
    def get_version_history(self, entity_type: str, entity_id: str) -> List[DataVersion]:
        """Get version history."""
        key = self._get_entity_key(entity_type, entity_id)
        return list(reversed(self.versions.get(key, [])))
    
    def rollback(
        self,
        entity_type: str,
        entity_id: str,
        target_version: str,
        user_id: str
    ) -> DataVersion:
        """Rollback to a specific version."""
        target = self.get_version(entity_type, entity_id, target_version)
        
        if not target:
            raise ValueError(f"Version {target_version} not found")
        
        return self.create_version(
            entity_type=entity_type,
            entity_id=entity_id,
            data=target.data,
            message=f"Rollback to version {target_version}",
            user_id=user_id,
            version_type=VersionType.PATCH
        )
    
    def create_snapshot(
        self,
        entity_type: str,
        entity_id: str,
        snapshot_type: SnapshotType = SnapshotType.FULL
    ) -> Snapshot:
        """Create a snapshot of current data."""
        key = self._get_entity_key(entity_type, entity_id)
        versions = self.versions.get(key, [])
        
        if not versions:
            raise ValueError(f"No versions found for {entity_type}/{entity_id}")
        
        current = versions[-1]
        
        snapshot = Snapshot(
            id=str(uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            snapshot_type=snapshot_type,
            data=current.data,
            checksum=self._calculate_checksum(current.data),
            created_at=datetime.utcnow(),
        )
        
        if key not in self.snapshots:
            self.snapshots[key] = []
        self.snapshots[key].append(snapshot)
        
        return snapshot
    
    def restore_from_snapshot(
        self,
        snapshot_id: str,
        user_id: str
    ) -> DataVersion:
        """Restore from a snapshot."""
        # Find snapshot
        snapshot = None
        for key, snapshots in self.snapshots.items():
            for s in snapshots:
                if s.id == snapshot_id:
                    snapshot = s
                    break
            if snapshot:
                break
        
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        return self.create_version(
            entity_type=snapshot.entity_type,
            entity_id=snapshot.entity_id,
            data=snapshot.data,
            message=f"Restored from snapshot {snapshot_id}",
            user_id=user_id,
            version_type=VersionType.PATCH
        )
    
    def get_changes(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> List[ChangeRecord]:
        """Get change history."""
        result = self.changes
        
        if entity_type:
            result = [c for c in result if c.entity_type == entity_type]
        
        if entity_id:
            result = [c for c in result if c.entity_id == entity_id]
        
        return list(reversed(result))


# ============================================================================
# Integration Tests
# ============================================================================

class TestVersionCreationAndRollback:
    """Integration tests for version creation and rollback."""
    
    @pytest.fixture
    def system(self):
        return IntegratedVersioningSystem()
    
    def test_create_first_version(self, system):
        """Test creating the first version of an entity."""
        version = system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Test Task", "status": "pending"},
            message="Initial version",
            user_id="user-001"
        )
        
        assert version.version == "0.0.1"
        assert version.version_number == 1
        assert version.data["name"] == "Test Task"
        assert version.parent_version_id is None
    
    def test_create_multiple_versions(self, system):
        """Test creating multiple versions."""
        # Create first version
        v1 = system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Test Task", "status": "pending"},
            message="Initial version",
            user_id="user-001"
        )
        
        # Create second version
        v2 = system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Test Task", "status": "in_progress"},
            message="Started work",
            user_id="user-001"
        )
        
        # Create third version
        v3 = system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Test Task", "status": "completed"},
            message="Completed",
            user_id="user-001"
        )
        
        assert v1.version == "0.0.1"
        assert v2.version == "0.0.2"
        assert v3.version == "0.0.3"
        assert v2.parent_version_id == v1.id
        assert v3.parent_version_id == v2.id
    
    def test_rollback_to_previous_version(self, system):
        """Test rolling back to a previous version."""
        # Create versions
        v1 = system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Original", "value": 1},
            message="v1",
            user_id="user-001"
        )
        
        v2 = system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Modified", "value": 2},
            message="v2",
            user_id="user-001"
        )
        
        # Rollback to v1
        v3 = system.rollback(
            entity_type="task",
            entity_id="task-001",
            target_version="0.0.1",
            user_id="user-001"
        )
        
        assert v3.version == "0.0.3"
        assert v3.data == v1.data
        assert "Rollback" in v3.message
    
    def test_version_history(self, system):
        """Test getting version history."""
        # Create versions
        for i in range(5):
            system.create_version(
                entity_type="task",
                entity_id="task-001",
                data={"iteration": i},
                message=f"Version {i}",
                user_id="user-001"
            )
        
        history = system.get_version_history("task", "task-001")
        
        assert len(history) == 5
        # History should be in reverse order (newest first)
        assert history[0].version == "0.0.5"
        assert history[-1].version == "0.0.1"


class TestChangeTrackingIntegration:
    """Integration tests for change tracking."""
    
    @pytest.fixture
    def system(self):
        return IntegratedVersioningSystem()
    
    def test_changes_tracked_on_version_create(self, system):
        """Test that changes are tracked when versions are created."""
        system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Test"},
            message="Initial",
            user_id="user-001"
        )
        
        changes = system.get_changes(entity_type="task", entity_id="task-001")
        
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.CREATE
        assert changes[0].old_snapshot is None
        assert changes[0].new_snapshot == {"name": "Test"}
    
    def test_diff_computed_on_update(self, system):
        """Test that diff is computed on updates."""
        system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Test", "value": 1},
            message="v1",
            user_id="user-001"
        )
        
        system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Test", "value": 2, "new_field": "added"},
            message="v2",
            user_id="user-001"
        )
        
        changes = system.get_changes(entity_type="task", entity_id="task-001")
        
        assert len(changes) == 2
        
        # Check the update change
        update_change = changes[0]  # Most recent first
        assert update_change.change_type == ChangeType.UPDATE
        assert "value" in update_change.diff["modified"]
        assert "new_field" in update_change.diff["added"]


class TestSnapshotIntegration:
    """Integration tests for snapshot management."""
    
    @pytest.fixture
    def system(self):
        return IntegratedVersioningSystem()
    
    def test_create_and_restore_snapshot(self, system):
        """Test creating and restoring from a snapshot."""
        # Create initial version
        v1 = system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Original", "value": 100},
            message="Initial",
            user_id="user-001"
        )
        
        # Create snapshot
        snapshot = system.create_snapshot("task", "task-001")
        
        # Modify data
        v2 = system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Modified", "value": 200},
            message="Modified",
            user_id="user-001"
        )
        
        # Restore from snapshot
        v3 = system.restore_from_snapshot(snapshot.id, "user-001")
        
        assert v3.data == v1.data
        assert v3.data["value"] == 100
    
    def test_snapshot_checksum(self, system):
        """Test that snapshot checksum is calculated correctly."""
        system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"name": "Test", "value": 42},
            message="Initial",
            user_id="user-001"
        )
        
        snapshot = system.create_snapshot("task", "task-001")
        
        # Verify checksum
        expected_checksum = system._calculate_checksum({"name": "Test", "value": 42})
        assert snapshot.checksum == expected_checksum


class TestDiffIntegration:
    """Integration tests for diff computation."""
    
    @pytest.fixture
    def system(self):
        return IntegratedVersioningSystem()
    
    def test_diff_captures_all_changes(self, system):
        """Test that diff captures all types of changes."""
        system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"keep": "same", "modify": "old", "remove": "gone"},
            message="v1",
            user_id="user-001"
        )
        
        system.create_version(
            entity_type="task",
            entity_id="task-001",
            data={"keep": "same", "modify": "new", "add": "new"},
            message="v2",
            user_id="user-001"
        )
        
        changes = system.get_changes(entity_type="task", entity_id="task-001")
        diff = changes[0].diff
        
        assert "add" in diff["added"]
        assert "remove" in diff["removed"]
        assert "modify" in diff["modified"]
        assert "keep" not in diff["added"]
        assert "keep" not in diff["removed"]
        assert "keep" not in diff["modified"]


class TestCompleteWorkflow:
    """Integration tests for complete workflows."""
    
    @pytest.fixture
    def system(self):
        return IntegratedVersioningSystem()
    
    def test_complete_version_lifecycle(self, system):
        """Test a complete version lifecycle."""
        # 1. Create initial version
        v1 = system.create_version(
            entity_type="document",
            entity_id="doc-001",
            data={"title": "Draft", "content": "Initial content"},
            message="Created document",
            user_id="author-001"
        )
        
        # 2. Create snapshot for backup
        snapshot1 = system.create_snapshot("document", "doc-001")
        
        # 3. Make several edits
        v2 = system.create_version(
            entity_type="document",
            entity_id="doc-001",
            data={"title": "Draft v2", "content": "Updated content"},
            message="First revision",
            user_id="author-001"
        )
        
        v3 = system.create_version(
            entity_type="document",
            entity_id="doc-001",
            data={"title": "Final", "content": "Final content", "status": "published"},
            message="Published",
            user_id="author-001"
        )
        
        # 4. Verify version history
        history = system.get_version_history("document", "doc-001")
        assert len(history) == 3
        
        # 5. Verify change tracking
        changes = system.get_changes(entity_type="document", entity_id="doc-001")
        assert len(changes) == 3
        
        # 6. Rollback to v2
        v4 = system.rollback("document", "doc-001", "0.0.2", "author-001")
        assert v4.data["title"] == "Draft v2"
        
        # 7. Restore from original snapshot
        v5 = system.restore_from_snapshot(snapshot1.id, "author-001")
        assert v5.data["title"] == "Draft"
        
        # 8. Final history should have 5 versions
        final_history = system.get_version_history("document", "doc-001")
        assert len(final_history) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
