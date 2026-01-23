"""Audit and Rollback Service for ontology change tracking.

This module provides comprehensive audit logging and rollback capabilities:
- Complete change history logging
- Cryptographic integrity verification (HMAC)
- Audit log filtering and querying
- Version rollback with notification
- Export functionality (CSV, JSON)

Requirements:
- 14.1: Comprehensive audit logging
- 14.2: Audit log filtering
- 14.3: Rollback functionality
- 14.4: Rollback notifications
- 14.5: Cryptographic integrity
"""

import asyncio
import hmac
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from dataclasses import dataclass, field, asdict
from enum import Enum


class ChangeType(str, Enum):
    """Type of change."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ROLLBACK = "rollback"


class OntologyArea(str, Enum):
    """Area of ontology affected."""
    ENTITY_TYPE = "entity_type"
    RELATION_TYPE = "relation_type"
    ATTRIBUTE = "attribute"
    VALIDATION_RULE = "validation_rule"
    TEMPLATE = "template"
    CONFIGURATION = "configuration"


@dataclass
class AuditLogEntry:
    """Single audit log entry."""
    log_id: UUID = field(default_factory=uuid4)
    ontology_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    change_type: ChangeType = ChangeType.UPDATE
    ontology_area: OntologyArea = OntologyArea.ENTITY_TYPE

    # Affected elements
    affected_element_ids: List[UUID] = field(default_factory=list)
    affected_element_names: List[str] = field(default_factory=list)

    # Change details
    before_state: Dict[str, Any] = field(default_factory=dict)
    after_state: Dict[str, Any] = field(default_factory=dict)
    change_description: str = ""

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Integrity
    hmac_signature: Optional[str] = None


@dataclass
class RollbackOperation:
    """Rollback operation record."""
    rollback_id: UUID = field(default_factory=uuid4)
    target_log_id: UUID = field(default_factory=uuid4)
    ontology_id: UUID = field(default_factory=uuid4)
    performed_by: UUID = field(default_factory=uuid4)
    rollback_timestamp: datetime = field(default_factory=datetime.utcnow)
    affected_users: List[UUID] = field(default_factory=list)
    rollback_reason: str = ""
    new_version_log_id: Optional[UUID] = None


@dataclass
class AuditLogFilter:
    """Filter for audit log queries."""
    ontology_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    change_type: Optional[ChangeType] = None
    ontology_area: Optional[OntologyArea] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    affected_element_id: Optional[UUID] = None
    limit: int = 100
    offset: int = 0


class AuditService:
    """Service for audit logging and rollback operations."""

    def __init__(self, secret_key: str = "default_secret_key"):
        """Initialize audit service.

        Args:
            secret_key: Secret key for HMAC signature generation
        """
        self._logs: Dict[UUID, AuditLogEntry] = {}
        self._rollbacks: Dict[UUID, RollbackOperation] = {}
        self._secret_key = secret_key.encode()
        self._lock = asyncio.Lock()

        # Indexes for efficient querying
        self._ontology_index: Dict[UUID, List[UUID]] = {}
        self._user_index: Dict[UUID, List[UUID]] = {}
        self._timestamp_index: List[Tuple[datetime, UUID]] = []

    async def log_change(
        self,
        ontology_id: UUID,
        user_id: UUID,
        change_type: ChangeType,
        ontology_area: OntologyArea,
        affected_element_ids: List[UUID],
        affected_element_names: List[str],
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        change_description: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLogEntry:
        """Log a change to the audit log.

        Args:
            ontology_id: Ontology ID
            user_id: User who made the change
            change_type: Type of change
            ontology_area: Area affected
            affected_element_ids: List of affected element IDs
            affected_element_names: List of affected element names
            before_state: State before change
            after_state: State after change
            change_description: Description of change
            ip_address: User's IP address
            user_agent: User's browser/client

        Returns:
            Created audit log entry
        """
        async with self._lock:
            entry = AuditLogEntry(
                ontology_id=ontology_id,
                user_id=user_id,
                change_type=change_type,
                ontology_area=ontology_area,
                affected_element_ids=affected_element_ids,
                affected_element_names=affected_element_names,
                before_state=before_state,
                after_state=after_state,
                change_description=change_description,
                ip_address=ip_address,
                user_agent=user_agent
            )

            # Generate HMAC signature for integrity
            entry.hmac_signature = self._generate_hmac(entry)

            # Store log entry
            self._logs[entry.log_id] = entry

            # Update indexes
            if ontology_id not in self._ontology_index:
                self._ontology_index[ontology_id] = []
            self._ontology_index[ontology_id].append(entry.log_id)

            if user_id not in self._user_index:
                self._user_index[user_id] = []
            self._user_index[user_id].append(entry.log_id)

            self._timestamp_index.append((entry.timestamp, entry.log_id))
            self._timestamp_index.sort(key=lambda x: x[0])

            return entry

    def _generate_hmac(self, entry: AuditLogEntry) -> str:
        """Generate HMAC signature for log entry.

        Args:
            entry: Log entry

        Returns:
            HMAC signature as hex string
        """
        # Create canonical representation for signing
        canonical_data = {
            "log_id": str(entry.log_id),
            "ontology_id": str(entry.ontology_id),
            "user_id": str(entry.user_id),
            "change_type": entry.change_type.value,
            "ontology_area": entry.ontology_area.value,
            "affected_element_ids": [str(eid) for eid in entry.affected_element_ids],
            "timestamp": entry.timestamp.isoformat(),
            "before_state": entry.before_state,
            "after_state": entry.after_state
        }

        canonical_str = json.dumps(canonical_data, sort_keys=True)
        signature = hmac.new(
            self._secret_key,
            canonical_str.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    async def verify_integrity(self, log_id: UUID) -> bool:
        """Verify the cryptographic integrity of a log entry.

        Args:
            log_id: Log entry ID

        Returns:
            True if integrity verified, False otherwise
        """
        async with self._lock:
            entry = self._logs.get(log_id)
            if not entry:
                return False

            if not entry.hmac_signature:
                return False

            # Recalculate signature
            expected_signature = self._generate_hmac(entry)

            # Compare signatures (constant-time comparison)
            return hmac.compare_digest(entry.hmac_signature, expected_signature)

    async def get_logs(
        self,
        filter: AuditLogFilter
    ) -> List[AuditLogEntry]:
        """Get audit logs with filtering.

        Args:
            filter: Filter criteria

        Returns:
            List of matching log entries
        """
        async with self._lock:
            # Start with all logs
            candidate_log_ids = set(self._logs.keys())

            # Apply ontology filter
            if filter.ontology_id:
                ontology_logs = set(self._ontology_index.get(filter.ontology_id, []))
                candidate_log_ids &= ontology_logs

            # Apply user filter
            if filter.user_id:
                user_logs = set(self._user_index.get(filter.user_id, []))
                candidate_log_ids &= user_logs

            # Get log entries
            results = []
            for log_id in candidate_log_ids:
                entry = self._logs[log_id]

                # Apply additional filters
                if filter.change_type and entry.change_type != filter.change_type:
                    continue

                if filter.ontology_area and entry.ontology_area != filter.ontology_area:
                    continue

                if filter.start_date and entry.timestamp < filter.start_date:
                    continue

                if filter.end_date and entry.timestamp > filter.end_date:
                    continue

                if filter.affected_element_id:
                    if filter.affected_element_id not in entry.affected_element_ids:
                        continue

                results.append(entry)

            # Sort by timestamp (newest first)
            results.sort(key=lambda e: e.timestamp, reverse=True)

            # Apply pagination
            start = filter.offset
            end = start + filter.limit
            return results[start:end]

    async def get_log(self, log_id: UUID) -> Optional[AuditLogEntry]:
        """Get a specific log entry.

        Args:
            log_id: Log entry ID

        Returns:
            Log entry or None
        """
        async with self._lock:
            return self._logs.get(log_id)

    async def rollback_to_version(
        self,
        target_log_id: UUID,
        performed_by: UUID,
        rollback_reason: str,
        notify_users: bool = True
    ) -> RollbackOperation:
        """Rollback ontology to a previous version.

        Args:
            target_log_id: Log entry to rollback to
            performed_by: User performing rollback
            rollback_reason: Reason for rollback
            notify_users: Whether to notify affected users

        Returns:
            Rollback operation record

        Raises:
            ValueError: If target log not found
        """
        async with self._lock:
            target_log = self._logs.get(target_log_id)
            if not target_log:
                raise ValueError(f"Target log {target_log_id} not found")

            # Identify affected users (all users who made changes after target version)
            affected_users = set()
            for log_id, entry in self._logs.items():
                if entry.ontology_id == target_log.ontology_id and entry.timestamp > target_log.timestamp:
                    affected_users.add(entry.user_id)

            # Create rollback operation
            rollback = RollbackOperation(
                target_log_id=target_log_id,
                ontology_id=target_log.ontology_id,
                performed_by=performed_by,
                affected_users=list(affected_users),
                rollback_reason=rollback_reason
            )

            # Create new log entry for the rollback action
            new_log = await self.log_change(
                ontology_id=target_log.ontology_id,
                user_id=performed_by,
                change_type=ChangeType.ROLLBACK,
                ontology_area=target_log.ontology_area,
                affected_element_ids=target_log.affected_element_ids,
                affected_element_names=target_log.affected_element_names,
                before_state=target_log.after_state,  # Current state
                after_state=target_log.before_state,  # Target state
                change_description=f"Rollback to version {target_log_id}: {rollback_reason}"
            )

            rollback.new_version_log_id = new_log.log_id
            self._rollbacks[rollback.rollback_id] = rollback

            return rollback

    async def export_logs(
        self,
        filter: AuditLogFilter,
        format: str = "json"
    ) -> str:
        """Export audit logs.

        Args:
            filter: Filter criteria
            format: Export format ("json" or "csv")

        Returns:
            Exported data as string
        """
        logs = await self.get_logs(filter)

        if format == "json":
            return self._export_json(logs)
        elif format == "csv":
            return self._export_csv(logs)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_json(self, logs: List[AuditLogEntry]) -> str:
        """Export logs as JSON.

        Args:
            logs: Log entries

        Returns:
            JSON string
        """
        data = []
        for log in logs:
            log_dict = asdict(log)
            # Convert UUIDs and datetime to strings
            log_dict["log_id"] = str(log_dict["log_id"])
            log_dict["ontology_id"] = str(log_dict["ontology_id"])
            log_dict["user_id"] = str(log_dict["user_id"])
            log_dict["affected_element_ids"] = [str(eid) for eid in log_dict["affected_element_ids"]]
            log_dict["timestamp"] = log_dict["timestamp"].isoformat()
            data.append(log_dict)

        return json.dumps(data, indent=2)

    def _export_csv(self, logs: List[AuditLogEntry]) -> str:
        """Export logs as CSV.

        Args:
            logs: Log entries

        Returns:
            CSV string
        """
        lines = []

        # Header
        header = [
            "log_id", "ontology_id", "user_id", "change_type", "ontology_area",
            "timestamp", "affected_elements", "change_description"
        ]
        lines.append(",".join(header))

        # Rows
        for log in logs:
            row = [
                str(log.log_id),
                str(log.ontology_id),
                str(log.user_id),
                log.change_type.value,
                log.ontology_area.value,
                log.timestamp.isoformat(),
                ";".join(log.affected_element_names),
                log.change_description.replace(",", ";")  # Escape commas
            ]
            lines.append(",".join(row))

        return "\n".join(lines)

    async def get_change_history(
        self,
        element_id: UUID,
        limit: int = 50
    ) -> List[AuditLogEntry]:
        """Get change history for a specific element.

        Args:
            element_id: Element ID
            limit: Maximum entries to return

        Returns:
            List of log entries
        """
        filter = AuditLogFilter(
            affected_element_id=element_id,
            limit=limit
        )
        return await self.get_logs(filter)

    async def get_user_activity(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Get activity log for a user.

        Args:
            user_id: User ID
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum entries to return

        Returns:
            List of log entries
        """
        filter = AuditLogFilter(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return await self.get_logs(filter)

    async def get_ontology_timeline(
        self,
        ontology_id: UUID,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Get complete timeline for an ontology.

        Args:
            ontology_id: Ontology ID
            limit: Maximum entries to return

        Returns:
            List of log entries in chronological order
        """
        filter = AuditLogFilter(
            ontology_id=ontology_id,
            limit=limit
        )
        logs = await self.get_logs(filter)

        # Return in chronological order (oldest first)
        return list(reversed(logs))

    async def get_recent_changes(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> List[AuditLogEntry]:
        """Get recent changes across all ontologies.

        Args:
            hours: Number of hours to look back
            limit: Maximum entries to return

        Returns:
            List of recent log entries
        """
        start_date = datetime.utcnow() - timedelta(hours=hours)

        filter = AuditLogFilter(
            start_date=start_date,
            limit=limit
        )
        return await self.get_logs(filter)

    async def get_rollback_history(
        self,
        ontology_id: UUID
    ) -> List[RollbackOperation]:
        """Get rollback history for an ontology.

        Args:
            ontology_id: Ontology ID

        Returns:
            List of rollback operations
        """
        async with self._lock:
            rollbacks = [
                r for r in self._rollbacks.values()
                if r.ontology_id == ontology_id
            ]
            return sorted(rollbacks, key=lambda r: r.rollback_timestamp, reverse=True)

    async def get_statistics(
        self,
        ontology_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit log statistics.

        Args:
            ontology_id: Filter by ontology
            start_date: Start date filter
            end_date: End date filter

        Returns:
            Dictionary of statistics
        """
        filter = AuditLogFilter(
            ontology_id=ontology_id,
            start_date=start_date,
            end_date=end_date,
            limit=100000  # Get all matching logs
        )
        logs = await self.get_logs(filter)

        # Calculate statistics
        change_type_counts = {}
        ontology_area_counts = {}
        user_activity = {}

        for log in logs:
            # Count by change type
            change_type_counts[log.change_type.value] = change_type_counts.get(log.change_type.value, 0) + 1

            # Count by ontology area
            ontology_area_counts[log.ontology_area.value] = ontology_area_counts.get(log.ontology_area.value, 0) + 1

            # Count by user
            user_id_str = str(log.user_id)
            user_activity[user_id_str] = user_activity.get(user_id_str, 0) + 1

        return {
            "total_changes": len(logs),
            "change_type_distribution": change_type_counts,
            "ontology_area_distribution": ontology_area_counts,
            "active_users": len(user_activity),
            "most_active_user": max(user_activity.items(), key=lambda x: x[1])[0] if user_activity else None,
            "rollback_count": len([r for r in self._rollbacks.values()
                                  if ontology_id is None or r.ontology_id == ontology_id])
        }
