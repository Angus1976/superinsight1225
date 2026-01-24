"""Annotation Audit Service for AI annotation operation tracking.

This module provides comprehensive audit logging for AI annotation operations:
- Complete annotation operation history logging
- Cryptographic integrity verification (HMAC)
- Audit log filtering and querying
- Export functionality (CSV, JSON)
- User activity tracking
- Compliance reporting

Requirements:
- 7.1: Comprehensive audit logging for annotations
- 7.4: Annotation history and versioning
- 7.5: Annotation export with metadata
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


class AnnotationOperationType(str, Enum):
    """Type of annotation operation."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    PRE_ANNOTATE = "pre_annotate"
    VALIDATE = "validate"
    EXPORT = "export"
    ROLLBACK = "rollback"


class AnnotationObjectType(str, Enum):
    """Type of annotation object."""
    ANNOTATION = "annotation"
    TASK = "task"
    PROJECT = "project"
    SUGGESTION = "suggestion"
    QUALITY_REPORT = "quality_report"
    BATCH_JOB = "batch_job"


@dataclass
class AnnotationAuditEntry:
    """Single annotation audit log entry."""
    log_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    operation_type: AnnotationOperationType = AnnotationOperationType.UPDATE
    object_type: AnnotationObjectType = AnnotationObjectType.ANNOTATION

    # Affected objects
    object_id: UUID = field(default_factory=uuid4)
    object_name: Optional[str] = None
    project_id: Optional[UUID] = None

    # Change details
    before_state: Dict[str, Any] = field(default_factory=dict)
    after_state: Dict[str, Any] = field(default_factory=dict)
    operation_description: str = ""

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

    # AI-specific metadata
    ai_confidence: Optional[float] = None
    ai_model: Optional[str] = None
    ai_method: Optional[str] = None

    # Integrity
    hmac_signature: Optional[str] = None


@dataclass
class AnnotationAuditFilter:
    """Filter for annotation audit log queries."""
    tenant_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    operation_type: Optional[AnnotationOperationType] = None
    object_type: Optional[AnnotationObjectType] = None
    project_id: Optional[UUID] = None
    object_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


@dataclass
class AnnotationVersion:
    """Annotation version information."""
    version_id: UUID = field(default_factory=uuid4)
    annotation_id: UUID = field(default_factory=uuid4)
    version_number: int = 1
    created_by: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    annotation_data: Dict[str, Any] = field(default_factory=dict)
    change_description: str = ""
    log_entry_id: UUID = field(default_factory=uuid4)


class AnnotationAuditService:
    """Service for auditing annotation operations with integrity verification."""

    def __init__(self, secret_key: str = "annotation_audit_secret_key"):
        """Initialize annotation audit service.

        Args:
            secret_key: Secret key for HMAC signature generation
        """
        self._logs: Dict[UUID, AnnotationAuditEntry] = {}
        self._versions: Dict[UUID, List[AnnotationVersion]] = {}
        self._secret_key = secret_key.encode()
        self._lock = asyncio.Lock()

        # Indexes for efficient querying
        self._tenant_index: Dict[UUID, List[UUID]] = {}
        self._user_index: Dict[UUID, List[UUID]] = {}
        self._project_index: Dict[UUID, List[UUID]] = {}
        self._object_index: Dict[UUID, List[UUID]] = {}
        self._timestamp_index: List[Tuple[datetime, UUID]] = []

    async def log_operation(
        self,
        tenant_id: UUID,
        user_id: UUID,
        operation_type: AnnotationOperationType,
        object_type: AnnotationObjectType,
        object_id: UUID,
        object_name: Optional[str] = None,
        project_id: Optional[UUID] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        operation_description: str = "",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        ai_confidence: Optional[float] = None,
        ai_model: Optional[str] = None,
        ai_method: Optional[str] = None
    ) -> AnnotationAuditEntry:
        """Log an annotation operation to the audit log.

        Args:
            tenant_id: Tenant ID
            user_id: User who performed the operation
            operation_type: Type of operation
            object_type: Type of object affected
            object_id: ID of affected object
            object_name: Name of affected object
            project_id: Project ID (if applicable)
            before_state: State before operation
            after_state: State after operation
            operation_description: Description of operation
            ip_address: User's IP address
            user_agent: User's browser/client
            session_id: Session identifier
            ai_confidence: AI confidence score (if applicable)
            ai_model: AI model used (if applicable)
            ai_method: AI method used (if applicable)

        Returns:
            Created audit log entry
        """
        async with self._lock:
            entry = AnnotationAuditEntry(
                tenant_id=tenant_id,
                user_id=user_id,
                operation_type=operation_type,
                object_type=object_type,
                object_id=object_id,
                object_name=object_name,
                project_id=project_id,
                before_state=before_state or {},
                after_state=after_state or {},
                operation_description=operation_description,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                ai_confidence=ai_confidence,
                ai_model=ai_model,
                ai_method=ai_method
            )

            # Generate HMAC signature for integrity
            entry.hmac_signature = self._generate_hmac(entry)

            # Store log entry
            self._logs[entry.log_id] = entry

            # Update indexes
            if tenant_id not in self._tenant_index:
                self._tenant_index[tenant_id] = []
            self._tenant_index[tenant_id].append(entry.log_id)

            if user_id not in self._user_index:
                self._user_index[user_id] = []
            self._user_index[user_id].append(entry.log_id)

            if project_id and project_id not in self._project_index:
                self._project_index[project_id] = []
            if project_id:
                self._project_index[project_id].append(entry.log_id)

            if object_id not in self._object_index:
                self._object_index[object_id] = []
            self._object_index[object_id].append(entry.log_id)

            self._timestamp_index.append((entry.timestamp, entry.log_id))
            self._timestamp_index.sort(key=lambda x: x[0])

            # Create version if it's an annotation update
            if object_type == AnnotationObjectType.ANNOTATION and operation_type in [
                AnnotationOperationType.CREATE,
                AnnotationOperationType.UPDATE,
                AnnotationOperationType.SUBMIT
            ]:
                await self._create_version(
                    annotation_id=object_id,
                    created_by=user_id,
                    annotation_data=after_state,
                    change_description=operation_description,
                    log_entry_id=entry.log_id
                )

            return entry

    def _generate_hmac(self, entry: AnnotationAuditEntry) -> str:
        """Generate HMAC signature for log entry.

        Args:
            entry: Log entry

        Returns:
            HMAC signature as hex string
        """
        # Create canonical representation for signing
        canonical_data = {
            "log_id": str(entry.log_id),
            "tenant_id": str(entry.tenant_id),
            "user_id": str(entry.user_id),
            "operation_type": entry.operation_type.value,
            "object_type": entry.object_type.value,
            "object_id": str(entry.object_id),
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
        filter: AnnotationAuditFilter
    ) -> List[AnnotationAuditEntry]:
        """Get audit logs with filtering.

        Args:
            filter: Filter criteria

        Returns:
            List of matching log entries
        """
        async with self._lock:
            # Start with all logs
            candidate_log_ids = set(self._logs.keys())

            # Apply tenant filter (required for multi-tenant isolation)
            if filter.tenant_id:
                tenant_logs = set(self._tenant_index.get(filter.tenant_id, []))
                candidate_log_ids &= tenant_logs

            # Apply user filter
            if filter.user_id:
                user_logs = set(self._user_index.get(filter.user_id, []))
                candidate_log_ids &= user_logs

            # Apply project filter
            if filter.project_id:
                project_logs = set(self._project_index.get(filter.project_id, []))
                candidate_log_ids &= project_logs

            # Apply object filter
            if filter.object_id:
                object_logs = set(self._object_index.get(filter.object_id, []))
                candidate_log_ids &= object_logs

            # Get log entries
            results = []
            for log_id in candidate_log_ids:
                entry = self._logs[log_id]

                # Apply additional filters
                if filter.operation_type and entry.operation_type != filter.operation_type:
                    continue

                if filter.object_type and entry.object_type != filter.object_type:
                    continue

                if filter.start_date and entry.timestamp < filter.start_date:
                    continue

                if filter.end_date and entry.timestamp > filter.end_date:
                    continue

                results.append(entry)

            # Sort by timestamp (newest first)
            results.sort(key=lambda e: e.timestamp, reverse=True)

            # Apply pagination
            start = filter.offset
            end = start + filter.limit
            return results[start:end]

    async def get_log(self, log_id: UUID) -> Optional[AnnotationAuditEntry]:
        """Get a specific log entry.

        Args:
            log_id: Log entry ID

        Returns:
            Log entry or None
        """
        async with self._lock:
            return self._logs.get(log_id)

    async def _create_version(
        self,
        annotation_id: UUID,
        created_by: UUID,
        annotation_data: Dict[str, Any],
        change_description: str,
        log_entry_id: UUID
    ) -> AnnotationVersion:
        """Create a new annotation version.

        Args:
            annotation_id: Annotation ID
            created_by: User who created this version
            annotation_data: Annotation data
            change_description: Description of changes
            log_entry_id: Associated log entry ID

        Returns:
            Created version
        """
        # Get existing versions
        versions = self._versions.get(annotation_id, [])
        version_number = len(versions) + 1

        version = AnnotationVersion(
            annotation_id=annotation_id,
            version_number=version_number,
            created_by=created_by,
            annotation_data=annotation_data,
            change_description=change_description,
            log_entry_id=log_entry_id
        )

        if annotation_id not in self._versions:
            self._versions[annotation_id] = []
        self._versions[annotation_id].append(version)

        return version

    async def get_annotation_versions(
        self,
        annotation_id: UUID,
        limit: int = 50
    ) -> List[AnnotationVersion]:
        """Get version history for an annotation.

        Args:
            annotation_id: Annotation ID
            limit: Maximum number of versions to return

        Returns:
            List of versions (newest first)
        """
        async with self._lock:
            versions = self._versions.get(annotation_id, [])
            # Return newest first
            return list(reversed(versions))[:limit]

    async def get_version(
        self,
        annotation_id: UUID,
        version_number: int
    ) -> Optional[AnnotationVersion]:
        """Get a specific version of an annotation.

        Args:
            annotation_id: Annotation ID
            version_number: Version number

        Returns:
            Version or None
        """
        async with self._lock:
            versions = self._versions.get(annotation_id, [])
            for version in versions:
                if version.version_number == version_number:
                    return version
            return None

    async def export_logs(
        self,
        filter: AnnotationAuditFilter,
        format: str = "json",
        include_metadata: bool = True
    ) -> str:
        """Export audit logs with metadata.

        Args:
            filter: Filter criteria
            format: Export format ("json" or "csv")
            include_metadata: Include AI metadata in export

        Returns:
            Exported data as string
        """
        logs = await self.get_logs(filter)

        if format == "json":
            return self._export_json(logs, include_metadata)
        elif format == "csv":
            return self._export_csv(logs, include_metadata)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_json(
        self,
        logs: List[AnnotationAuditEntry],
        include_metadata: bool
    ) -> str:
        """Export logs as JSON.

        Args:
            logs: Log entries
            include_metadata: Include AI metadata

        Returns:
            JSON string
        """
        data = []
        for log in logs:
            log_dict = asdict(log)

            # Convert UUIDs and datetime to strings
            log_dict["log_id"] = str(log_dict["log_id"])
            log_dict["tenant_id"] = str(log_dict["tenant_id"])
            log_dict["user_id"] = str(log_dict["user_id"])
            log_dict["object_id"] = str(log_dict["object_id"])
            if log_dict["project_id"]:
                log_dict["project_id"] = str(log_dict["project_id"])
            log_dict["timestamp"] = log_dict["timestamp"].isoformat()

            # Remove metadata if not requested
            if not include_metadata:
                log_dict.pop("ai_confidence", None)
                log_dict.pop("ai_model", None)
                log_dict.pop("ai_method", None)
                log_dict.pop("hmac_signature", None)

            data.append(log_dict)

        return json.dumps(data, indent=2)

    def _export_csv(
        self,
        logs: List[AnnotationAuditEntry],
        include_metadata: bool
    ) -> str:
        """Export logs as CSV.

        Args:
            logs: Log entries
            include_metadata: Include AI metadata

        Returns:
            CSV string
        """
        lines = []

        # Header
        header = [
            "log_id", "tenant_id", "user_id", "operation_type", "object_type",
            "object_id", "object_name", "project_id", "timestamp",
            "operation_description", "ip_address"
        ]
        if include_metadata:
            header.extend(["ai_confidence", "ai_model", "ai_method"])

        lines.append(",".join(header))

        # Rows
        for log in logs:
            row = [
                str(log.log_id),
                str(log.tenant_id),
                str(log.user_id),
                log.operation_type.value,
                log.object_type.value,
                str(log.object_id),
                log.object_name or "",
                str(log.project_id) if log.project_id else "",
                log.timestamp.isoformat(),
                log.operation_description.replace(",", ";"),  # Escape commas
                log.ip_address or ""
            ]

            if include_metadata:
                row.extend([
                    str(log.ai_confidence) if log.ai_confidence else "",
                    log.ai_model or "",
                    log.ai_method or ""
                ])

            lines.append(",".join(row))

        return "\n".join(lines)

    async def get_user_activity(
        self,
        tenant_id: UUID,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AnnotationAuditEntry]:
        """Get activity log for a user.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum entries to return

        Returns:
            List of log entries
        """
        filter = AnnotationAuditFilter(
            tenant_id=tenant_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return await self.get_logs(filter)

    async def get_project_activity(
        self,
        tenant_id: UUID,
        project_id: UUID,
        limit: int = 100
    ) -> List[AnnotationAuditEntry]:
        """Get activity log for a project.

        Args:
            tenant_id: Tenant ID
            project_id: Project ID
            limit: Maximum entries to return

        Returns:
            List of log entries
        """
        filter = AnnotationAuditFilter(
            tenant_id=tenant_id,
            project_id=project_id,
            limit=limit
        )
        return await self.get_logs(filter)

    async def get_annotation_history(
        self,
        tenant_id: UUID,
        annotation_id: UUID,
        limit: int = 50
    ) -> List[AnnotationAuditEntry]:
        """Get complete history for an annotation.

        Args:
            tenant_id: Tenant ID
            annotation_id: Annotation ID
            limit: Maximum entries to return

        Returns:
            List of log entries in chronological order
        """
        filter = AnnotationAuditFilter(
            tenant_id=tenant_id,
            object_id=annotation_id,
            object_type=AnnotationObjectType.ANNOTATION,
            limit=limit
        )
        logs = await self.get_logs(filter)

        # Return in chronological order (oldest first)
        return list(reversed(logs))

    async def get_statistics(
        self,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit log statistics.

        Args:
            tenant_id: Tenant ID
            start_date: Start date filter
            end_date: End date filter

        Returns:
            Dictionary of statistics
        """
        filter = AnnotationAuditFilter(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            limit=100000  # Get all matching logs
        )
        logs = await self.get_logs(filter)

        # Calculate statistics
        operation_counts = {}
        object_type_counts = {}
        user_activity = {}
        ai_operations = 0

        for log in logs:
            # Count by operation type
            operation_counts[log.operation_type.value] = \
                operation_counts.get(log.operation_type.value, 0) + 1

            # Count by object type
            object_type_counts[log.object_type.value] = \
                object_type_counts.get(log.object_type.value, 0) + 1

            # Count by user
            user_id_str = str(log.user_id)
            user_activity[user_id_str] = user_activity.get(user_id_str, 0) + 1

            # Count AI operations
            if log.ai_model or log.ai_method:
                ai_operations += 1

        return {
            "total_operations": len(logs),
            "operation_distribution": operation_counts,
            "object_type_distribution": object_type_counts,
            "active_users": len(user_activity),
            "most_active_user": max(user_activity.items(), key=lambda x: x[1])[0] if user_activity else None,
            "ai_assisted_operations": ai_operations,
            "ai_assistance_rate": (ai_operations / len(logs) * 100) if logs else 0
        }


# Global instance
_annotation_audit_service: Optional[AnnotationAuditService] = None
_audit_lock = asyncio.Lock()


async def get_annotation_audit_service(
    secret_key: Optional[str] = None
) -> AnnotationAuditService:
    """Get or create the global annotation audit service.

    Args:
        secret_key: Optional secret key for HMAC

    Returns:
        Annotation audit service instance
    """
    global _annotation_audit_service

    async with _audit_lock:
        if _annotation_audit_service is None:
            _annotation_audit_service = AnnotationAuditService(
                secret_key=secret_key or "annotation_audit_secret_key"
            )
        return _annotation_audit_service


async def reset_annotation_audit_service():
    """Reset the global annotation audit service (for testing)."""
    global _annotation_audit_service

    async with _audit_lock:
        _annotation_audit_service = None
