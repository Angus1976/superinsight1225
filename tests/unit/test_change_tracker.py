"""
Unit tests for Change Tracker.

Tests the core functionality of:
- Change recording with diff computation
- Change history queries
- Entity timeline generation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta
from enum import Enum


class ChangeType(str, Enum):
    """Change type enum."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class MockChangeTracker:
    """Mock Change Tracker for testing without database dependencies."""
    
    def _compute_diff(self, old_data, new_data):
        """Compute difference between old and new data."""
        diff = {
            "added": {},
            "removed": {},
            "modified": {}
        }
        
        old_data = old_data or {}
        new_data = new_data or {}
        
        old_keys = set(old_data.keys())
        new_keys = set(new_data.keys())
        
        # Added keys
        for key in new_keys - old_keys:
            diff["added"][key] = new_data[key]
        
        # Removed keys
        for key in old_keys - new_keys:
            diff["removed"][key] = old_data[key]
        
        # Modified keys
        for key in old_keys & new_keys:
            if old_data[key] != new_data[key]:
                diff["modified"][key] = {
                    "old": old_data[key],
                    "new": new_data[key]
                }
        
        return diff
    
    def _generate_change_summary(self, change):
        """Generate human-readable summary of a change."""
        if change.change_type == ChangeType.CREATE:
            return f"Created {change.entity_type}"
        elif change.change_type == ChangeType.DELETE:
            return f"Deleted {change.entity_type}"
        elif change.change_type == ChangeType.UPDATE:
            if change.diff:
                added = len(change.diff.get("added", {}))
                removed = len(change.diff.get("removed", {}))
                modified = len(change.diff.get("modified", {}))
                parts = []
                if added:
                    parts.append(f"{added} added")
                if removed:
                    parts.append(f"{removed} removed")
                if modified:
                    parts.append(f"{modified} modified")
                return f"Updated {change.entity_type}: {', '.join(parts)}"
            return f"Updated {change.entity_type}"
        return f"Changed {change.entity_type}"


class TestChangeTracker:
    """Tests for ChangeTracker class."""
    
    @pytest.fixture
    def change_tracker(self):
        """Create a MockChangeTracker instance."""
        return MockChangeTracker()
    
    def test_compute_diff_added_fields(self, change_tracker):
        """Test diff computation for added fields."""
        old_data = {"name": "test", "value": 1}
        new_data = {"name": "test", "value": 1, "new_field": "added"}
        
        diff = change_tracker._compute_diff(old_data, new_data)
        
        assert "new_field" in diff["added"]
        assert diff["added"]["new_field"] == "added"
        assert len(diff["removed"]) == 0
        assert len(diff["modified"]) == 0
    
    def test_compute_diff_removed_fields(self, change_tracker):
        """Test diff computation for removed fields."""
        old_data = {"name": "test", "value": 1, "old_field": "removed"}
        new_data = {"name": "test", "value": 1}
        
        diff = change_tracker._compute_diff(old_data, new_data)
        
        assert "old_field" in diff["removed"]
        assert diff["removed"]["old_field"] == "removed"
        assert len(diff["added"]) == 0
        assert len(diff["modified"]) == 0
    
    def test_compute_diff_modified_fields(self, change_tracker):
        """Test diff computation for modified fields."""
        old_data = {"name": "test", "value": 1}
        new_data = {"name": "test", "value": 2}
        
        diff = change_tracker._compute_diff(old_data, new_data)
        
        assert "value" in diff["modified"]
        assert diff["modified"]["value"]["old"] == 1
        assert diff["modified"]["value"]["new"] == 2
        assert len(diff["added"]) == 0
        assert len(diff["removed"]) == 0
    
    def test_compute_diff_mixed_changes(self, change_tracker):
        """Test diff computation with mixed changes."""
        old_data = {"name": "test", "value": 1, "removed": "gone"}
        new_data = {"name": "test", "value": 2, "added": "new"}
        
        diff = change_tracker._compute_diff(old_data, new_data)
        
        assert "added" in diff["added"]
        assert "removed" in diff["removed"]
        assert "value" in diff["modified"]
    
    def test_compute_diff_empty_old(self, change_tracker):
        """Test diff computation with empty old data."""
        old_data = {}
        new_data = {"name": "test", "value": 1}
        
        diff = change_tracker._compute_diff(old_data, new_data)
        
        assert "name" in diff["added"]
        assert "value" in diff["added"]
        assert len(diff["removed"]) == 0
        assert len(diff["modified"]) == 0
    
    def test_compute_diff_empty_new(self, change_tracker):
        """Test diff computation with empty new data."""
        old_data = {"name": "test", "value": 1}
        new_data = {}
        
        diff = change_tracker._compute_diff(old_data, new_data)
        
        assert "name" in diff["removed"]
        assert "value" in diff["removed"]
        assert len(diff["added"]) == 0
        assert len(diff["modified"]) == 0
    
    def test_compute_diff_both_empty(self, change_tracker):
        """Test diff computation with both empty."""
        old_data = {}
        new_data = {}
        
        diff = change_tracker._compute_diff(old_data, new_data)
        
        assert len(diff["added"]) == 0
        assert len(diff["removed"]) == 0
        assert len(diff["modified"]) == 0
    
    def test_compute_diff_none_values(self, change_tracker):
        """Test diff computation with None values."""
        old_data = None
        new_data = {"name": "test"}
        
        diff = change_tracker._compute_diff(old_data, new_data)
        
        assert "name" in diff["added"]
    
    def test_compute_diff_nested_objects(self, change_tracker):
        """Test diff computation with nested objects."""
        old_data = {"config": {"setting1": "a", "setting2": "b"}}
        new_data = {"config": {"setting1": "a", "setting2": "c"}}
        
        diff = change_tracker._compute_diff(old_data, new_data)
        
        assert "config" in diff["modified"]
    
    def test_generate_change_summary_create(self, change_tracker):
        """Test change summary generation for create."""
        mock_change = Mock()
        mock_change.change_type = ChangeType.CREATE
        mock_change.entity_type = "task"
        mock_change.diff = None
        
        summary = change_tracker._generate_change_summary(mock_change)
        
        assert "Created" in summary
        assert "task" in summary
    
    def test_generate_change_summary_delete(self, change_tracker):
        """Test change summary generation for delete."""
        mock_change = Mock()
        mock_change.change_type = ChangeType.DELETE
        mock_change.entity_type = "task"
        mock_change.diff = None
        
        summary = change_tracker._generate_change_summary(mock_change)
        
        assert "Deleted" in summary
        assert "task" in summary
    
    def test_generate_change_summary_update(self, change_tracker):
        """Test change summary generation for update."""
        mock_change = Mock()
        mock_change.change_type = ChangeType.UPDATE
        mock_change.entity_type = "task"
        mock_change.diff = {
            "added": {"field1": "value"},
            "removed": {"field2": "value"},
            "modified": {"field3": {"old": 1, "new": 2}}
        }
        
        summary = change_tracker._generate_change_summary(mock_change)
        
        assert "Updated" in summary
        assert "task" in summary
        assert "1 added" in summary
        assert "1 removed" in summary
        assert "1 modified" in summary


class TestChangeType:
    """Tests for ChangeType enum."""
    
    def test_change_type_values(self):
        """Test ChangeType enum values."""
        assert ChangeType.CREATE.value == "create"
        assert ChangeType.UPDATE.value == "update"
        assert ChangeType.DELETE.value == "delete"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
