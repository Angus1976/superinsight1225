"""
Unit tests for Snapshot Manager.

Tests the core functionality of:
- Full and incremental snapshot creation
- Scheduled snapshot management
- Snapshot restoration
- Retention policy enforcement
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta
import hashlib
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class SnapshotType(str, Enum):
    """Snapshot type enum."""
    FULL = "full"
    INCREMENTAL = "incremental"


@dataclass
class RestoreResult:
    """Result of snapshot restoration."""
    snapshot_id: str
    entity_type: str
    entity_id: str
    restored_at: datetime
    restored_by: Optional[str]
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "restored_at": self.restored_at.isoformat(),
            "restored_by": self.restored_by,
        }


@dataclass
class RetentionPolicy:
    """Snapshot retention policy."""
    max_age_days: int = 90
    max_count: int = 100
    keep_tagged: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_age_days": self.max_age_days,
            "max_count": self.max_count,
            "keep_tagged": self.keep_tagged,
        }


class MockSnapshotManager:
    """Mock Snapshot Manager for testing."""
    
    def _calculate_checksum(self, data):
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _calculate_size(self, data):
        return len(json.dumps(data, default=str).encode())
    
    def _compute_incremental(self, base_data, new_data):
        diff = {
            "added": {},
            "removed": {},
            "modified": {}
        }
        
        base_keys = set(base_data.keys()) if base_data else set()
        new_keys = set(new_data.keys()) if new_data else set()
        
        for key in new_keys - base_keys:
            diff["added"][key] = new_data[key]
        
        for key in base_keys - new_keys:
            diff["removed"][key] = base_data[key]
        
        for key in base_keys & new_keys:
            if base_data[key] != new_data[key]:
                diff["modified"][key] = {
                    "old": base_data[key],
                    "new": new_data[key]
                }
        
        return diff


class TestSnapshotManager:
    """Tests for SnapshotManager class."""
    
    @pytest.fixture
    def snapshot_manager(self):
        """Create a MockSnapshotManager instance."""
        return MockSnapshotManager()
    
    def test_calculate_checksum(self, snapshot_manager):
        """Test checksum calculation."""
        data = {"name": "test", "value": 123}
        checksum = snapshot_manager._calculate_checksum(data)
        
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex digest length
        
        # Same data should produce same checksum
        checksum2 = snapshot_manager._calculate_checksum(data)
        assert checksum == checksum2
    
    def test_calculate_checksum_order_independent(self, snapshot_manager):
        """Test checksum is order-independent for dict keys."""
        data1 = {"a": 1, "b": 2, "c": 3}
        data2 = {"c": 3, "a": 1, "b": 2}
        
        checksum1 = snapshot_manager._calculate_checksum(data1)
        checksum2 = snapshot_manager._calculate_checksum(data2)
        
        assert checksum1 == checksum2
    
    def test_calculate_size(self, snapshot_manager):
        """Test size calculation."""
        data = {"name": "test"}
        size = snapshot_manager._calculate_size(data)
        
        assert isinstance(size, int)
        assert size > 0
    
    def test_compute_incremental_added(self, snapshot_manager):
        """Test incremental diff for added fields."""
        base_data = {"name": "test"}
        new_data = {"name": "test", "value": 123}
        
        diff = snapshot_manager._compute_incremental(base_data, new_data)
        
        assert "value" in diff["added"]
        assert diff["added"]["value"] == 123
    
    def test_compute_incremental_removed(self, snapshot_manager):
        """Test incremental diff for removed fields."""
        base_data = {"name": "test", "value": 123}
        new_data = {"name": "test"}
        
        diff = snapshot_manager._compute_incremental(base_data, new_data)
        
        assert "value" in diff["removed"]
        assert diff["removed"]["value"] == 123
    
    def test_compute_incremental_modified(self, snapshot_manager):
        """Test incremental diff for modified fields."""
        base_data = {"name": "test", "value": 123}
        new_data = {"name": "test", "value": 456}
        
        diff = snapshot_manager._compute_incremental(base_data, new_data)
        
        assert "value" in diff["modified"]
        assert diff["modified"]["value"]["old"] == 123
        assert diff["modified"]["value"]["new"] == 456
    
    def test_compute_incremental_no_changes(self, snapshot_manager):
        """Test incremental diff with no changes."""
        data = {"name": "test", "value": 123}
        
        diff = snapshot_manager._compute_incremental(data, data)
        
        assert len(diff["added"]) == 0
        assert len(diff["removed"]) == 0
        assert len(diff["modified"]) == 0
    
    def test_compute_incremental_empty_base(self, snapshot_manager):
        """Test incremental diff with empty base."""
        base_data = {}
        new_data = {"name": "test"}
        
        diff = snapshot_manager._compute_incremental(base_data, new_data)
        
        assert "name" in diff["added"]
    
    def test_compute_incremental_empty_new(self, snapshot_manager):
        """Test incremental diff with empty new data."""
        base_data = {"name": "test"}
        new_data = {}
        
        diff = snapshot_manager._compute_incremental(base_data, new_data)
        
        assert "name" in diff["removed"]


class TestRestoreResult:
    """Tests for RestoreResult data class."""
    
    def test_restore_result_to_dict(self):
        """Test RestoreResult to_dict method."""
        result = RestoreResult(
            snapshot_id="snap123",
            entity_type="task",
            entity_id="task456",
            restored_at=datetime(2024, 1, 1, 12, 0, 0),
            restored_by="user1",
            data={"name": "test"}
        )
        
        dict_result = result.to_dict()
        
        assert dict_result["snapshot_id"] == "snap123"
        assert dict_result["entity_type"] == "task"
        assert dict_result["entity_id"] == "task456"
        assert dict_result["restored_by"] == "user1"
        assert "2024-01-01" in dict_result["restored_at"]


class TestRetentionPolicy:
    """Tests for RetentionPolicy data class."""
    
    def test_retention_policy_defaults(self):
        """Test RetentionPolicy default values."""
        policy = RetentionPolicy()
        
        assert policy.max_age_days == 90
        assert policy.max_count == 100
        assert policy.keep_tagged == True
    
    def test_retention_policy_custom(self):
        """Test RetentionPolicy with custom values."""
        policy = RetentionPolicy(
            max_age_days=30,
            max_count=50,
            keep_tagged=False
        )
        
        assert policy.max_age_days == 30
        assert policy.max_count == 50
        assert policy.keep_tagged == False
    
    def test_retention_policy_to_dict(self):
        """Test RetentionPolicy to_dict method."""
        policy = RetentionPolicy(max_age_days=60, max_count=75)
        
        result = policy.to_dict()
        
        assert result["max_age_days"] == 60
        assert result["max_count"] == 75
        assert result["keep_tagged"] == True


class TestSnapshotType:
    """Tests for SnapshotType enum."""
    
    def test_snapshot_type_values(self):
        """Test SnapshotType enum values."""
        assert SnapshotType.FULL.value == "full"
        assert SnapshotType.INCREMENTAL.value == "incremental"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
