"""
Conflict Detection and Resolution for SuperInsight Platform.

Provides comprehensive conflict handling for data synchronization:
- Multiple detection strategies
- Configurable resolution policies
- Conflict audit trail
- Manual resolution workflow
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import hashlib
import json
from uuid import uuid4

logger = logging.getLogger(__name__)


class ConflictType(str, Enum):
    """Types of conflicts."""
    CONCURRENT_UPDATE = "concurrent_update"
    STALE_UPDATE = "stale_update"
    DELETE_UPDATE = "delete_update"
    SCHEMA_MISMATCH = "schema_mismatch"
    CONSTRAINT_VIOLATION = "constraint_violation"
    DATA_TYPE_MISMATCH = "data_type_mismatch"


class ResolutionStrategy(str, Enum):
    """Conflict resolution strategies."""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    SOURCE_PRIORITY = "source_priority"
    TARGET_PRIORITY = "target_priority"
    MERGE_FIELDS = "merge_fields"
    MERGE_DEEP = "merge_deep"
    CUSTOM = "custom"
    MANUAL = "manual"
    SKIP = "skip"


class ConflictStatus(str, Enum):
    """Status of a conflict."""
    DETECTED = "detected"
    RESOLVING = "resolving"
    RESOLVED = "resolved"
    FAILED = "failed"
    PENDING_MANUAL = "pending_manual"
    SKIPPED = "skipped"


@dataclass
class ConflictContext:
    """Context information for conflict resolution."""
    sync_id: str
    source_id: str
    target_id: str
    table: str
    operation: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictRecord:
    """Detailed record of a conflict."""
    id: str
    conflict_type: ConflictType
    status: ConflictStatus
    context: ConflictContext
    
    # Data
    source_data: Dict[str, Any]
    target_data: Optional[Dict[str, Any]] = None
    resolved_data: Optional[Dict[str, Any]] = None
    
    # Resolution
    resolution_strategy: Optional[ResolutionStrategy] = None
    resolution_reason: Optional[str] = None
    resolved_by: Optional[str] = None  # "system" or user ID
    
    # Timestamps
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    # Audit
    resolution_attempts: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "conflict_type": self.conflict_type.value,
            "status": self.status.value,
            "context": {
                "sync_id": self.context.sync_id,
                "source_id": self.context.source_id,
                "target_id": self.context.target_id,
                "table": self.context.table,
                "operation": self.context.operation
            },
            "source_data": self.source_data,
            "target_data": self.target_data,
            "resolved_data": self.resolved_data,
            "resolution_strategy": self.resolution_strategy.value if self.resolution_strategy else None,
            "resolution_reason": self.resolution_reason,
            "resolved_by": self.resolved_by,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class ResolutionPolicy:
    """Policy for conflict resolution."""
    name: str
    default_strategy: ResolutionStrategy = ResolutionStrategy.LAST_WRITE_WINS
    
    # Strategy overrides by conflict type
    type_strategies: Dict[ConflictType, ResolutionStrategy] = field(default_factory=dict)
    
    # Strategy overrides by table
    table_strategies: Dict[str, ResolutionStrategy] = field(default_factory=dict)
    
    # Field-level merge configuration
    merge_config: Dict[str, str] = field(default_factory=dict)  # field -> "source" | "target" | "newer"
    
    # Validation
    require_validation: bool = True
    max_resolution_attempts: int = 3
    
    # Notifications
    notify_on_manual: bool = True
    notify_on_failure: bool = True


class ConflictDetector:
    """
    Detects conflicts between source and target data.
    
    Supports multiple detection strategies based on:
    - Timestamps
    - Version numbers
    - Content hashing
    - Schema comparison
    """
    
    def __init__(self):
        self._version_fields: Dict[str, str] = {}  # table -> version field
        self._timestamp_fields: Dict[str, str] = {}  # table -> timestamp field
    
    def configure_table(
        self,
        table: str,
        version_field: Optional[str] = None,
        timestamp_field: Optional[str] = None
    ) -> None:
        """Configure detection fields for a table."""
        if version_field:
            self._version_fields[table] = version_field
        if timestamp_field:
            self._timestamp_fields[table] = timestamp_field
    
    async def detect(
        self,
        context: ConflictContext,
        source_data: Dict[str, Any],
        target_data: Optional[Dict[str, Any]]
    ) -> Optional[ConflictRecord]:
        """
        Detect if there's a conflict.
        
        Returns ConflictRecord if conflict detected, None otherwise.
        """
        # No target data = no conflict (new record)
        if target_data is None:
            return None
        
        # Check for delete-update conflict
        if context.operation == "delete" and target_data:
            return self._create_conflict(
                ConflictType.DELETE_UPDATE,
                context,
                source_data,
                target_data,
                "Attempting to delete modified record"
            )
        
        # Check version-based conflict
        version_conflict = self._check_version_conflict(
            context.table, source_data, target_data
        )
        if version_conflict:
            return self._create_conflict(
                ConflictType.CONCURRENT_UPDATE,
                context,
                source_data,
                target_data,
                version_conflict
            )
        
        # Check timestamp-based conflict
        timestamp_conflict = self._check_timestamp_conflict(
            context.table, source_data, target_data
        )
        if timestamp_conflict:
            return self._create_conflict(
                ConflictType.STALE_UPDATE,
                context,
                source_data,
                target_data,
                timestamp_conflict
            )
        
        # Check content-based conflict
        if self._has_content_conflict(source_data, target_data):
            return self._create_conflict(
                ConflictType.CONCURRENT_UPDATE,
                context,
                source_data,
                target_data,
                "Content differs between source and target"
            )
        
        return None
    
    def _check_version_conflict(
        self,
        table: str,
        source: Dict[str, Any],
        target: Dict[str, Any]
    ) -> Optional[str]:
        """Check for version-based conflict."""
        version_field = self._version_fields.get(table)
        if not version_field:
            return None
        
        source_version = source.get(version_field)
        target_version = target.get(version_field)
        
        if source_version is None or target_version is None:
            return None
        
        if source_version < target_version:
            return f"Source version ({source_version}) < target version ({target_version})"
        
        return None
    
    def _check_timestamp_conflict(
        self,
        table: str,
        source: Dict[str, Any],
        target: Dict[str, Any]
    ) -> Optional[str]:
        """Check for timestamp-based conflict."""
        ts_field = self._timestamp_fields.get(table, "updated_at")
        
        source_ts = source.get(ts_field)
        target_ts = target.get(ts_field)
        
        if source_ts is None or target_ts is None:
            return None
        
        # Parse timestamps if strings
        if isinstance(source_ts, str):
            source_ts = datetime.fromisoformat(source_ts.replace('Z', '+00:00'))
        if isinstance(target_ts, str):
            target_ts = datetime.fromisoformat(target_ts.replace('Z', '+00:00'))
        
        if source_ts < target_ts:
            return f"Source timestamp ({source_ts}) < target timestamp ({target_ts})"
        
        return None
    
    def _has_content_conflict(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any]
    ) -> bool:
        """Check if content differs."""
        # Exclude metadata fields from comparison
        exclude_fields = {"_id", "id", "created_at", "updated_at", "version"}
        
        source_filtered = {k: v for k, v in source.items() if k not in exclude_fields}
        target_filtered = {k: v for k, v in target.items() if k not in exclude_fields}
        
        source_hash = self._compute_hash(source_filtered)
        target_hash = self._compute_hash(target_filtered)
        
        return source_hash != target_hash
    
    def _compute_hash(self, data: Dict[str, Any]) -> str:
        """Compute hash of data."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _create_conflict(
        self,
        conflict_type: ConflictType,
        context: ConflictContext,
        source_data: Dict[str, Any],
        target_data: Dict[str, Any],
        reason: str
    ) -> ConflictRecord:
        """Create a conflict record."""
        return ConflictRecord(
            id=str(uuid4()),
            conflict_type=conflict_type,
            status=ConflictStatus.DETECTED,
            context=context,
            source_data=source_data,
            target_data=target_data,
            resolution_reason=reason
        )


class ConflictResolver:
    """
    Resolves conflicts using configured policies.
    
    Supports:
    - Multiple resolution strategies
    - Custom resolvers
    - Field-level merge
    - Manual resolution workflow
    """
    
    def __init__(self, policy: Optional[ResolutionPolicy] = None):
        self.policy = policy or ResolutionPolicy(name="default")
        self._custom_resolvers: Dict[str, Callable] = {}
        self._validators: List[Callable] = []
    
    def register_resolver(
        self,
        key: str,
        resolver: Callable[[ConflictRecord], Dict[str, Any]]
    ) -> None:
        """Register a custom resolver."""
        self._custom_resolvers[key] = resolver
    
    def register_validator(
        self,
        validator: Callable[[Dict[str, Any]], bool]
    ) -> None:
        """Register a data validator."""
        self._validators.append(validator)
    
    async def resolve(self, conflict: ConflictRecord) -> ConflictRecord:
        """
        Resolve a conflict.
        
        Returns updated ConflictRecord with resolution.
        """
        conflict.status = ConflictStatus.RESOLVING
        conflict.resolution_attempts += 1
        
        try:
            # Determine strategy
            strategy = self._get_strategy(conflict)
            conflict.resolution_strategy = strategy
            
            # Apply resolution
            if strategy == ResolutionStrategy.MANUAL:
                conflict.status = ConflictStatus.PENDING_MANUAL
                return conflict
            
            if strategy == ResolutionStrategy.SKIP:
                conflict.status = ConflictStatus.SKIPPED
                conflict.resolved_at = datetime.utcnow()
                return conflict
            
            if strategy == ResolutionStrategy.CUSTOM:
                resolved_data = await self._apply_custom_resolver(conflict)
            else:
                resolved_data = self._apply_strategy(conflict, strategy)
            
            # Validate resolved data
            if self.policy.require_validation:
                if not self._validate_data(resolved_data):
                    raise ValueError("Resolved data failed validation")
            
            conflict.resolved_data = resolved_data
            conflict.status = ConflictStatus.RESOLVED
            conflict.resolved_at = datetime.utcnow()
            conflict.resolved_by = "system"
            
        except Exception as e:
            conflict.errors.append(str(e))
            
            if conflict.resolution_attempts >= self.policy.max_resolution_attempts:
                conflict.status = ConflictStatus.FAILED
            else:
                conflict.status = ConflictStatus.DETECTED
            
            logger.error(f"Conflict resolution failed: {e}")
        
        return conflict
    
    async def resolve_manually(
        self,
        conflict: ConflictRecord,
        resolved_data: Dict[str, Any],
        user_id: str,
        reason: Optional[str] = None
    ) -> ConflictRecord:
        """
        Manually resolve a conflict.
        
        Args:
            conflict: The conflict to resolve
            resolved_data: The manually resolved data
            user_id: ID of the user resolving
            reason: Optional reason for resolution
        """
        # Validate
        if self.policy.require_validation:
            if not self._validate_data(resolved_data):
                raise ValueError("Resolved data failed validation")
        
        conflict.resolved_data = resolved_data
        conflict.resolution_strategy = ResolutionStrategy.MANUAL
        conflict.resolution_reason = reason or "Manual resolution"
        conflict.resolved_by = user_id
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolved_at = datetime.utcnow()
        
        return conflict
    
    def _get_strategy(self, conflict: ConflictRecord) -> ResolutionStrategy:
        """Determine resolution strategy for conflict."""
        # Check table-specific strategy
        table = conflict.context.table
        if table in self.policy.table_strategies:
            return self.policy.table_strategies[table]
        
        # Check type-specific strategy
        if conflict.conflict_type in self.policy.type_strategies:
            return self.policy.type_strategies[conflict.conflict_type]
        
        # Check for custom resolver
        if table in self._custom_resolvers:
            return ResolutionStrategy.CUSTOM
        
        return self.policy.default_strategy
    
    def _apply_strategy(
        self,
        conflict: ConflictRecord,
        strategy: ResolutionStrategy
    ) -> Dict[str, Any]:
        """Apply resolution strategy."""
        source = conflict.source_data
        target = conflict.target_data or {}
        
        if strategy == ResolutionStrategy.LAST_WRITE_WINS:
            return source
        
        elif strategy == ResolutionStrategy.FIRST_WRITE_WINS:
            return target
        
        elif strategy == ResolutionStrategy.SOURCE_PRIORITY:
            return source
        
        elif strategy == ResolutionStrategy.TARGET_PRIORITY:
            return target
        
        elif strategy == ResolutionStrategy.MERGE_FIELDS:
            return self._merge_fields(source, target)
        
        elif strategy == ResolutionStrategy.MERGE_DEEP:
            return self._merge_deep(source, target)
        
        else:
            return source
    
    async def _apply_custom_resolver(
        self,
        conflict: ConflictRecord
    ) -> Dict[str, Any]:
        """Apply custom resolver."""
        table = conflict.context.table
        resolver = self._custom_resolvers.get(table)
        
        if not resolver:
            raise ValueError(f"No custom resolver for table: {table}")
        
        if asyncio.iscoroutinefunction(resolver):
            return await resolver(conflict)
        else:
            return resolver(conflict)
    
    def _merge_fields(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge at field level using merge config."""
        merged = target.copy()
        
        for field, value in source.items():
            merge_rule = self.policy.merge_config.get(field, "source")
            
            if merge_rule == "source":
                merged[field] = value
            elif merge_rule == "target":
                pass  # Keep target value
            elif merge_rule == "newer":
                # Compare timestamps if available
                merged[field] = value  # Default to source
        
        return merged
    
    def _merge_deep(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge source into target."""
        merged = target.copy()
        
        for key, value in source.items():
            if key in merged:
                if isinstance(value, dict) and isinstance(merged[key], dict):
                    merged[key] = self._merge_deep(value, merged[key])
                else:
                    merged[key] = value
            else:
                merged[key] = value
        
        return merged
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate resolved data."""
        for validator in self._validators:
            try:
                if not validator(data):
                    return False
            except Exception:
                return False
        return True


class ConflictManager:
    """
    Manages conflict detection, resolution, and tracking.
    
    Provides:
    - Centralized conflict handling
    - Conflict history and audit
    - Statistics and reporting
    - Manual resolution workflow
    """
    
    def __init__(self):
        self._detector = ConflictDetector()
        self._resolvers: Dict[str, ConflictResolver] = {}
        self._conflicts: Dict[str, ConflictRecord] = {}
        self._handlers: Dict[str, List[Callable]] = {}
        self._stats = {
            "total_detected": 0,
            "total_resolved": 0,
            "total_failed": 0,
            "pending_manual": 0,
            "by_type": {},
            "by_table": {}
        }
    
    def configure_resolver(
        self,
        name: str,
        policy: ResolutionPolicy
    ) -> ConflictResolver:
        """Configure a resolver with policy."""
        resolver = ConflictResolver(policy)
        self._resolvers[name] = resolver
        return resolver
    
    def get_resolver(self, name: str) -> Optional[ConflictResolver]:
        """Get a configured resolver."""
        return self._resolvers.get(name)
    
    def on_event(self, event: str, handler: Callable) -> None:
        """Register event handler."""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)
    
    async def process(
        self,
        resolver_name: str,
        context: ConflictContext,
        source_data: Dict[str, Any],
        target_data: Optional[Dict[str, Any]]
    ) -> Optional[ConflictRecord]:
        """
        Process potential conflict.
        
        Detects and resolves conflicts in one call.
        """
        # Detect conflict
        conflict = await self._detector.detect(context, source_data, target_data)
        
        if not conflict:
            return None
        
        # Track conflict
        self._conflicts[conflict.id] = conflict
        self._update_stats("detected", conflict)
        await self._emit_event("conflict_detected", conflict)
        
        # Get resolver
        resolver = self._resolvers.get(resolver_name)
        if not resolver:
            resolver = ConflictResolver()
        
        # Resolve
        conflict = await resolver.resolve(conflict)
        
        # Update tracking
        if conflict.status == ConflictStatus.RESOLVED:
            self._update_stats("resolved", conflict)
            await self._emit_event("conflict_resolved", conflict)
        elif conflict.status == ConflictStatus.FAILED:
            self._update_stats("failed", conflict)
            await self._emit_event("conflict_failed", conflict)
        elif conflict.status == ConflictStatus.PENDING_MANUAL:
            self._update_stats("pending", conflict)
            await self._emit_event("conflict_pending", conflict)
        
        return conflict
    
    async def resolve_manually(
        self,
        conflict_id: str,
        resolved_data: Dict[str, Any],
        user_id: str,
        reason: Optional[str] = None
    ) -> ConflictRecord:
        """Manually resolve a pending conflict."""
        conflict = self._conflicts.get(conflict_id)
        if not conflict:
            raise ValueError(f"Conflict not found: {conflict_id}")
        
        if conflict.status != ConflictStatus.PENDING_MANUAL:
            raise ValueError(f"Conflict is not pending manual resolution: {conflict_id}")
        
        # Use default resolver for manual resolution
        resolver = ConflictResolver()
        conflict = await resolver.resolve_manually(
            conflict, resolved_data, user_id, reason
        )
        
        self._update_stats("resolved", conflict)
        self._stats["pending_manual"] -= 1
        await self._emit_event("conflict_resolved", conflict)
        
        return conflict
    
    def get_conflict(self, conflict_id: str) -> Optional[ConflictRecord]:
        """Get a conflict by ID."""
        return self._conflicts.get(conflict_id)
    
    def get_pending_conflicts(self) -> List[ConflictRecord]:
        """Get all pending manual conflicts."""
        return [
            c for c in self._conflicts.values()
            if c.status == ConflictStatus.PENDING_MANUAL
        ]
    
    def get_conflicts_by_table(self, table: str) -> List[ConflictRecord]:
        """Get conflicts for a specific table."""
        return [
            c for c in self._conflicts.values()
            if c.context.table == table
        ]
    
    def _update_stats(self, event: str, conflict: ConflictRecord) -> None:
        """Update statistics."""
        if event == "detected":
            self._stats["total_detected"] += 1
            
            # By type
            type_key = conflict.conflict_type.value
            self._stats["by_type"][type_key] = self._stats["by_type"].get(type_key, 0) + 1
            
            # By table
            table = conflict.context.table
            self._stats["by_table"][table] = self._stats["by_table"].get(table, 0) + 1
        
        elif event == "resolved":
            self._stats["total_resolved"] += 1
        
        elif event == "failed":
            self._stats["total_failed"] += 1
        
        elif event == "pending":
            self._stats["pending_manual"] += 1
    
    async def _emit_event(self, event: str, conflict: ConflictRecord) -> None:
        """Emit event to handlers."""
        handlers = self._handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(conflict)
                else:
                    handler(conflict)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get conflict statistics."""
        return {
            **self._stats,
            "resolution_rate": (
                self._stats["total_resolved"] / self._stats["total_detected"]
                if self._stats["total_detected"] > 0 else 0
            )
        }


# Global conflict manager
conflict_manager = ConflictManager()


__all__ = [
    "ConflictType",
    "ResolutionStrategy",
    "ConflictStatus",
    "ConflictContext",
    "ConflictRecord",
    "ResolutionPolicy",
    "ConflictDetector",
    "ConflictResolver",
    "ConflictManager",
    "conflict_manager",
]
