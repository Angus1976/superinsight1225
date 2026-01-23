"""Collaboration Service for real-time ontology editing.

This module provides real-time collaboration capabilities for ontology editing:
- Session management with presence tracking
- Element locking mechanism with TTL
- Real-time change broadcasting via Redis pub/sub
- Conflict detection and resolution
- Version history management

Requirements:
- 1.4: Concurrent edit conflict detection
- 7.1: Real-time collaboration sessions
- 7.2: Change broadcasting within 2 seconds
- 7.3: Conflict resolution
- 7.4: Element locking
- 7.5: Version history
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum


class ConflictResolution(str, Enum):
    """Conflict resolution strategies."""
    ACCEPT_THEIRS = "accept_theirs"
    ACCEPT_MINE = "accept_mine"
    MANUAL_MERGE = "manual_merge"


class ChangeType(str, Enum):
    """Types of changes to ontology elements."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOCK = "lock"
    UNLOCK = "unlock"


@dataclass
class Participant:
    """Collaboration session participant."""
    user_id: UUID
    username: str
    email: str
    joined_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


@dataclass
class ElementLock:
    """Lock on an ontology element."""
    lock_id: UUID = field(default_factory=uuid4)
    element_id: UUID = field(default_factory=uuid4)
    element_type: str = ""  # "entity_type", "relation_type", "attribute"
    locked_by: UUID = field(default_factory=uuid4)  # user_id
    locked_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=5))
    session_id: UUID = field(default_factory=uuid4)


@dataclass
class Change:
    """Change to an ontology element."""
    change_id: UUID = field(default_factory=uuid4)
    element_id: UUID = field(default_factory=uuid4)
    element_type: str = ""
    change_type: ChangeType = ChangeType.UPDATE
    user_id: UUID = field(default_factory=uuid4)
    username: str = ""
    session_id: UUID = field(default_factory=uuid4)
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: int = 1


@dataclass
class Conflict:
    """Conflict between concurrent changes."""
    conflict_id: UUID = field(default_factory=uuid4)
    element_id: UUID = field(default_factory=uuid4)
    element_type: str = ""
    change1: Change = field(default_factory=lambda: Change())
    change2: Change = field(default_factory=lambda: Change())
    detected_at: datetime = field(default_factory=datetime.utcnow)
    is_resolved: bool = False
    resolution: Optional[ConflictResolution] = None
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None


@dataclass
class CollaborationSession:
    """Real-time collaboration session."""
    session_id: UUID = field(default_factory=uuid4)
    ontology_id: UUID = field(default_factory=uuid4)
    name: str = ""
    created_by: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    participants: Dict[UUID, Participant] = field(default_factory=dict)  # user_id -> Participant
    active_locks: Dict[UUID, ElementLock] = field(default_factory=dict)  # element_id -> ElementLock
    changes: List[Change] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    is_active: bool = True


@dataclass
class Version:
    """Version of an ontology element."""
    version_id: UUID = field(default_factory=uuid4)
    element_id: UUID = field(default_factory=uuid4)
    element_type: str = ""
    version_number: int = 1
    data: Dict[str, Any] = field(default_factory=dict)
    change_summary: str = ""
    created_by: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    parent_version_id: Optional[UUID] = None


class CollaborationService:
    """Service for real-time ontology collaboration."""

    def __init__(self):
        """Initialize collaboration service."""
        self._sessions: Dict[UUID, CollaborationSession] = {}
        self._locks: Dict[UUID, ElementLock] = {}  # element_id -> ElementLock
        self._versions: Dict[UUID, List[Version]] = {}  # element_id -> List[Version]
        self._lock = asyncio.Lock()

        # Configuration
        self._lock_ttl = 300  # 5 minutes
        self._heartbeat_timeout = 60  # 1 minute
        self._broadcast_timeout = 2.0  # 2 seconds

    async def create_session(
        self,
        ontology_id: UUID,
        name: str,
        created_by: UUID,
        creator_username: str,
        creator_email: str
    ) -> CollaborationSession:
        """Create a new collaboration session.

        Args:
            ontology_id: ID of the ontology being edited
            name: Session name
            created_by: User ID of creator
            creator_username: Creator username
            creator_email: Creator email

        Returns:
            Created collaboration session
        """
        async with self._lock:
            session = CollaborationSession(
                ontology_id=ontology_id,
                name=name,
                created_by=created_by
            )

            # Add creator as first participant
            creator = Participant(
                user_id=created_by,
                username=creator_username,
                email=creator_email
            )
            session.participants[created_by] = creator

            self._sessions[session.session_id] = session

            return session

    async def join_session(
        self,
        session_id: UUID,
        user_id: UUID,
        username: str,
        email: str
    ) -> Optional[Participant]:
        """Join an existing collaboration session.

        Args:
            session_id: Session ID
            user_id: User ID
            username: Username
            email: Email

        Returns:
            Participant object if successful, None if session not found
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session or not session.is_active:
                return None

            # Check if user already in session
            if user_id in session.participants:
                participant = session.participants[user_id]
                participant.is_active = True
                participant.last_heartbeat = datetime.utcnow()
                return participant

            # Add new participant
            participant = Participant(
                user_id=user_id,
                username=username,
                email=email
            )
            session.participants[user_id] = participant

            return participant

    async def leave_session(
        self,
        session_id: UUID,
        user_id: UUID
    ) -> bool:
        """Leave a collaboration session.

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            True if successful
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False

            # Mark participant as inactive
            if user_id in session.participants:
                session.participants[user_id].is_active = False

            # Release all locks held by this user in this session
            locks_to_release = [
                lock for lock in session.active_locks.values()
                if lock.locked_by == user_id
            ]

            for lock in locks_to_release:
                await self._release_lock_internal(session, lock.element_id)

            return True

    async def lock_element(
        self,
        session_id: UUID,
        element_id: UUID,
        element_type: str,
        user_id: UUID
    ) -> Optional[ElementLock]:
        """Lock an ontology element for editing.

        Args:
            session_id: Session ID
            element_id: Element ID to lock
            element_type: Type of element
            user_id: User ID requesting lock

        Returns:
            ElementLock if successful, None if element is already locked
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session or not session.is_active:
                return None

            # Check if element is already locked
            if element_id in session.active_locks:
                existing_lock = session.active_locks[element_id]

                # Check if lock has expired
                if datetime.utcnow() > existing_lock.expires_at:
                    # Lock expired, release it
                    await self._release_lock_internal(session, element_id)
                else:
                    # Lock still valid
                    if existing_lock.locked_by == user_id:
                        # Same user, extend lock
                        existing_lock.expires_at = datetime.utcnow() + timedelta(seconds=self._lock_ttl)
                        return existing_lock
                    else:
                        # Locked by another user
                        return None

            # Create new lock
            lock = ElementLock(
                element_id=element_id,
                element_type=element_type,
                locked_by=user_id,
                session_id=session_id,
                expires_at=datetime.utcnow() + timedelta(seconds=self._lock_ttl)
            )

            session.active_locks[element_id] = lock
            self._locks[element_id] = lock

            # Broadcast lock event
            await self._broadcast_change(session, Change(
                element_id=element_id,
                element_type=element_type,
                change_type=ChangeType.LOCK,
                user_id=user_id,
                session_id=session_id
            ))

            return lock

    async def unlock_element(
        self,
        session_id: UUID,
        element_id: UUID,
        user_id: UUID
    ) -> bool:
        """Unlock an ontology element.

        Args:
            session_id: Session ID
            element_id: Element ID to unlock
            user_id: User ID requesting unlock

        Returns:
            True if successful
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False

            # Check if element is locked
            if element_id not in session.active_locks:
                return False

            lock = session.active_locks[element_id]

            # Verify user owns the lock
            if lock.locked_by != user_id:
                return False

            # Release lock
            await self._release_lock_internal(session, element_id)

            # Broadcast unlock event
            await self._broadcast_change(session, Change(
                element_id=element_id,
                element_type=lock.element_type,
                change_type=ChangeType.UNLOCK,
                user_id=user_id,
                session_id=session_id
            ))

            return True

    async def _release_lock_internal(
        self,
        session: CollaborationSession,
        element_id: UUID
    ) -> None:
        """Release a lock (internal method, assumes lock is already acquired)."""
        if element_id in session.active_locks:
            del session.active_locks[element_id]
        if element_id in self._locks:
            del self._locks[element_id]

    async def record_change(
        self,
        session_id: UUID,
        element_id: UUID,
        element_type: str,
        change_type: ChangeType,
        user_id: UUID,
        username: str,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None
    ) -> Change:
        """Record a change to an ontology element.

        Args:
            session_id: Session ID
            element_id: Element ID
            element_type: Type of element
            change_type: Type of change
            user_id: User making the change
            username: Username
            before: State before change
            after: State after change

        Returns:
            Change object
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            # Create version
            version_number = len(self._versions.get(element_id, [])) + 1

            change = Change(
                element_id=element_id,
                element_type=element_type,
                change_type=change_type,
                user_id=user_id,
                username=username,
                session_id=session_id,
                before=before,
                after=after,
                version=version_number
            )

            session.changes.append(change)

            # Create version entry
            version = Version(
                element_id=element_id,
                element_type=element_type,
                version_number=version_number,
                data=after or {},
                change_summary=f"{change_type.value} by {username}",
                created_by=user_id
            )

            if element_id not in self._versions:
                self._versions[element_id] = []
            self._versions[element_id].append(version)

            # Detect conflicts
            await self._detect_conflicts(session, change)

            # Broadcast change
            await self._broadcast_change(session, change)

            return change

    async def _detect_conflicts(
        self,
        session: CollaborationSession,
        new_change: Change
    ) -> None:
        """Detect conflicts with concurrent changes.

        Args:
            session: Collaboration session
            new_change: New change to check for conflicts
        """
        # Look for recent changes to the same element by different users
        recent_changes = [
            c for c in session.changes[-10:]  # Check last 10 changes
            if c.element_id == new_change.element_id
            and c.user_id != new_change.user_id
            and (new_change.timestamp - c.timestamp).total_seconds() < 60  # Within 1 minute
        ]

        for other_change in recent_changes:
            # Check if changes conflict
            if self._changes_conflict(new_change, other_change):
                conflict = Conflict(
                    element_id=new_change.element_id,
                    element_type=new_change.element_type,
                    change1=other_change,
                    change2=new_change
                )
                session.conflicts.append(conflict)

    def _changes_conflict(self, change1: Change, change2: Change) -> bool:
        """Check if two changes conflict.

        Args:
            change1: First change
            change2: Second change

        Returns:
            True if changes conflict
        """
        # Both changes modify the same element
        if change1.element_id != change2.element_id:
            return False

        # Both are updates that modify the same fields
        if change1.after and change2.after:
            common_fields = set(change1.after.keys()) & set(change2.after.keys())
            if common_fields:
                # Check if any common field has different values
                for field in common_fields:
                    if change1.after[field] != change2.after[field]:
                        return True

        return False

    async def resolve_conflict(
        self,
        session_id: UUID,
        conflict_id: UUID,
        resolution: ConflictResolution,
        resolved_by: UUID,
        merged_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Resolve a conflict.

        Args:
            session_id: Session ID
            conflict_id: Conflict ID
            resolution: Resolution strategy
            resolved_by: User resolving the conflict
            merged_data: Merged data for manual merge

        Returns:
            True if successful
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False

            # Find conflict
            conflict = next((c for c in session.conflicts if c.conflict_id == conflict_id), None)
            if not conflict or conflict.is_resolved:
                return False

            # Apply resolution
            conflict.is_resolved = True
            conflict.resolution = resolution
            conflict.resolved_by = resolved_by
            conflict.resolved_at = datetime.utcnow()

            # Create resolution change
            if resolution == ConflictResolution.ACCEPT_THEIRS:
                final_data = conflict.change1.after
            elif resolution == ConflictResolution.ACCEPT_MINE:
                final_data = conflict.change2.after
            else:  # MANUAL_MERGE
                final_data = merged_data

            if final_data:
                await self.record_change(
                    session_id=session_id,
                    element_id=conflict.element_id,
                    element_type=conflict.element_type,
                    change_type=ChangeType.UPDATE,
                    user_id=resolved_by,
                    username=session.participants[resolved_by].username if resolved_by in session.participants else "Unknown",
                    before=conflict.change2.before,
                    after=final_data
                )

            return True

    async def _broadcast_change(
        self,
        session: CollaborationSession,
        change: Change
    ) -> None:
        """Broadcast a change to all session participants.

        Args:
            session: Collaboration session
            change: Change to broadcast

        Note: In a real implementation, this would use Redis pub/sub or WebSocket.
        """
        # Simulate broadcast with timeout check
        broadcast_start = datetime.utcnow()

        # In real implementation, publish to Redis channel:
        # await redis.publish(f"collaboration:{session.session_id}", json.dumps(change))

        # For now, just track that broadcast was called
        broadcast_duration = (datetime.utcnow() - broadcast_start).total_seconds()

        # Ensure broadcast is within 2 seconds requirement
        if broadcast_duration > self._broadcast_timeout:
            # Log warning or raise alert
            pass

    async def get_version_history(
        self,
        element_id: UUID,
        limit: int = 10
    ) -> List[Version]:
        """Get version history for an element.

        Args:
            element_id: Element ID
            limit: Maximum number of versions to return

        Returns:
            List of versions, most recent first
        """
        async with self._lock:
            versions = self._versions.get(element_id, [])
            return list(reversed(versions[-limit:]))

    async def restore_version(
        self,
        session_id: UUID,
        element_id: UUID,
        version_number: int,
        user_id: UUID,
        username: str
    ) -> Optional[Version]:
        """Restore an element to a previous version.

        Args:
            session_id: Session ID
            element_id: Element ID
            version_number: Version number to restore
            user_id: User performing restore
            username: Username

        Returns:
            New version created from restoration, or None if failed
        """
        async with self._lock:
            versions = self._versions.get(element_id, [])
            if not versions:
                return None

            # Find target version
            target_version = next((v for v in versions if v.version_number == version_number), None)
            if not target_version:
                return None

            # Create new version from target
            current_version_number = len(versions)
            current_data = versions[-1].data if versions else {}

            change = await self.record_change(
                session_id=session_id,
                element_id=element_id,
                element_type=target_version.element_type,
                change_type=ChangeType.UPDATE,
                user_id=user_id,
                username=username,
                before=current_data,
                after=target_version.data
            )

            # Return the newly created version
            return self._versions[element_id][-1]

    async def get_active_sessions(self) -> List[CollaborationSession]:
        """Get all active collaboration sessions.

        Returns:
            List of active sessions
        """
        async with self._lock:
            return [s for s in self._sessions.values() if s.is_active]

    async def cleanup_expired_locks(self) -> int:
        """Clean up expired locks.

        Returns:
            Number of locks cleaned up
        """
        async with self._lock:
            expired_count = 0
            now = datetime.utcnow()

            for session in self._sessions.values():
                expired_elements = [
                    element_id for element_id, lock in session.active_locks.items()
                    if now > lock.expires_at
                ]

                for element_id in expired_elements:
                    await self._release_lock_internal(session, element_id)
                    expired_count += 1

            return expired_count

    async def cleanup_inactive_participants(self) -> int:
        """Clean up inactive participants (no heartbeat within timeout).

        Returns:
            Number of participants marked inactive
        """
        async with self._lock:
            inactive_count = 0
            now = datetime.utcnow()

            for session in self._sessions.values():
                for participant in session.participants.values():
                    if participant.is_active:
                        time_since_heartbeat = (now - participant.last_heartbeat).total_seconds()
                        if time_since_heartbeat > self._heartbeat_timeout:
                            participant.is_active = False
                            inactive_count += 1

            return inactive_count
