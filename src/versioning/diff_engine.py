"""
Diff Engine.

Computes differences between data versions:
- Field-level and line-level diff
- Three-way merge with conflict detection
- Conflict resolution
"""

import json
import difflib
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class DiffLevel(str, Enum):
    """Diff granularity level."""
    FIELD = "field"
    LINE = "line"


@dataclass
class FieldChange:
    """Represents a single field change."""
    field: str
    change_type: str  # added, removed, modified
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
    """
    Diff Engine for computing version differences.
    
    Provides:
    - Field-level diff for structured data
    - Line-level diff for text comparison
    - Three-way merge with conflict detection
    - Conflict resolution strategies
    """
    
    def compute_diff(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        diff_level: DiffLevel = DiffLevel.FIELD
    ) -> DiffResult:
        """
        Compute difference between two data versions.
        
        Args:
            old_data: Original data
            new_data: New data
            diff_level: Granularity level (field or line)
            
        Returns:
            DiffResult with changes and summary
        """
        if diff_level == DiffLevel.LINE:
            return self._line_diff(old_data, new_data)
        else:
            return self._field_diff(old_data, new_data)
    
    def _field_diff(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> DiffResult:
        """Compute field-level differences."""
        changes = []
        old_data = old_data or {}
        new_data = new_data or {}
        
        old_keys = set(old_data.keys())
        new_keys = set(new_data.keys())
        
        # Added fields
        for key in new_keys - old_keys:
            changes.append(FieldChange(
                field=key,
                change_type="added",
                old_value=None,
                new_value=new_data[key]
            ))
        
        # Removed fields
        for key in old_keys - new_keys:
            changes.append(FieldChange(
                field=key,
                change_type="removed",
                old_value=old_data[key],
                new_value=None
            ))
        
        # Modified fields
        for key in old_keys & new_keys:
            if old_data[key] != new_data[key]:
                # Handle nested dicts recursively
                if isinstance(old_data[key], dict) and isinstance(new_data[key], dict):
                    nested_diff = self._field_diff(old_data[key], new_data[key])
                    if nested_diff.changes:
                        changes.append(FieldChange(
                            field=key,
                            change_type="modified",
                            old_value=old_data[key],
                            new_value=new_data[key]
                        ))
                else:
                    changes.append(FieldChange(
                        field=key,
                        change_type="modified",
                        old_value=old_data[key],
                        new_value=new_data[key]
                    ))
        
        summary = self._generate_summary(changes)
        
        return DiffResult(
            diff_level=DiffLevel.FIELD,
            changes=changes,
            summary=summary
        )
    
    def _line_diff(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> DiffResult:
        """Compute line-level differences using unified diff."""
        old_lines = json.dumps(old_data or {}, indent=2, sort_keys=True).splitlines()
        new_lines = json.dumps(new_data or {}, indent=2, sort_keys=True).splitlines()
        
        differ = difflib.unified_diff(
            old_lines, new_lines,
            fromfile='old', tofile='new',
            lineterm=''
        )
        unified_diff = list(differ)
        
        summary = self._generate_line_summary(old_lines, new_lines)
        
        return DiffResult(
            diff_level=DiffLevel.LINE,
            unified_diff=unified_diff,
            summary=summary
        )
    
    def _generate_summary(self, changes: List[FieldChange]) -> DiffSummary:
        """Generate summary from field changes."""
        return DiffSummary(
            added=sum(1 for c in changes if c.change_type == "added"),
            removed=sum(1 for c in changes if c.change_type == "removed"),
            modified=sum(1 for c in changes if c.change_type == "modified")
        )
    
    def _generate_line_summary(
        self,
        old_lines: List[str],
        new_lines: List[str]
    ) -> DiffSummary:
        """Generate summary from line diff."""
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        
        added = 0
        removed = 0
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                added += j2 - j1
            elif tag == 'delete':
                removed += i2 - i1
            elif tag == 'replace':
                added += j2 - j1
                removed += i2 - i1
        
        return DiffSummary(
            added=added,
            removed=removed,
            modified=0  # Line diff doesn't track modifications separately
        )
    
    def three_way_merge(
        self,
        base: Dict[str, Any],
        ours: Dict[str, Any],
        theirs: Dict[str, Any]
    ) -> MergeResult:
        """
        Perform three-way merge.
        
        Args:
            base: Common ancestor version
            ours: Our changes
            theirs: Their changes
            
        Returns:
            MergeResult with merged data and any conflicts
        """
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
            
            # Both sides made the same change
            if ours_val == theirs_val:
                if ours_val is not None:
                    merged[key] = ours_val
                # If both deleted, don't include in merged
                continue
            
            # Only ours changed
            if ours_val != base_val and theirs_val == base_val:
                if ours_val is not None:
                    merged[key] = ours_val
                # If we deleted, don't include
                continue
            
            # Only theirs changed
            if theirs_val != base_val and ours_val == base_val:
                if theirs_val is not None:
                    merged[key] = theirs_val
                # If they deleted, don't include
                continue
            
            # Both changed differently - conflict
            if ours_val != base_val and theirs_val != base_val:
                conflicts.append(MergeConflict(
                    field=key,
                    base_value=base_val,
                    ours_value=ours_val,
                    theirs_value=theirs_val
                ))
                # Use ours as default in merged (can be resolved later)
                if ours_val is not None:
                    merged[key] = ours_val
                elif theirs_val is not None:
                    merged[key] = theirs_val
        
        return MergeResult(
            merged=merged,
            conflicts=conflicts,
            has_conflicts=len(conflicts) > 0
        )
    
    def resolve_conflict(
        self,
        merge_result: MergeResult,
        field: str,
        resolution: str,  # "ours", "theirs", "base", "custom"
        custom_value: Any = None
    ) -> MergeResult:
        """
        Resolve a specific conflict in a merge result.
        
        Args:
            merge_result: The merge result with conflicts
            field: Field to resolve
            resolution: Resolution strategy
            custom_value: Custom value if resolution is "custom"
            
        Returns:
            Updated MergeResult
        """
        # Find the conflict
        conflict = None
        remaining_conflicts = []
        
        for c in merge_result.conflicts:
            if c.field == field:
                conflict = c
            else:
                remaining_conflicts.append(c)
        
        if not conflict:
            logger.warning(f"No conflict found for field: {field}")
            return merge_result
        
        # Apply resolution
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
        
        return MergeResult(
            merged=new_merged,
            conflicts=remaining_conflicts,
            has_conflicts=len(remaining_conflicts) > 0
        )
    
    def resolve_all_conflicts(
        self,
        merge_result: MergeResult,
        strategy: str = "ours"  # "ours", "theirs", "base"
    ) -> MergeResult:
        """
        Resolve all conflicts using a single strategy.
        
        Args:
            merge_result: The merge result with conflicts
            strategy: Resolution strategy for all conflicts
            
        Returns:
            MergeResult with all conflicts resolved
        """
        result = merge_result
        for conflict in list(merge_result.conflicts):
            result = self.resolve_conflict(result, conflict.field, strategy)
        return result
    
    def compute_patch(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute a patch that can be applied to transform old_data to new_data.
        
        Returns:
            Patch dictionary with operations
        """
        diff = self._field_diff(old_data, new_data)
        
        patch = {
            "operations": [],
            "checksum": None,
        }
        
        for change in diff.changes:
            if change.change_type == "added":
                patch["operations"].append({
                    "op": "add",
                    "path": change.field,
                    "value": change.new_value
                })
            elif change.change_type == "removed":
                patch["operations"].append({
                    "op": "remove",
                    "path": change.field
                })
            elif change.change_type == "modified":
                patch["operations"].append({
                    "op": "replace",
                    "path": change.field,
                    "value": change.new_value
                })
        
        return patch
    
    def apply_patch(
        self,
        data: Dict[str, Any],
        patch: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply a patch to data.
        
        Args:
            data: Original data
            patch: Patch to apply
            
        Returns:
            Patched data
        """
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


# Global instance
diff_engine = DiffEngine()
