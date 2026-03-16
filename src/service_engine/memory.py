"""
MemoryManager — UserMemory CRUD, 50-entry compression, include_memory toggle.

Stores interaction history per (user_id, tenant_id). When entries exceed
COMPRESSION_THRESHOLD, triggers LLM summary compression.
"""

import logging
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import uuid4

from sqlalchemy import delete, func, select

from src.database.connection import db_manager
from src.service_engine.models import UserMemory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COMPRESSION_THRESHOLD = 50


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------
class MemoryManager:
    """CRUD + compression for per-user interaction memory."""

    def __init__(
        self,
        session_factory: Optional[Callable] = None,
        summarizer: Optional[Callable] = None,
    ) -> None:
        self._session_factory = session_factory or db_manager.get_session
        self._summarizer = summarizer or self._default_summarizer

    # -- public API ----------------------------------------------------------

    async def load_memories(
        self, user_id: str, tenant_id: str,
    ) -> list[dict]:
        """Load all memory entries for *user_id* + *tenant_id*, ordered by created_at."""
        with self._session_factory() as session:
            stmt = (
                select(UserMemory)
                .where(
                    UserMemory.user_id == user_id,
                    UserMemory.tenant_id == tenant_id,
                )
                .order_by(UserMemory.created_at.asc())
            )
            rows = session.execute(stmt).scalars().all()
            return [self._row_to_dict(r) for r in rows]

    async def append_memory(
        self, user_id: str, tenant_id: str, content: dict,
    ) -> None:
        """Add a new interaction memory entry."""
        with self._session_factory() as session:
            entry = UserMemory(
                id=uuid4(),
                user_id=user_id,
                tenant_id=tenant_id,
                memory_type="interaction",
                content=content,
                created_at=datetime.now(timezone.utc),
            )
            session.add(entry)

    async def compress_if_needed(
        self, user_id: str, tenant_id: str,
    ) -> None:
        """If entries > COMPRESSION_THRESHOLD, summarise and replace."""
        with self._session_factory() as session:
            count = self._count_entries(session, user_id, tenant_id)
            if count <= COMPRESSION_THRESHOLD:
                return

            entries = self._load_all(session, user_id, tenant_id)
            summary_text = await self._summarizer(
                [self._row_to_dict(e) for e in entries],
            )

            # Delete originals
            session.execute(
                delete(UserMemory).where(
                    UserMemory.user_id == user_id,
                    UserMemory.tenant_id == tenant_id,
                )
            )

            # Insert summary
            session.add(
                UserMemory(
                    id=uuid4(),
                    user_id=user_id,
                    tenant_id=tenant_id,
                    memory_type="summary",
                    content={"summary": summary_text},
                    created_at=datetime.now(timezone.utc),
                )
            )

    async def clear_memories(
        self, user_id: str, tenant_id: str,
    ) -> None:
        """Delete all memories for *user_id* + *tenant_id*."""
        with self._session_factory() as session:
            session.execute(
                delete(UserMemory).where(
                    UserMemory.user_id == user_id,
                    UserMemory.tenant_id == tenant_id,
                )
            )

    # -- default summarizer --------------------------------------------------

    @staticmethod
    async def _default_summarizer(entries: list[dict]) -> str:
        """Simple concatenation fallback when no LLM available."""
        return f"Summary of {len(entries)} interactions"

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _row_to_dict(row: UserMemory) -> dict:
        return {
            "id": str(row.id),
            "user_id": row.user_id,
            "tenant_id": row.tenant_id,
            "memory_type": row.memory_type,
            "content": row.content,
            "created_at": (
                row.created_at.isoformat() if row.created_at else None
            ),
        }

    @staticmethod
    def _count_entries(session, user_id: str, tenant_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(UserMemory)
            .where(
                UserMemory.user_id == user_id,
                UserMemory.tenant_id == tenant_id,
            )
        )
        return session.execute(stmt).scalar() or 0

    @staticmethod
    def _load_all(session, user_id: str, tenant_id: str) -> list[UserMemory]:
        stmt = (
            select(UserMemory)
            .where(
                UserMemory.user_id == user_id,
                UserMemory.tenant_id == tenant_id,
            )
            .order_by(UserMemory.created_at.asc())
        )
        return list(session.execute(stmt).scalars().all())
