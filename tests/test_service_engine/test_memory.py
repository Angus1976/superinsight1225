"""Unit tests for MemoryManager.

Uses a pure in-memory mock approach — no real DB or SQLite required.
We create a thin fake session that stores UserMemory rows in a plain list
and interprets SQLAlchemy statement objects via isinstance checks.
"""

import pytest
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.sql.dml import Delete
from sqlalchemy.sql.expression import FunctionElement
from sqlalchemy.sql.selectable import Select

from src.service_engine.memory import COMPRESSION_THRESHOLD, MemoryManager
from src.service_engine.models import UserMemory


# ---------------------------------------------------------------------------
# Fake session / session-factory (pure in-memory, no DB)
# ---------------------------------------------------------------------------

class _FakeScalars:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def all(self) -> list:
        return list(self._rows)


class _FakeResult:
    def __init__(self, rows: Optional[list] = None, scalar_value=None) -> None:
        self._rows = rows
        self._scalar_value = scalar_value

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._rows or [])

    def scalar(self):
        return self._scalar_value


class FakeSession:
    """In-memory session backed by a shared list of UserMemory objects."""

    def __init__(self, store: list) -> None:
        self._store = store
        self._pending: list = []

    def add(self, obj) -> None:
        self._pending.append(obj)

    def commit(self) -> None:
        self._store.extend(self._pending)
        self._pending.clear()

    def rollback(self) -> None:
        self._pending.clear()

    def close(self) -> None:
        pass

    def execute(self, stmt):
        if isinstance(stmt, Delete):
            return self._exec_delete(stmt)
        if isinstance(stmt, Select):
            if self._is_count(stmt):
                return self._exec_count(stmt)
            return self._exec_select(stmt)
        return _FakeResult()

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _extract_filters(stmt):
        """Pull user_id / tenant_id values from the WHERE clause."""
        user_id = tenant_id = None
        clause = getattr(stmt, 'whereclause', None)
        if clause is None:
            return user_id, tenant_id
        parts = list(clause.clauses) if hasattr(clause, 'clauses') else [clause]
        for part in parts:
            left = getattr(part, 'left', None)
            right = getattr(part, 'right', None)
            if left is None or right is None:
                continue
            col = str(getattr(left, 'key', ''))
            val = getattr(right, 'value', None)
            if col == 'user_id':
                user_id = val
            elif col == 'tenant_id':
                tenant_id = val
        return user_id, tenant_id

    def _filtered(self, stmt) -> list:
        uid, tid = self._extract_filters(stmt)
        rows = self._store
        if uid is not None:
            rows = [r for r in rows if r.user_id == uid]
        if tid is not None:
            rows = [r for r in rows if r.tenant_id == tid]
        return rows

    @staticmethod
    def _is_count(stmt: Select) -> bool:
        for col in stmt.selected_columns:
            if isinstance(col, FunctionElement):
                return True
        return False

    def _exec_select(self, stmt: Select) -> _FakeResult:
        rows = self._filtered(stmt)
        if hasattr(stmt, '_order_by_clauses') and stmt._order_by_clauses:
            rows = sorted(
                rows,
                key=lambda r: r.created_at or datetime.min.replace(tzinfo=timezone.utc),
            )
        return _FakeResult(rows=rows)

    def _exec_count(self, stmt: Select) -> _FakeResult:
        return _FakeResult(scalar_value=len(self._filtered(stmt)))

    def _exec_delete(self, stmt: Delete) -> _FakeResult:
        uid, tid = self._extract_filters(stmt)
        self._store[:] = [
            r for r in self._store
            if not (
                (uid is None or r.user_id == uid)
                and (tid is None or r.tenant_id == tid)
            )
        ]
        return _FakeResult()


def _make_factory(store: list):
    @contextmanager
    def factory():
        s = FakeSession(store)
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()
    return factory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store():
    return []

@pytest.fixture()
def session_factory(store):
    return _make_factory(store)

@pytest.fixture()
def manager(session_factory):
    return MemoryManager(session_factory=session_factory)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER = "u-1"
TENANT = "t-1"


def _seed(store: list, n: int, user_id=USER, tenant_id=TENANT):
    for i in range(n):
        store.append(
            UserMemory(
                id=uuid4(),
                user_id=user_id,
                tenant_id=tenant_id,
                memory_type="interaction",
                content={"msg": f"entry-{i}"},
                created_at=datetime(2025, 1, 1, 0, 0, i, tzinfo=timezone.utc),
            )
        )


# ---------------------------------------------------------------------------
# Tests — load_memories
# ---------------------------------------------------------------------------

class TestLoadMemories:
    @pytest.mark.asyncio
    async def test_returns_empty_for_new_user(self, manager):
        result = await manager.load_memories(USER, TENANT)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_entries_in_order(self, manager, store):
        _seed(store, 3)
        result = await manager.load_memories(USER, TENANT)
        assert len(result) == 3
        timestamps = [r["created_at"] for r in result]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_isolates_by_user_and_tenant(self, manager, store):
        _seed(store, 2, user_id="u-1", tenant_id="t-1")
        _seed(store, 3, user_id="u-2", tenant_id="t-1")
        result = await manager.load_memories("u-1", "t-1")
        assert len(result) == 2
        assert all(r["user_id"] == "u-1" for r in result)


# ---------------------------------------------------------------------------
# Tests — append_memory
# ---------------------------------------------------------------------------

class TestAppendMemory:
    @pytest.mark.asyncio
    async def test_adds_entry(self, manager):
        await manager.append_memory(USER, TENANT, {"role": "user", "text": "hi"})
        entries = await manager.load_memories(USER, TENANT)
        assert len(entries) == 1
        assert entries[0]["memory_type"] == "interaction"
        assert entries[0]["content"] == {"role": "user", "text": "hi"}

    @pytest.mark.asyncio
    async def test_multiple_appends(self, manager):
        await manager.append_memory(USER, TENANT, {"msg": "a"})
        await manager.append_memory(USER, TENANT, {"msg": "b"})
        entries = await manager.load_memories(USER, TENANT)
        assert len(entries) == 2


# ---------------------------------------------------------------------------
# Tests — compress_if_needed
# ---------------------------------------------------------------------------

class TestCompressIfNeeded:
    @pytest.mark.asyncio
    async def test_no_compression_at_threshold(self, manager, store):
        _seed(store, COMPRESSION_THRESHOLD)
        await manager.compress_if_needed(USER, TENANT)
        entries = await manager.load_memories(USER, TENANT)
        assert len(entries) == COMPRESSION_THRESHOLD

    @pytest.mark.asyncio
    async def test_compresses_above_threshold(self, manager, store):
        _seed(store, COMPRESSION_THRESHOLD + 1)
        await manager.compress_if_needed(USER, TENANT)
        entries = await manager.load_memories(USER, TENANT)
        assert len(entries) == 1
        assert entries[0]["memory_type"] == "summary"
        assert "summary" in entries[0]["content"]

    @pytest.mark.asyncio
    async def test_custom_summarizer_called(self, store, session_factory):
        called_with = []

        async def fake_summarizer(entries):
            called_with.append(len(entries))
            return "custom summary"

        mgr = MemoryManager(session_factory=session_factory, summarizer=fake_summarizer)
        _seed(store, COMPRESSION_THRESHOLD + 5)
        await mgr.compress_if_needed(USER, TENANT)

        assert called_with == [COMPRESSION_THRESHOLD + 5]
        entries = await mgr.load_memories(USER, TENANT)
        assert entries[0]["content"]["summary"] == "custom summary"

    @pytest.mark.asyncio
    async def test_does_not_affect_other_users(self, manager, store):
        _seed(store, COMPRESSION_THRESHOLD + 1, user_id="u-1")
        _seed(store, 5, user_id="u-2")
        await manager.compress_if_needed("u-1", TENANT)
        other = await manager.load_memories("u-2", TENANT)
        assert len(other) == 5


# ---------------------------------------------------------------------------
# Tests — clear_memories
# ---------------------------------------------------------------------------

class TestClearMemories:
    @pytest.mark.asyncio
    async def test_removes_all_entries(self, manager, store):
        _seed(store, 5)
        await manager.clear_memories(USER, TENANT)
        entries = await manager.load_memories(USER, TENANT)
        assert entries == []

    @pytest.mark.asyncio
    async def test_does_not_affect_other_users(self, manager, store):
        _seed(store, 3, user_id="u-1")
        _seed(store, 4, user_id="u-2")
        await manager.clear_memories("u-1", TENANT)
        remaining = await manager.load_memories("u-2", TENANT)
        assert len(remaining) == 4
