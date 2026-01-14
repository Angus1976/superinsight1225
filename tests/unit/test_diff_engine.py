"""
Unit tests for Diff Engine.

Tests the core functionality of:
- Field-level and line-level diff
- Three-way merge with conflict detection
- Conflict resolution
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json
import difflib
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


class DiffLevel(str, Enum):
    """Diff granularity level."""
    FIELD = "field"
    LINE = "line"


@dataclass
class FieldChange:
    """Represents a single field change."""
    field: str
    change_type: str
    old_value: Any = None
    new_value: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "change_type": self.change_type,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }


@dataclass
class DiffSummary:
    """Summary of differences."""
    added: int = 0
    removed: int = 0
    modified: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        return {
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
        }


@dataclass
class DiffResult:
    """Result of diff computation."""
    diff_level: DiffLevel
    changes: List[FieldChange] = field(default_factory=list)
    unified_diff: List[str] = field(default_factory=list)
    summary: DiffSummary = field(default_factory=DiffSummary)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "diff_level": self.diff_level.value,
            "changes": [c.to_dict() for c in self.changes],
            "unified_diff": self.unified_diff,
            "summary": self.summary.to_dict(),
        }


@dataclass
class MergeConflict:
    """Represents a merge conflict."""
    field: str
    base_value: Any
    ours_value: Any
    theirs_value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "base_value": self.base_value,
            "ours_value": self.ours_value,
            "theirs_value": self.theirs_value,
        }


@dataclass
class MergeResult:
    """Result of three-way merge."""
    merged: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[MergeConflict] = field(default_factory=list)
    has_conflicts: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "merged": self.merged,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "has_conflicts": self.has_conflicts,
        }


class DiffEngine:
    """Diff Engine for computing version differences."""
    
    def compute_diff(self, old_data, new_data, diff_level=DiffLevel.FIELD):
        if diff_level == DiffLevel.LINE:
            return self._line_diff(old_data, new_data)
        else:
            return self._field_diff(old_data, new_data)
    
    def _field_diff(self, old_data, new_data):
        changes = []
        old_data = old_data or {}
        new_data = new_data or {}
        
        old_keys = set(old_data.keys())
        new_keys = set(new_data.keys())
        
        for key in new_keys - old_keys:
            changes.append(FieldChange(field=key, change_type="added", new_value=new_data[key]))
        
        for key in old_keys - new_keys:
            changes.append(FieldChange(field=key, change_type="removed", old_value=old_data[key]))
        
        for key in old_keys & new_keys:
            if old_data[key] != new_data[key]:
                changes.append(FieldChange(
                    field=key, change_type="modified",
                    old_value=old_data[key], new_value=new_data[key]
                ))
        
        summary = DiffSummary(
            added=sum(1 for c in changes if c.change_type == "added"),
            removed=sum(1 for c in changes if c.change_type == "removed"),
            modified=sum(1 for c in changes if c.change_type == "modified")
        )
        
        return DiffResult(diff_level=DiffLevel.FIELD, changes=changes, summary=summary)
    
    def _line_diff(self, old_data, new_data):
        old_lines = json.dumps(old_data or {}, indent=2, sort_keys=True).splitlines()
        new_lines = json.dumps(new_data or {}, indent=2, sort_keys=True).splitlines()
        
        differ = difflib.unified_diff(old_lines, new_lines, fromfile='old', tofile='new', lineterm='')
        unified_diff = list(differ)
        
        return DiffResult(diff_level=DiffLevel.LINE, unified_diff=unified_diff, summary=DiffSummary())
    
    def three_way_merge(self, base, ours, theirs):
        merged = {}
        conflicts = []
        
        base = base or {}
        ours = ours or {}
        theirs = theirs or {}
        
        all_keys = set(base.keys()) | set(ours.keys()) | set(theirs.keys())
        
        for key in all_keys:
            base_val = base.get(key)
            ours_val = ours.get(key)
            theirs_val = theirs.get(key)
            
            if ours_val == theirs_val:
                if ours_val is not None:
                    merged[key] = ours_val
                continue
            
            if ours_val != base_val and theirs_val == base_val:
                if ours_val is not None:
                    merged[key] = ours_val
                continue
            
            if theirs_val != base_val and ours_val == base_val:
                if theirs_val is not None:
                    merged[key] = theirs_val
                continue
            
            if ours_val != base_val and theirs_val != base_val:
                conflicts.append(MergeConflict(
                    field=key, base_value=base_val,
                    ours_value=ours_val, theirs_value=theirs_val
                ))
                if ours_val is not None:
                    merged[key] = ours_val
                elif theirs_val is not None:
                    merged[key] = theirs_val
        
        return MergeResult(merged=merged, conflicts=conflicts, has_conflicts=len(conflicts) > 0)
    
    def resolve_conflict(self, merge_result, field, resolution, custom_value=None):
        conflict = None
        remaining_conflicts = []
        
        for c in merge_result.conflicts:
            if c.field == field:
                conflict = c
            else:
                remaining_conflicts.append(c)
        
        if not conflict:
            return merge_result
        
        new_merged = dict(merge_result.merged)
        
        if resolution == "ours":
            if conflict.ours_value is not None:
                new_merged[field] = conflict.ours_value
            else:
                new_merged.pop(field, None)
        elif resolution == "theirs":
            if conflict.theirs_value is not None:
                new_merged[field] = conflict.theirs_value
            else:
                new_merged.pop(field, None)
        elif resolution == "base":
            if conflict.base_value is not None:
                new_merged[field] = conflict.base_value
            else:
                new_merged.pop(field, None)
        elif resolution == "custom":
            if custom_value is not None:
                new_merged[field] = custom_value
            else:
                new_merged.pop(field, None)
        
        return MergeResult(merged=new_merged, conflicts=remaining_conflicts, has_conflicts=len(remaining_conflicts) > 0)
    
    def resolve_all_conflicts(self, merge_result, strategy="ours"):
        result = merge_result
        for conflict in list(merge_result.conflicts):
            result = self.resolve_conflict(result, conflict.field, strategy)
        return result
    
    def compute_patch(self, old_data, new_data):
        diff = self._field_diff(old_data, new_data)
        patch = {"operations": []}
        
        for change in diff.changes:
            if change.change_type == "added":
                patch["operations"].append({"op": "add", "path": change.field, "value": change.new_value})
            elif change.change_type == "removed":
                patch["operations"].append({"op": "remove", "path": change.field})
            elif change.change_type == "modified":
                patch["operations"].append({"op": "replace", "path": change.field, "value": change.new_value})
        
        return patch
    
    def apply_patch(self, data, patch):
        result = dict(data) if data else {}
        
        for op in patch.get("operations", []):
            path = op.get("path")
            if op["op"] == "add":
                result[path] = op["value"]
            elif op["op"] == "remove":
                result.pop(path, None)
            elif op["op"] == "replace":
                result[path] = op["value"]
        
        return result


class TestDiffEngine:
    """Tests for DiffEngine class."""
    
    @pytest.fixture
    def diff_engine(self):
        """Create a DiffEngine instance."""
        return DiffEngine()
    
    def test_field_diff_added(self, diff_engine):
        """Test field diff for added fields."""
        old_data = {"name": "test"}
        new_data = {"name": "test", "value": 123}
        
        result = diff_engine.compute_diff(old_data, new_data, DiffLevel.FIELD)
        
        assert result.diff_level == DiffLevel.FIELD
        assert len(result.changes) == 1
        assert result.changes[0].field == "value"
        assert result.changes[0].change_type == "added"
        assert result.changes[0].new_value == 123
        assert result.summary.added == 1
    
    def test_field_diff_removed(self, diff_engine):
        """Test field diff for removed fields."""
        old_data = {"name": "test", "value": 123}
        new_data = {"name": "test"}
        
        result = diff_engine.compute_diff(old_data, new_data, DiffLevel.FIELD)
        
        assert len(result.changes) == 1
        assert result.changes[0].field == "value"
        assert result.changes[0].change_type == "removed"
        assert result.changes[0].old_value == 123
        assert result.summary.removed == 1
    
    def test_field_diff_modified(self, diff_engine):
        """Test field diff for modified fields."""
        old_data = {"name": "test", "value": 123}
        new_data = {"name": "test", "value": 456}
        
        result = diff_engine.compute_diff(old_data, new_data, DiffLevel.FIELD)
        
        assert len(result.changes) == 1
        assert result.changes[0].field == "value"
        assert result.changes[0].change_type == "modified"
        assert result.changes[0].old_value == 123
        assert result.changes[0].new_value == 456
        assert result.summary.modified == 1
    
    def test_field_diff_no_changes(self, diff_engine):
        """Test field diff with no changes."""
        data = {"name": "test", "value": 123}
        
        result = diff_engine.compute_diff(data, data, DiffLevel.FIELD)
        
        assert len(result.changes) == 0
        assert result.summary.added == 0
        assert result.summary.removed == 0
        assert result.summary.modified == 0
    
    def test_field_diff_empty_data(self, diff_engine):
        """Test field diff with empty data."""
        result = diff_engine.compute_diff({}, {}, DiffLevel.FIELD)
        
        assert len(result.changes) == 0
    
    def test_field_diff_nested_objects(self, diff_engine):
        """Test field diff with nested objects."""
        old_data = {"config": {"a": 1, "b": 2}}
        new_data = {"config": {"a": 1, "b": 3}}
        
        result = diff_engine.compute_diff(old_data, new_data, DiffLevel.FIELD)
        
        assert len(result.changes) == 1
        assert result.changes[0].field == "config"
        assert result.changes[0].change_type == "modified"
    
    def test_line_diff(self, diff_engine):
        """Test line-level diff."""
        old_data = {"name": "test", "value": 123}
        new_data = {"name": "test", "value": 456}
        
        result = diff_engine.compute_diff(old_data, new_data, DiffLevel.LINE)
        
        assert result.diff_level == DiffLevel.LINE
        assert len(result.unified_diff) > 0
    
    def test_three_way_merge_no_conflicts(self, diff_engine):
        """Test three-way merge without conflicts."""
        base = {"name": "test", "value": 1}
        ours = {"name": "test", "value": 1, "added_by_us": "a"}
        theirs = {"name": "test", "value": 1, "added_by_them": "b"}
        
        result = diff_engine.three_way_merge(base, ours, theirs)
        
        assert not result.has_conflicts
        assert len(result.conflicts) == 0
        assert result.merged["name"] == "test"
        assert result.merged["value"] == 1
        assert result.merged["added_by_us"] == "a"
        assert result.merged["added_by_them"] == "b"
    
    def test_three_way_merge_with_conflicts(self, diff_engine):
        """Test three-way merge with conflicts."""
        base = {"name": "test", "value": 1}
        ours = {"name": "test", "value": 2}
        theirs = {"name": "test", "value": 3}
        
        result = diff_engine.three_way_merge(base, ours, theirs)
        
        assert result.has_conflicts
        assert len(result.conflicts) == 1
        assert result.conflicts[0].field == "value"
        assert result.conflicts[0].base_value == 1
        assert result.conflicts[0].ours_value == 2
        assert result.conflicts[0].theirs_value == 3
    
    def test_three_way_merge_same_change(self, diff_engine):
        """Test three-way merge when both sides make same change."""
        base = {"name": "test", "value": 1}
        ours = {"name": "test", "value": 2}
        theirs = {"name": "test", "value": 2}
        
        result = diff_engine.three_way_merge(base, ours, theirs)
        
        assert not result.has_conflicts
        assert result.merged["value"] == 2
    
    def test_three_way_merge_only_ours_changed(self, diff_engine):
        """Test three-way merge when only ours changed."""
        base = {"name": "test", "value": 1}
        ours = {"name": "test", "value": 2}
        theirs = {"name": "test", "value": 1}
        
        result = diff_engine.three_way_merge(base, ours, theirs)
        
        assert not result.has_conflicts
        assert result.merged["value"] == 2
    
    def test_three_way_merge_only_theirs_changed(self, diff_engine):
        """Test three-way merge when only theirs changed."""
        base = {"name": "test", "value": 1}
        ours = {"name": "test", "value": 1}
        theirs = {"name": "test", "value": 2}
        
        result = diff_engine.three_way_merge(base, ours, theirs)
        
        assert not result.has_conflicts
        assert result.merged["value"] == 2
    
    def test_resolve_conflict_ours(self, diff_engine):
        """Test conflict resolution with 'ours' strategy."""
        merge_result = MergeResult(
            merged={"value": 2},
            conflicts=[MergeConflict(
                field="value",
                base_value=1,
                ours_value=2,
                theirs_value=3
            )],
            has_conflicts=True
        )
        
        result = diff_engine.resolve_conflict(merge_result, "value", "ours")
        
        assert not result.has_conflicts
        assert result.merged["value"] == 2
    
    def test_resolve_conflict_theirs(self, diff_engine):
        """Test conflict resolution with 'theirs' strategy."""
        merge_result = MergeResult(
            merged={"value": 2},
            conflicts=[MergeConflict(
                field="value",
                base_value=1,
                ours_value=2,
                theirs_value=3
            )],
            has_conflicts=True
        )
        
        result = diff_engine.resolve_conflict(merge_result, "value", "theirs")
        
        assert not result.has_conflicts
        assert result.merged["value"] == 3
    
    def test_resolve_conflict_base(self, diff_engine):
        """Test conflict resolution with 'base' strategy."""
        merge_result = MergeResult(
            merged={"value": 2},
            conflicts=[MergeConflict(
                field="value",
                base_value=1,
                ours_value=2,
                theirs_value=3
            )],
            has_conflicts=True
        )
        
        result = diff_engine.resolve_conflict(merge_result, "value", "base")
        
        assert not result.has_conflicts
        assert result.merged["value"] == 1
    
    def test_resolve_conflict_custom(self, diff_engine):
        """Test conflict resolution with custom value."""
        merge_result = MergeResult(
            merged={"value": 2},
            conflicts=[MergeConflict(
                field="value",
                base_value=1,
                ours_value=2,
                theirs_value=3
            )],
            has_conflicts=True
        )
        
        result = diff_engine.resolve_conflict(
            merge_result, "value", "custom", custom_value=100
        )
        
        assert not result.has_conflicts
        assert result.merged["value"] == 100
    
    def test_resolve_all_conflicts(self, diff_engine):
        """Test resolving all conflicts with single strategy."""
        merge_result = MergeResult(
            merged={"a": 1, "b": 2},
            conflicts=[
                MergeConflict(field="a", base_value=0, ours_value=1, theirs_value=10),
                MergeConflict(field="b", base_value=0, ours_value=2, theirs_value=20),
            ],
            has_conflicts=True
        )
        
        result = diff_engine.resolve_all_conflicts(merge_result, "theirs")
        
        assert not result.has_conflicts
        assert result.merged["a"] == 10
        assert result.merged["b"] == 20
    
    def test_compute_patch(self, diff_engine):
        """Test patch computation."""
        old_data = {"name": "test", "value": 1}
        new_data = {"name": "test", "value": 2, "added": "new"}
        
        patch = diff_engine.compute_patch(old_data, new_data)
        
        assert "operations" in patch
        assert len(patch["operations"]) == 2
    
    def test_apply_patch(self, diff_engine):
        """Test patch application."""
        data = {"name": "test", "value": 1}
        patch = {
            "operations": [
                {"op": "replace", "path": "value", "value": 2},
                {"op": "add", "path": "added", "value": "new"},
            ]
        }
        
        result = diff_engine.apply_patch(data, patch)
        
        assert result["name"] == "test"
        assert result["value"] == 2
        assert result["added"] == "new"


class TestDiffDataClasses:
    """Tests for diff data classes."""
    
    def test_field_change_to_dict(self):
        """Test FieldChange to_dict method."""
        change = FieldChange(
            field="value",
            change_type="modified",
            old_value=1,
            new_value=2
        )
        
        result = change.to_dict()
        
        assert result["field"] == "value"
        assert result["change_type"] == "modified"
        assert result["old_value"] == 1
        assert result["new_value"] == 2
    
    def test_diff_summary_to_dict(self):
        """Test DiffSummary to_dict method."""
        summary = DiffSummary(added=1, removed=2, modified=3)
        
        result = summary.to_dict()
        
        assert result["added"] == 1
        assert result["removed"] == 2
        assert result["modified"] == 3
    
    def test_diff_result_to_dict(self):
        """Test DiffResult to_dict method."""
        result = DiffResult(
            diff_level=DiffLevel.FIELD,
            changes=[FieldChange(field="test", change_type="added", new_value=1)],
            summary=DiffSummary(added=1)
        )
        
        dict_result = result.to_dict()
        
        assert dict_result["diff_level"] == "field"
        assert len(dict_result["changes"]) == 1
        assert dict_result["summary"]["added"] == 1
    
    def test_merge_conflict_to_dict(self):
        """Test MergeConflict to_dict method."""
        conflict = MergeConflict(
            field="value",
            base_value=1,
            ours_value=2,
            theirs_value=3
        )
        
        result = conflict.to_dict()
        
        assert result["field"] == "value"
        assert result["base_value"] == 1
        assert result["ours_value"] == 2
        assert result["theirs_value"] == 3
    
    def test_merge_result_to_dict(self):
        """Test MergeResult to_dict method."""
        result = MergeResult(
            merged={"value": 1},
            conflicts=[],
            has_conflicts=False
        )
        
        dict_result = result.to_dict()
        
        assert dict_result["merged"]["value"] == 1
        assert dict_result["has_conflicts"] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
