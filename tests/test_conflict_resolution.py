"""
Tests for data conflict detection and resolution algorithms.

Tests:
- Version conflict detection
- Content conflict detection
- Delete conflict detection
- Timestamp-based resolution strategy
- Source/target priority strategies
- Field-level merge strategies
- Business rule resolution
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4
from enum import Enum
from dataclasses import dataclass, field


class ConflictType(str, Enum):
    """Data conflict type enumeration."""
    VERSION_CONFLICT = "version_conflict"
    CONTENT_CONFLICT = "content_conflict"
    SCHEMA_CONFLICT = "schema_conflict"
    DELETE_CONFLICT = "delete_conflict"
    CONSTRAINT_CONFLICT = "constraint_conflict"


class ConflictStatus(str, Enum):
    """Conflict status enumeration."""
    PENDING = "pending"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    MANUAL = "manual"


class ResolutionStrategy(str, Enum):
    """Conflict resolution strategy enumeration."""
    TIMESTAMP_BASED = "timestamp_based"
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"
    MANUAL = "manual"
    FIELD_MERGE = "field_merge"
    BUSINESS_RULE = "business_rule"


@dataclass
class DataVersion:
    """Represents a version of data."""
    record_id: str
    data: Dict[str, Any]
    version: str
    timestamp: datetime
    source: str
    is_deleted: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conflict:
    """Represents a detected conflict."""
    id: str
    record_id: str
    conflict_type: ConflictType
    source_version: DataVersion
    target_version: DataVersion
    status: ConflictStatus = ConflictStatus.PENDING
    resolution: Optional[Dict[str, Any]] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "record_id": self.record_id,
            "conflict_type": self.conflict_type.value,
            "status": self.status.value,
            "priority": self.priority
        }


class ConflictDetector:
    """Detects conflicts between source and target data versions."""

    def detect_version_conflict(
        self,
        source: DataVersion,
        target: DataVersion
    ) -> Optional[Conflict]:
        """
        Detect version-based conflicts.

        A version conflict occurs when both source and target have
        been modified since last sync.
        """
        if source.version != target.version:
            return Conflict(
                id=str(uuid4()),
                record_id=source.record_id,
                conflict_type=ConflictType.VERSION_CONFLICT,
                source_version=source,
                target_version=target
            )
        return None

    def detect_content_conflict(
        self,
        source: DataVersion,
        target: DataVersion
    ) -> Optional[Conflict]:
        """
        Detect content-based conflicts.

        A content conflict occurs when the same fields have
        different values in source and target.
        """
        conflicting_fields = []

        for key in source.data:
            if key in target.data and source.data[key] != target.data[key]:
                conflicting_fields.append(key)

        if conflicting_fields:
            conflict = Conflict(
                id=str(uuid4()),
                record_id=source.record_id,
                conflict_type=ConflictType.CONTENT_CONFLICT,
                source_version=source,
                target_version=target
            )
            conflict.resolution = {"conflicting_fields": conflicting_fields}
            return conflict
        return None

    def detect_delete_conflict(
        self,
        source: DataVersion,
        target: DataVersion
    ) -> Optional[Conflict]:
        """
        Detect delete conflicts.

        A delete conflict occurs when one side deletes a record
        while the other modifies it.
        """
        if source.is_deleted != target.is_deleted:
            return Conflict(
                id=str(uuid4()),
                record_id=source.record_id,
                conflict_type=ConflictType.DELETE_CONFLICT,
                source_version=source,
                target_version=target,
                priority=8  # Delete conflicts are high priority
            )
        return None

    def detect_all_conflicts(
        self,
        source: DataVersion,
        target: DataVersion
    ) -> List[Conflict]:
        """Detect all types of conflicts."""
        conflicts = []

        # Check delete conflict first (highest priority)
        delete_conflict = self.detect_delete_conflict(source, target)
        if delete_conflict:
            conflicts.append(delete_conflict)
            return conflicts  # Delete conflicts supersede others

        # Check version conflict
        version_conflict = self.detect_version_conflict(source, target)
        if version_conflict:
            conflicts.append(version_conflict)

        # Check content conflict
        content_conflict = self.detect_content_conflict(source, target)
        if content_conflict:
            conflicts.append(content_conflict)

        return conflicts


class ConflictResolver:
    """Resolves conflicts using various strategies."""

    def __init__(self, default_strategy: ResolutionStrategy = ResolutionStrategy.TIMESTAMP_BASED):
        self.default_strategy = default_strategy
        self._business_rules: Dict[str, callable] = {}

    def register_business_rule(self, rule_name: str, rule_fn: callable) -> None:
        """Register a business rule for conflict resolution."""
        self._business_rules[rule_name] = rule_fn

    def resolve(
        self,
        conflict: Conflict,
        strategy: Optional[ResolutionStrategy] = None
    ) -> Dict[str, Any]:
        """
        Resolve a conflict using the specified strategy.

        Returns the resolved data.
        """
        strategy = strategy or self.default_strategy

        if strategy == ResolutionStrategy.TIMESTAMP_BASED:
            return self._resolve_by_timestamp(conflict)
        elif strategy == ResolutionStrategy.SOURCE_WINS:
            return self._resolve_source_wins(conflict)
        elif strategy == ResolutionStrategy.TARGET_WINS:
            return self._resolve_target_wins(conflict)
        elif strategy == ResolutionStrategy.FIELD_MERGE:
            return self._resolve_field_merge(conflict)
        elif strategy == ResolutionStrategy.BUSINESS_RULE:
            return self._resolve_by_business_rule(conflict)
        else:
            # Manual resolution required
            conflict.status = ConflictStatus.MANUAL
            return {}

    def _resolve_by_timestamp(self, conflict: Conflict) -> Dict[str, Any]:
        """Resolve by choosing the most recent version."""
        source = conflict.source_version
        target = conflict.target_version

        if source.timestamp > target.timestamp:
            winner = source
        else:
            winner = target

        conflict.status = ConflictStatus.RESOLVED
        conflict.resolved_at = datetime.utcnow()
        conflict.resolution = {
            "strategy": "timestamp_based",
            "winner": winner.source,
            "data": winner.data
        }

        return winner.data

    def _resolve_source_wins(self, conflict: Conflict) -> Dict[str, Any]:
        """Resolve by always choosing source."""
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolved_at = datetime.utcnow()
        conflict.resolution = {
            "strategy": "source_wins",
            "data": conflict.source_version.data
        }

        return conflict.source_version.data

    def _resolve_target_wins(self, conflict: Conflict) -> Dict[str, Any]:
        """Resolve by always choosing target."""
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolved_at = datetime.utcnow()
        conflict.resolution = {
            "strategy": "target_wins",
            "data": conflict.target_version.data
        }

        return conflict.target_version.data

    def _resolve_field_merge(self, conflict: Conflict) -> Dict[str, Any]:
        """
        Resolve by merging fields.

        Non-conflicting fields are merged.
        Conflicting fields use timestamp to determine winner.
        """
        source = conflict.source_version
        target = conflict.target_version

        merged = {}

        # Start with target data
        merged.update(target.data)

        # Apply source data for fields where source is newer
        if source.timestamp > target.timestamp:
            merged.update(source.data)
        else:
            # Only update non-conflicting fields from source
            for key, value in source.data.items():
                if key not in target.data:
                    merged[key] = value

        conflict.status = ConflictStatus.RESOLVED
        conflict.resolved_at = datetime.utcnow()
        conflict.resolution = {
            "strategy": "field_merge",
            "data": merged
        }

        return merged

    def _resolve_by_business_rule(self, conflict: Conflict) -> Dict[str, Any]:
        """Resolve using registered business rules."""
        # Try to find applicable rule
        record_type = conflict.source_version.metadata.get("record_type", "default")

        if record_type in self._business_rules:
            result = self._business_rules[record_type](conflict)
            conflict.status = ConflictStatus.RESOLVED
            conflict.resolved_at = datetime.utcnow()
            conflict.resolution = {
                "strategy": "business_rule",
                "rule": record_type,
                "data": result
            }
            return result

        # Fallback to timestamp
        return self._resolve_by_timestamp(conflict)


class TestConflictDetector:
    """Tests for ConflictDetector."""

    @pytest.fixture
    def detector(self):
        """Create conflict detector instance."""
        return ConflictDetector()

    def test_detect_version_conflict(self, detector):
        """Test version conflict detection."""
        source = DataVersion(
            record_id="record_1",
            data={"name": "Source"},
            version="v2",
            timestamp=datetime.utcnow(),
            source="source_db"
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Target"},
            version="v1",
            timestamp=datetime.utcnow() - timedelta(hours=1),
            source="target_db"
        )

        conflict = detector.detect_version_conflict(source, target)

        assert conflict is not None
        assert conflict.conflict_type == ConflictType.VERSION_CONFLICT
        assert conflict.record_id == "record_1"

    def test_no_version_conflict_when_same(self, detector):
        """Test no conflict when versions match."""
        source = DataVersion(
            record_id="record_1",
            data={"name": "Same"},
            version="v1",
            timestamp=datetime.utcnow(),
            source="source_db"
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Same"},
            version="v1",
            timestamp=datetime.utcnow(),
            source="target_db"
        )

        conflict = detector.detect_version_conflict(source, target)

        assert conflict is None

    def test_detect_content_conflict(self, detector):
        """Test content conflict detection."""
        source = DataVersion(
            record_id="record_1",
            data={"name": "Alice", "age": 30},
            version="v1",
            timestamp=datetime.utcnow(),
            source="source_db"
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Bob", "age": 30},  # name differs
            version="v1",
            timestamp=datetime.utcnow(),
            source="target_db"
        )

        conflict = detector.detect_content_conflict(source, target)

        assert conflict is not None
        assert conflict.conflict_type == ConflictType.CONTENT_CONFLICT
        assert "name" in conflict.resolution["conflicting_fields"]
        assert "age" not in conflict.resolution["conflicting_fields"]

    def test_no_content_conflict_when_same(self, detector):
        """Test no content conflict when data matches."""
        data = {"name": "Alice", "age": 30}
        source = DataVersion(
            record_id="record_1",
            data=data.copy(),
            version="v1",
            timestamp=datetime.utcnow(),
            source="source_db"
        )
        target = DataVersion(
            record_id="record_1",
            data=data.copy(),
            version="v1",
            timestamp=datetime.utcnow(),
            source="target_db"
        )

        conflict = detector.detect_content_conflict(source, target)

        assert conflict is None

    def test_detect_delete_conflict(self, detector):
        """Test delete conflict detection."""
        source = DataVersion(
            record_id="record_1",
            data={},
            version="v2",
            timestamp=datetime.utcnow(),
            source="source_db",
            is_deleted=True
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Still exists"},
            version="v1",
            timestamp=datetime.utcnow(),
            source="target_db",
            is_deleted=False
        )

        conflict = detector.detect_delete_conflict(source, target)

        assert conflict is not None
        assert conflict.conflict_type == ConflictType.DELETE_CONFLICT
        assert conflict.priority == 8  # High priority

    def test_no_delete_conflict_when_both_exist(self, detector):
        """Test no delete conflict when both records exist."""
        source = DataVersion(
            record_id="record_1",
            data={"name": "Source"},
            version="v1",
            timestamp=datetime.utcnow(),
            source="source_db",
            is_deleted=False
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Target"},
            version="v1",
            timestamp=datetime.utcnow(),
            source="target_db",
            is_deleted=False
        )

        conflict = detector.detect_delete_conflict(source, target)

        assert conflict is None

    def test_detect_all_conflicts(self, detector):
        """Test detecting multiple conflict types."""
        source = DataVersion(
            record_id="record_1",
            data={"name": "Alice", "email": "alice@new.com"},
            version="v2",
            timestamp=datetime.utcnow(),
            source="source_db"
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Alice", "email": "alice@old.com"},
            version="v1",
            timestamp=datetime.utcnow() - timedelta(hours=1),
            source="target_db"
        )

        conflicts = detector.detect_all_conflicts(source, target)

        assert len(conflicts) >= 1
        # Should detect both version and content conflicts
        conflict_types = [c.conflict_type for c in conflicts]
        assert ConflictType.VERSION_CONFLICT in conflict_types


class TestConflictResolver:
    """Tests for ConflictResolver."""

    @pytest.fixture
    def resolver(self):
        """Create conflict resolver instance."""
        return ConflictResolver()

    @pytest.fixture
    def sample_conflict(self):
        """Create a sample conflict for testing."""
        source = DataVersion(
            record_id="record_1",
            data={"name": "Source Name", "value": 100},
            version="v2",
            timestamp=datetime.utcnow(),
            source="source_db"
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Target Name", "value": 50},
            version="v1",
            timestamp=datetime.utcnow() - timedelta(hours=1),
            source="target_db"
        )
        return Conflict(
            id=str(uuid4()),
            record_id="record_1",
            conflict_type=ConflictType.CONTENT_CONFLICT,
            source_version=source,
            target_version=target
        )

    def test_resolve_by_timestamp_source_wins(self, resolver):
        """Test timestamp resolution when source is newer."""
        source = DataVersion(
            record_id="record_1",
            data={"name": "Newer"},
            version="v2",
            timestamp=datetime.utcnow(),
            source="source_db"
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Older"},
            version="v1",
            timestamp=datetime.utcnow() - timedelta(hours=1),
            source="target_db"
        )
        conflict = Conflict(
            id=str(uuid4()),
            record_id="record_1",
            conflict_type=ConflictType.CONTENT_CONFLICT,
            source_version=source,
            target_version=target
        )

        result = resolver.resolve(conflict, ResolutionStrategy.TIMESTAMP_BASED)

        assert result["name"] == "Newer"
        assert conflict.status == ConflictStatus.RESOLVED
        assert conflict.resolution["winner"] == "source_db"

    def test_resolve_by_timestamp_target_wins(self, resolver):
        """Test timestamp resolution when target is newer."""
        source = DataVersion(
            record_id="record_1",
            data={"name": "Older"},
            version="v1",
            timestamp=datetime.utcnow() - timedelta(hours=1),
            source="source_db"
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Newer"},
            version="v2",
            timestamp=datetime.utcnow(),
            source="target_db"
        )
        conflict = Conflict(
            id=str(uuid4()),
            record_id="record_1",
            conflict_type=ConflictType.CONTENT_CONFLICT,
            source_version=source,
            target_version=target
        )

        result = resolver.resolve(conflict, ResolutionStrategy.TIMESTAMP_BASED)

        assert result["name"] == "Newer"
        assert conflict.resolution["winner"] == "target_db"

    def test_resolve_source_wins(self, resolver, sample_conflict):
        """Test source wins strategy."""
        result = resolver.resolve(sample_conflict, ResolutionStrategy.SOURCE_WINS)

        assert result["name"] == "Source Name"
        assert result["value"] == 100
        assert sample_conflict.status == ConflictStatus.RESOLVED

    def test_resolve_target_wins(self, resolver, sample_conflict):
        """Test target wins strategy."""
        result = resolver.resolve(sample_conflict, ResolutionStrategy.TARGET_WINS)

        assert result["name"] == "Target Name"
        assert result["value"] == 50
        assert sample_conflict.status == ConflictStatus.RESOLVED

    def test_resolve_field_merge(self, resolver):
        """Test field merge strategy."""
        source = DataVersion(
            record_id="record_1",
            data={"name": "Source", "email": "source@example.com", "source_only": "yes"},
            version="v2",
            timestamp=datetime.utcnow(),
            source="source_db"
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Target", "phone": "123-456-7890"},
            version="v1",
            timestamp=datetime.utcnow() - timedelta(hours=1),
            source="target_db"
        )
        conflict = Conflict(
            id=str(uuid4()),
            record_id="record_1",
            conflict_type=ConflictType.CONTENT_CONFLICT,
            source_version=source,
            target_version=target
        )

        result = resolver.resolve(conflict, ResolutionStrategy.FIELD_MERGE)

        # Source is newer, so its fields should win
        assert result["name"] == "Source"
        assert result["email"] == "source@example.com"
        assert result["source_only"] == "yes"
        # Phone from target should be preserved
        assert "phone" in result

    def test_resolve_by_business_rule(self, resolver):
        """Test business rule resolution."""
        # Register a custom business rule
        def priority_rule(conflict: Conflict) -> Dict[str, Any]:
            # Always prefer higher value
            source_val = conflict.source_version.data.get("priority", 0)
            target_val = conflict.target_version.data.get("priority", 0)
            if source_val >= target_val:
                return conflict.source_version.data
            return conflict.target_version.data

        resolver.register_business_rule("priority_record", priority_rule)

        source = DataVersion(
            record_id="record_1",
            data={"name": "Source", "priority": 10},
            version="v2",
            timestamp=datetime.utcnow() - timedelta(hours=1),  # Older
            source="source_db",
            metadata={"record_type": "priority_record"}
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Target", "priority": 5},
            version="v1",
            timestamp=datetime.utcnow(),  # Newer
            source="target_db",
            metadata={"record_type": "priority_record"}
        )
        conflict = Conflict(
            id=str(uuid4()),
            record_id="record_1",
            conflict_type=ConflictType.CONTENT_CONFLICT,
            source_version=source,
            target_version=target
        )

        result = resolver.resolve(conflict, ResolutionStrategy.BUSINESS_RULE)

        # Business rule should choose source (higher priority)
        assert result["name"] == "Source"
        assert result["priority"] == 10

    def test_manual_resolution_required(self, resolver, sample_conflict):
        """Test manual resolution strategy."""
        result = resolver.resolve(sample_conflict, ResolutionStrategy.MANUAL)

        assert result == {}
        assert sample_conflict.status == ConflictStatus.MANUAL

    def test_default_strategy(self):
        """Test using default strategy."""
        resolver = ConflictResolver(default_strategy=ResolutionStrategy.SOURCE_WINS)

        source = DataVersion(
            record_id="record_1",
            data={"name": "Source"},
            version="v1",
            timestamp=datetime.utcnow() - timedelta(hours=1),  # Older
            source="source_db"
        )
        target = DataVersion(
            record_id="record_1",
            data={"name": "Target"},
            version="v2",
            timestamp=datetime.utcnow(),  # Newer
            source="target_db"
        )
        conflict = Conflict(
            id=str(uuid4()),
            record_id="record_1",
            conflict_type=ConflictType.CONTENT_CONFLICT,
            source_version=source,
            target_version=target
        )

        # Should use default (source_wins) even though target is newer
        result = resolver.resolve(conflict)

        assert result["name"] == "Source"


class TestConflictIntegration:
    """Integration tests for conflict detection and resolution."""

    def test_full_conflict_workflow(self):
        """Test complete conflict detection and resolution workflow."""
        detector = ConflictDetector()
        resolver = ConflictResolver()

        # Simulate two systems with conflicting data
        source = DataVersion(
            record_id="customer_123",
            data={
                "name": "John Doe",
                "email": "john.new@example.com",
                "phone": "555-1234",
                "updated_by": "system_a"
            },
            version="v5",
            timestamp=datetime.utcnow(),
            source="crm_system"
        )

        target = DataVersion(
            record_id="customer_123",
            data={
                "name": "John Doe",
                "email": "john.old@example.com",
                "address": "123 Main St",
                "updated_by": "system_b"
            },
            version="v4",
            timestamp=datetime.utcnow() - timedelta(minutes=30),
            source="billing_system"
        )

        # Detect conflicts
        conflicts = detector.detect_all_conflicts(source, target)
        assert len(conflicts) >= 1

        # Resolve each conflict
        for conflict in conflicts:
            resolved_data = resolver.resolve(conflict, ResolutionStrategy.FIELD_MERGE)
            assert resolved_data is not None
            assert conflict.status == ConflictStatus.RESOLVED

    def test_batch_conflict_processing(self):
        """Test processing multiple conflicts in batch."""
        detector = ConflictDetector()
        resolver = ConflictResolver()

        # Create batch of records
        records = []
        for i in range(10):
            source = DataVersion(
                record_id=f"record_{i}",
                data={"value": i * 2},
                version=f"v{i + 1}",
                timestamp=datetime.utcnow(),
                source="source"
            )
            target = DataVersion(
                record_id=f"record_{i}",
                data={"value": i},
                version=f"v{i}",
                timestamp=datetime.utcnow() - timedelta(hours=1),
                source="target"
            )
            records.append((source, target))

        # Detect all conflicts
        all_conflicts = []
        for source, target in records:
            conflicts = detector.detect_all_conflicts(source, target)
            all_conflicts.extend(conflicts)

        # Resolve all conflicts
        resolved_count = 0
        for conflict in all_conflicts:
            resolver.resolve(conflict, ResolutionStrategy.TIMESTAMP_BASED)
            if conflict.status == ConflictStatus.RESOLVED:
                resolved_count += 1

        assert resolved_count == len(all_conflicts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
